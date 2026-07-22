"""Non-sealed synthetic FLUX-v8 problem-validation simulator.

This module uses only the Python standard library. The field is an intentionally
transparent response-function model, not a CFD replacement.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Sequence


@dataclass(frozen=True)
class FieldConfig:
    escape_coefficient: float = 0.2
    aerial_width: float = 11.0
    ground_width: float = 6.0
    aerial_height: float = 5.0
    vertical_decay: float = 0.06
    source_grid_min: float = -22.0
    source_grid_max: float = 22.0
    source_grid_step: float = 0.02

    def __post_init__(self) -> None:
        positive = (
            self.escape_coefficient,
            self.aerial_width,
            self.ground_width,
            self.aerial_height,
            self.vertical_decay,
            self.source_grid_step,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in positive):
            raise ValueError("field scales must be finite and positive")
        if self.source_grid_min >= self.source_grid_max:
            raise ValueError("invalid source grid")


@dataclass(frozen=True)
class Campaign:
    seed: int
    source: float
    deposition: float
    source_x: float
    aerial_sigma: float
    ground_sigma: float


@dataclass(frozen=True)
class Observation:
    modality: str
    x: float
    value: float


@dataclass(frozen=True)
class MethodResult:
    method: str
    source_hat: float
    deposition_hat: float
    source_x_hat: float
    source_relative_error: float
    deposition_absolute_error: float
    location_absolute_error: float
    aerial_count: int
    ground_count: int


UNIFORM_TEN = (-27.0, -21.0, -15.0, -9.0, -3.0, 3.0, 9.0, 15.0, 21.0, 27.0)
AERIAL_SIX = (-25.0, -15.0, -5.0, 5.0, 15.0, 25.0)
GROUND_FIXED_FOUR = (-24.0, -8.0, 8.0, 24.0)
GROUND_CANDIDATES = tuple(float(value) for value in range(-28, 29, 2))


def make_campaign(
    *, seed: int, deposition: float, aerial_sigma: float, ground_sigma: float
) -> Campaign:
    rng = random.Random(seed)
    return Campaign(
        seed=seed,
        source=1.0,
        deposition=deposition,
        source_x=rng.uniform(-18.0, 18.0),
        aerial_sigma=aerial_sigma,
        ground_sigma=ground_sigma,
    )


def _aerial_shape(config: FieldConfig, x: float, source_x: float) -> float:
    horizontal = math.exp(-0.5 * ((x - source_x) / config.aerial_width) ** 2)
    return horizontal * math.exp(-config.vertical_decay * config.aerial_height)


def _ground_shape(config: FieldConfig, x: float, source_x: float) -> float:
    return math.exp(-0.5 * ((x - source_x) / config.ground_width) ** 2)


def _observe(
    config: FieldConfig,
    campaign: Campaign,
    modality: str,
    positions: Sequence[float],
    rng: random.Random,
) -> tuple[Observation, ...]:
    amplitude = campaign.source / (config.escape_coefficient + campaign.deposition)
    deposited = campaign.deposition * amplitude
    observations: list[Observation] = []
    for x in positions:
        if modality == "aerial":
            mean = amplitude * _aerial_shape(config, x, campaign.source_x)
            sigma = campaign.aerial_sigma
        elif modality == "ground":
            mean = deposited * _ground_shape(config, x, campaign.source_x)
            sigma = campaign.ground_sigma
        else:
            raise ValueError(f"unknown modality: {modality}")
        observations.append(Observation(modality, x, mean + rng.gauss(0.0, sigma)))
    return tuple(observations)


def _grid(config: FieldConfig) -> tuple[float, ...]:
    count = int(round((config.source_grid_max - config.source_grid_min) / config.source_grid_step))
    return tuple(config.source_grid_min + index * config.source_grid_step for index in range(count + 1))


def _fit_scale(values: Sequence[float], shapes: Sequence[float]) -> tuple[float, float]:
    denominator = sum(value * value for value in shapes)
    if denominator <= 0.0:
        return 0.0, math.inf
    scale = max(1e-12, sum(y * h for y, h in zip(values, shapes)) / denominator)
    residual = sum((y - scale * h) ** 2 for y, h in zip(values, shapes))
    return scale, residual


def _estimate(
    config: FieldConfig,
    campaign: Campaign,
    observations: Sequence[Observation],
    ground_only_prior_deposition: float = 0.275,
) -> tuple[float, float, float]:
    aerial = tuple(obs for obs in observations if obs.modality == "aerial")
    ground = tuple(obs for obs in observations if obs.modality == "ground")
    if not aerial and not ground:
        raise ValueError("at least one observation is required")
    best: tuple[float, float, float, float] | None = None
    for source_x in _grid(config):
        amplitude = deposited = 0.0
        objective = 0.0
        if aerial:
            shapes = tuple(_aerial_shape(config, obs.x, source_x) for obs in aerial)
            amplitude, residual = _fit_scale(tuple(obs.value for obs in aerial), shapes)
            objective += residual / (campaign.aerial_sigma**2)
        if ground:
            shapes = tuple(_ground_shape(config, obs.x, source_x) for obs in ground)
            deposited, residual = _fit_scale(tuple(obs.value for obs in ground), shapes)
            objective += residual / (campaign.ground_sigma**2)
        candidate = (objective, source_x, amplitude, deposited)
        if best is None or candidate < best:
            best = candidate
    assert best is not None
    _, source_x_hat, amplitude_hat, deposited_hat = best
    if aerial and ground:
        deposition_hat = max(0.0, deposited_hat / amplitude_hat)
        source_hat = config.escape_coefficient * amplitude_hat + deposited_hat
    elif aerial:
        deposition_hat = 0.0
        source_hat = config.escape_coefficient * amplitude_hat
    else:
        deposition_hat = ground_only_prior_deposition
        source_hat = deposited_hat * (
            config.escape_coefficient + ground_only_prior_deposition
        ) / ground_only_prior_deposition
    return source_hat, deposition_hat, source_x_hat


def _estimate_at_source_x(
    config: FieldConfig,
    campaign: Campaign,
    observations: Sequence[Observation],
    source_x_hat: float,
) -> tuple[float, float, float]:
    """Estimate only the aerial-nullspace parameters at a fixed aerial location."""

    aerial = tuple(obs for obs in observations if obs.modality == "aerial")
    ground = tuple(obs for obs in observations if obs.modality == "ground")
    if not aerial or not ground:
        raise ValueError("projected FLUX update requires both modalities")
    aerial_shapes = tuple(_aerial_shape(config, obs.x, source_x_hat) for obs in aerial)
    ground_shapes = tuple(_ground_shape(config, obs.x, source_x_hat) for obs in ground)
    amplitude, _ = _fit_scale(tuple(obs.value for obs in aerial), aerial_shapes)
    deposited, _ = _fit_scale(tuple(obs.value for obs in ground), ground_shapes)
    deposition_hat = max(0.0, deposited / amplitude)
    source_hat = config.escape_coefficient * amplitude + deposited
    return source_hat, deposition_hat, source_x_hat


def _targeted_ground_positions(source_x_hat: float) -> tuple[float, ...]:
    ranked = sorted(GROUND_CANDIDATES, key=lambda value: (abs(value - source_x_hat), value))
    return tuple(sorted(ranked[:4]))


def run_method(config: FieldConfig, campaign: Campaign, method: str) -> MethodResult:
    rng = random.Random(campaign.seed * 1009 + sum(ord(char) for char in method))
    projected_source_x: float | None = None
    if method == "uav_only":
        observations = _observe(config, campaign, "aerial", UNIFORM_TEN, rng)
    elif method == "ugv_only":
        observations = _observe(config, campaign, "ground", UNIFORM_TEN, rng)
    elif method == "fixed_joint":
        observations = _observe(config, campaign, "aerial", AERIAL_SIX, rng)
        observations += _observe(config, campaign, "ground", GROUND_FIXED_FOUR, rng)
    elif method == "random_joint":
        aerial_positions = tuple(sorted(rng.sample(UNIFORM_TEN, 6)))
        ground_positions = tuple(sorted(rng.sample(GROUND_CANDIDATES, 4)))
        observations = _observe(config, campaign, "aerial", aerial_positions, rng)
        observations += _observe(config, campaign, "ground", ground_positions, rng)
    elif method in {"flux", "oracle_joint"}:
        aerial = _observe(config, campaign, "aerial", AERIAL_SIX, rng)
        if method == "flux":
            _, _, projected_source_x = _estimate(config, campaign, aerial)
            ground_positions = _targeted_ground_positions(projected_source_x)
        else:
            ground_positions = _targeted_ground_positions(campaign.source_x)
        observations = aerial + _observe(config, campaign, "ground", ground_positions, rng)
    else:
        raise ValueError(f"unknown method: {method}")
    if projected_source_x is None:
        source_hat, deposition_hat, source_x_hat = _estimate(config, campaign, observations)
    else:
        source_hat, deposition_hat, source_x_hat = _estimate_at_source_x(
            config, campaign, observations, projected_source_x
        )
    aerial_count = sum(obs.modality == "aerial" for obs in observations)
    ground_count = len(observations) - aerial_count
    if aerial_count + ground_count != 10:
        raise RuntimeError("matched-count contract violated")
    return MethodResult(
        method=method,
        source_hat=source_hat,
        deposition_hat=deposition_hat,
        source_x_hat=source_x_hat,
        source_relative_error=abs(source_hat - campaign.source) / campaign.source,
        deposition_absolute_error=abs(deposition_hat - campaign.deposition),
        location_absolute_error=abs(source_x_hat - campaign.source_x),
        aerial_count=aerial_count,
        ground_count=ground_count,
    )
