"""Exact upgrade-path planning on a known or upper-confidence risk table."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Mapping, Sequence

from .profiles import Profile, binary_profiles


@dataclass(frozen=True)
class UpgradePlan:
    path: tuple[Profile, ...]
    cumulative_debt: float
    normalized_debt: float
    maximum_risk: float


def find_minimum_debt_path(
    risk_upper: Mapping[Profile, float],
    *,
    tau_target: float,
    tau_hard: float,
    exposure_by_stage: Sequence[float] | None = None,
) -> UpgradePlan | None:
    """Find the minimum-debt monotone path subject to a hard risk cap.

    `risk_upper` may contain exact risks in analytic G0 or simultaneous upper
    confidence bounds in certification.  Returning ``None`` is fail-closed.
    """
    if not 0.0 <= tau_target < tau_hard <= 1.0:
        raise ValueError("require 0 <= tau_target < tau_hard <= 1")
    if not risk_upper:
        raise ValueError("risk table is empty")
    n_agents = len(next(iter(risk_upper)))
    profiles = binary_profiles(n_agents)
    if set(risk_upper) != set(profiles):
        raise ValueError("planner requires a complete risk table")
    exposures = tuple(exposure_by_stage or (1.0,) * (n_agents + 1))
    if len(exposures) != n_agents + 1 or any(value < 0 for value in exposures):
        raise ValueError("exposure_by_stage must have n_agents + 1 nonnegative values")

    start = (0,) * n_agents
    goal = (1,) * n_agents
    if float(risk_upper[start]) > tau_hard or float(risk_upper[goal]) > tau_hard:
        return None

    best_cost: dict[Profile, float] = {}
    best_path: dict[Profile, tuple[Profile, ...]] = {}
    start_cost = exposures[0] * max(float(risk_upper[start]) - tau_target, 0.0)
    best_cost[start] = start_cost
    best_path[start] = (start,)

    for level in range(1, n_agents + 1):
        for profile in (item for item in profiles if sum(item) == level):
            risk = float(risk_upper[profile])
            if risk > tau_hard:
                continue
            node_cost = exposures[level] * max(risk - tau_target, 0.0)
            chosen_cost = inf
            chosen_path: tuple[Profile, ...] | None = None
            for index, value in enumerate(profile):
                if not value:
                    continue
                predecessor = profile[:index] + (0,) + profile[index + 1 :]
                if predecessor not in best_cost:
                    continue
                candidate_cost = best_cost[predecessor] + node_cost
                candidate_path = best_path[predecessor] + (profile,)
                if candidate_cost < chosen_cost - 1e-15 or (
                    abs(candidate_cost - chosen_cost) <= 1e-15
                    and (chosen_path is None or candidate_path < chosen_path)
                ):
                    chosen_cost = candidate_cost
                    chosen_path = candidate_path
            if chosen_path is not None:
                best_cost[profile] = chosen_cost
                best_path[profile] = chosen_path

    if goal not in best_path:
        return None
    path = best_path[goal]
    total_exposure = sum(exposures)
    normalized = best_cost[goal] / total_exposure if total_exposure else 0.0
    return UpgradePlan(
        path=path,
        cumulative_debt=best_cost[goal],
        normalized_debt=normalized,
        maximum_risk=max(float(risk_upper[profile]) for profile in path),
    )
