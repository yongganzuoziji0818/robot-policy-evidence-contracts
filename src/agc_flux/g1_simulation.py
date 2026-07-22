"""Public-asset-constrained semi-natural FLUX-v8 G1 simulator.

The response functions remain synthetic. Their censoring and mismatch roles
are constrained by the public 106Ru concentration/deposition literature. This
module must never be described as field or natural robot evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Sequence


MISMATCH_FAMILIES = ("transport_shift", "deposition_patchiness", "detection_censoring")
G1_METHODS = (
    "uav_only", "fixed_joint", "random_joint", "joint_d_opt", "flux",
    "flux_no_projection", "flux_untargeted", "near_ground_joint", "oracle_joint",
)
AERIAL_SIX = (-25.0, -15.0, -5.0, 5.0, 15.0, 25.0)
UNIFORM_TEN = (-27.0, -21.0, -15.0, -9.0, -3.0, 3.0, 9.0, 15.0, 21.0, 27.0)
GROUND_FIXED_FOUR = (-24.0, -8.0, 8.0, 24.0)
GROUND_CANDIDATES = tuple(float(value) for value in range(-28, 29, 2))


@dataclass(frozen=True)
class G1Config:
    escape_coefficient: float = 0.2
    aerial_width: float = 11.0
    ground_width: float = 6.0
    aerial_height: float = 5.0
    near_ground_height: float = 0.5
    vertical_decay: float = 0.06
    source_grid_min: float = -22.0
    source_grid_max: float = 22.0
    source_grid_step: float = 0.05


@dataclass(frozen=True)
class G1Campaign:
    seed: int
    source: float
    deposition: float
    source_x: float
    aerial_sigma: float
    ground_sigma: float
    mismatch_family: str
    mismatch_sign: int
    patch_phase: float
    ground_mdq: float


@dataclass(frozen=True)
class G1Observation:
    modality: str
    x: float
    value: float
    detected: bool


@dataclass(frozen=True)
class G1MethodResult:
    method: str
    source_hat: float
    deposition_hat: float
    source_x_hat: float
    source_relative_error: float
    deposition_absolute_error: float
    location_absolute_error: float
    aerial_count: int
    ground_count: int
    near_ground_count: int
    ground_detected_count: int
    projected_update: bool
    selected_ground_positions: tuple[float, ...]


def make_g1_campaign(*, seed: int, deposition: float, noise_tier: str, mismatch_family: str) -> G1Campaign:
    if deposition not in (0.05, 0.5):
        raise ValueError("unsupported deposition level")
    if noise_tier not in ("low", "high"):
        raise ValueError("noise tier must be low or high")
    if mismatch_family not in MISMATCH_FAMILIES:
        raise ValueError("unknown mismatch family")
    rng = random.Random(seed)
    aerial_sigma, ground_sigma = ((0.05, 0.02) if noise_tier == "low" else (0.2, 0.1))
    mdq = 0.0
    if mismatch_family == "detection_censoring":
        mdq = 0.04 if noise_tier == "low" else 0.12
    return G1Campaign(
        seed=seed,
        source=rng.uniform(0.8, 1.2),
        deposition=deposition,
        source_x=rng.uniform(-16.0, 16.0),
        aerial_sigma=aerial_sigma,
        ground_sigma=ground_sigma,
        mismatch_family=mismatch_family,
        mismatch_sign=-1 if rng.random() < 0.5 else 1,
        patch_phase=rng.uniform(-math.pi, math.pi),
        ground_mdq=mdq,
    )


def _normal_noise(campaign: G1Campaign, modality: str, x: float) -> float:
    modality_code = {"aerial": 11, "ground": 23, "near_ground": 37}[modality]
    coordinate = int(round((x + 100.0) * 1000.0))
    rng = random.Random(campaign.seed * 1_000_003 + modality_code * 100_003 + coordinate)
    sigma = campaign.ground_sigma if modality == "ground" else campaign.aerial_sigma
    return rng.gauss(0.0, sigma)


def _truth_concentration_shape(config: G1Config, campaign: G1Campaign, x: float, height: float) -> float:
    width, center = config.aerial_width, campaign.source_x
    if campaign.mismatch_family == "transport_shift":
        width *= 1.30
        center += 1.2 * campaign.mismatch_sign
    return math.exp(-0.5 * ((x - center) / width) ** 2) * math.exp(-config.vertical_decay * height)


def _truth_ground_shape(config: G1Config, campaign: G1Campaign, x: float) -> float:
    width, center, multiplier = config.ground_width, campaign.source_x, 1.0
    if campaign.mismatch_family == "transport_shift":
        width *= 0.72
        center -= 1.0 * campaign.mismatch_sign
    elif campaign.mismatch_family == "deposition_patchiness":
        width *= 1.15
        multiplier = (1.0 + 0.15 * campaign.mismatch_sign) * (
            1.0 + 0.28 * math.sin((x - campaign.patch_phase) / 4.5)
        )
    return max(0.25, multiplier) * math.exp(-0.5 * ((x - center) / width) ** 2)


def observe(config: G1Config, campaign: G1Campaign, modality: str, positions: Sequence[float]) -> tuple[G1Observation, ...]:
    amplitude = campaign.source / (config.escape_coefficient + campaign.deposition)
    deposited = campaign.deposition * amplitude
    observations = []
    for x in positions:
        if modality == "aerial":
            mean = amplitude * _truth_concentration_shape(config, campaign, x, config.aerial_height)
        elif modality == "near_ground":
            mean = amplitude * _truth_concentration_shape(config, campaign, x, config.near_ground_height)
        elif modality == "ground":
            mean = deposited * _truth_ground_shape(config, campaign, x)
        else:
            raise ValueError("unknown modality")
        value = mean + _normal_noise(campaign, modality, x)
        detected = not (modality == "ground" and campaign.ground_mdq > 0.0 and value < campaign.ground_mdq)
        if not detected:
            value = 0.0
        observations.append(G1Observation(modality, float(x), value, detected))
    return tuple(observations)


def _nominal_shape(config: G1Config, observation: G1Observation, source_x: float) -> float:
    if observation.modality == "ground":
        width, vertical = config.ground_width, 1.0
    elif observation.modality == "aerial":
        width, vertical = config.aerial_width, math.exp(-config.vertical_decay * config.aerial_height)
    elif observation.modality == "near_ground":
        width, vertical = config.aerial_width, math.exp(-config.vertical_decay * config.near_ground_height)
    else:
        raise ValueError("unknown modality")
    return math.exp(-0.5 * ((observation.x - source_x) / width) ** 2) * vertical


def _fit_scale(values: Sequence[float], shapes: Sequence[float]) -> tuple[float, float]:
    denominator = sum(value * value for value in shapes)
    if denominator <= 0.0:
        return 1e-12, math.inf
    scale = max(1e-12, sum(y * h for y, h in zip(values, shapes)) / denominator)
    return scale, sum((y - scale * h) ** 2 for y, h in zip(values, shapes))


def _grid(config: G1Config) -> tuple[float, ...]:
    count = int(round((config.source_grid_max - config.source_grid_min) / config.source_grid_step))
    return tuple(config.source_grid_min + index * config.source_grid_step for index in range(count + 1))


def estimate(config: G1Config, campaign: G1Campaign, observations: Sequence[G1Observation], fixed_source_x: float | None = None) -> tuple[float, float, float]:
    concentration = tuple(obs for obs in observations if obs.modality in ("aerial", "near_ground"))
    ground = tuple(obs for obs in observations if obs.modality == "ground")
    if not concentration and not ground:
        raise ValueError("no observations")
    candidates = (fixed_source_x,) if fixed_source_x is not None else _grid(config)
    best: tuple[float, float, float, float] | None = None
    for source_x in candidates:
        amplitude = deposited = objective = 0.0
        if concentration:
            shapes = tuple(_nominal_shape(config, obs, source_x) for obs in concentration)
            amplitude, residual = _fit_scale(tuple(obs.value for obs in concentration), shapes)
            objective += residual / campaign.aerial_sigma**2
        if ground:
            shapes = tuple(_nominal_shape(config, obs, source_x) for obs in ground)
            deposited, residual = _fit_scale(tuple(obs.value for obs in ground), shapes)
            objective += residual / campaign.ground_sigma**2
        candidate = (objective, source_x, amplitude, deposited)
        if best is None or candidate < best:
            best = candidate
    assert best is not None
    _, source_x_hat, amplitude, deposited = best
    if concentration and ground:
        return config.escape_coefficient * amplitude + deposited, max(0.0, deposited / amplitude), source_x_hat
    if concentration:
        return config.escape_coefficient * amplitude, 0.0, source_x_hat
    prior = 0.275
    return deposited * (config.escape_coefficient + prior) / prior, prior, source_x_hat


def _nullspace_positions(source_x_hat: float) -> tuple[float, ...]:
    ranked = sorted(GROUND_CANDIDATES, key=lambda x: (abs(x - source_x_hat), x))
    return tuple(sorted(ranked[:4]))


def _determinant3(matrix: list[list[float]]) -> float:
    a, b, c = matrix
    return a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])


def _add_information(matrix: list[list[float]], jacobian: tuple[float, float, float], sigma: float) -> None:
    for row in range(3):
        for column in range(3):
            matrix[row][column] += jacobian[row] * jacobian[column] / sigma**2


def _d_opt_positions(config: G1Config, campaign: G1Campaign, source_x_hat: float, amplitude_hat: float) -> tuple[float, ...]:
    beta = 0.275
    source = amplitude_hat * (config.escape_coefficient + beta)
    information = [[1e-8 if row == column else 0.0 for column in range(3)] for row in range(3)]
    for x in AERIAL_SIX:
        h = math.exp(-0.5 * ((x - source_x_hat) / config.aerial_width) ** 2) * math.exp(-config.vertical_decay * config.aerial_height)
        jacobian = (h / (config.escape_coefficient + beta), -source * h / (config.escape_coefficient + beta) ** 2, amplitude_hat * h * (x - source_x_hat) / config.aerial_width**2)
        _add_information(information, jacobian, campaign.aerial_sigma)
    selected: list[float] = []
    for _ in range(4):
        best_score, best_x = -1.0, 0.0
        for x in GROUND_CANDIDATES:
            if x in selected:
                continue
            g = math.exp(-0.5 * ((x - source_x_hat) / config.ground_width) ** 2)
            deposited = beta * source / (config.escape_coefficient + beta)
            jacobian = (beta * g / (config.escape_coefficient + beta), source * config.escape_coefficient * g / (config.escape_coefficient + beta) ** 2, deposited * g * (x - source_x_hat) / config.ground_width**2)
            candidate = [row[:] for row in information]
            _add_information(candidate, jacobian, campaign.ground_sigma)
            score = _determinant3(candidate)
            if score > best_score:
                best_score, best_x = score, x
        selected.append(best_x)
        g = math.exp(-0.5 * ((best_x - source_x_hat) / config.ground_width) ** 2)
        deposited = beta * source / (config.escape_coefficient + beta)
        jacobian = (beta * g / (config.escape_coefficient + beta), source * config.escape_coefficient * g / (config.escape_coefficient + beta) ** 2, deposited * g * (best_x - source_x_hat) / config.ground_width**2)
        _add_information(information, jacobian, campaign.ground_sigma)
    return tuple(sorted(selected))


def run_g1_method(config: G1Config, campaign: G1Campaign, method: str) -> G1MethodResult:
    if method not in G1_METHODS:
        raise ValueError("unknown G1 method")
    selected_ground: tuple[float, ...] = ()
    projected, fixed_source_x = False, None
    if method == "uav_only":
        observations = observe(config, campaign, "aerial", UNIFORM_TEN)
    else:
        aerial = observe(config, campaign, "aerial", AERIAL_SIX)
        source_from_aerial, _, aerial_source_x = estimate(config, campaign, aerial)
        amplitude_hat = source_from_aerial / config.escape_coefficient
        if method == "fixed_joint":
            selected_ground = GROUND_FIXED_FOUR
        elif method == "random_joint":
            chooser = random.Random(campaign.seed * 313 + 17)
            selected_ground = tuple(sorted(chooser.sample(GROUND_CANDIDATES, 4)))
        elif method == "joint_d_opt":
            selected_ground = _d_opt_positions(config, campaign, aerial_source_x, amplitude_hat)
        elif method in ("flux", "flux_no_projection"):
            selected_ground = _nullspace_positions(aerial_source_x)
        elif method == "flux_untargeted":
            selected_ground = GROUND_FIXED_FOUR
        elif method == "near_ground_joint":
            observations = aerial + observe(config, campaign, "near_ground", GROUND_FIXED_FOUR)
        elif method == "oracle_joint":
            selected_ground = _nullspace_positions(campaign.source_x)
        if method != "near_ground_joint":
            observations = aerial + observe(config, campaign, "ground", selected_ground)
        if method in ("flux", "flux_untargeted"):
            fixed_source_x, projected = aerial_source_x, True
        elif method == "oracle_joint":
            fixed_source_x, projected = campaign.source_x, True
    source_hat, deposition_hat, source_x_hat = estimate(config, campaign, observations, fixed_source_x)
    aerial_count = sum(obs.modality == "aerial" for obs in observations)
    ground_count = sum(obs.modality == "ground" for obs in observations)
    near_ground_count = sum(obs.modality == "near_ground" for obs in observations)
    if aerial_count + ground_count + near_ground_count != 10:
        raise RuntimeError("matched sample-count contract violated")
    return G1MethodResult(
        method=method,
        source_hat=source_hat,
        deposition_hat=deposition_hat,
        source_x_hat=source_x_hat,
        source_relative_error=abs(source_hat - campaign.source) / campaign.source,
        deposition_absolute_error=abs(deposition_hat - campaign.deposition),
        location_absolute_error=abs(source_x_hat - campaign.source_x),
        aerial_count=aerial_count,
        ground_count=ground_count,
        near_ground_count=near_ground_count,
        ground_detected_count=sum(obs.modality == "ground" and obs.detected for obs in observations),
        projected_update=projected,
        selected_ground_positions=selected_ground,
    )
