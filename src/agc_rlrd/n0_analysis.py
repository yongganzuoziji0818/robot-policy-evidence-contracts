"""Method-agnostic measurements for a complete natural-version N0-B census."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Mapping

from .profiles import Profile, all_monotone_paths, binary_profiles, mobius_coefficients


@dataclass(frozen=True)
class PairInteraction:
    pair: tuple[int, int]
    contrast: float
    harmful: bool
    meets_sesoi: bool


@dataclass(frozen=True)
class NaturalCensusSummary:
    n_agents: int
    boundary_canaries_safe: bool
    safe_path_count: int
    unsafe_path_count: int
    order_changes_feasibility: bool
    pair_interactions: tuple[PairInteraction, ...]
    maximum_absolute_higher_order_interaction: float
    decision_changing_natural_interaction: bool


def _validate_complete_risk(risk: Mapping[Profile, float]) -> int:
    if not risk:
        raise ValueError("risk census is empty")
    n_agents = len(next(iter(risk)))
    expected = set(binary_profiles(n_agents))
    if set(risk) != expected:
        raise ValueError("N0-B requires a complete all-profile risk census")
    if any(not 0.0 <= float(value) <= 1.0 for value in risk.values()):
        raise ValueError("risk values must lie in [0, 1]")
    return n_agents


def summarize_natural_census(
    risk: Mapping[Profile, float], *, tau_hard: float, interaction_sesoi: float
) -> NaturalCensusSummary:
    """Summarize natural interaction without using an RLRD model or outcome.

    `decision_changing_natural_interaction` is deliberately stringent: the
    baseline, every singleton, and all-new profile must pass their canaries;
    at least one monotone order must be safe and one unsafe; and at least one
    harmful baseline-referenced pair interaction must meet the frozen SESOI.
    """
    n_agents = _validate_complete_risk(risk)
    if not 0.0 < tau_hard <= 1.0:
        raise ValueError("tau_hard must lie in (0, 1]")
    if not 0.0 < interaction_sesoi <= 1.0:
        raise ValueError("interaction_sesoi must lie in (0, 1]")

    baseline = (0,) * n_agents
    goal = (1,) * n_agents
    singleton_profiles = tuple(
        tuple(1 if position == index else 0 for position in range(n_agents))
        for index in range(n_agents)
    )
    boundary_safe = all(
        float(risk[profile]) <= tau_hard
        for profile in (baseline, *singleton_profiles, goal)
    )
    safe_paths = 0
    unsafe_paths = 0
    for path in all_monotone_paths(n_agents):
        if all(float(risk[profile]) <= tau_hard for profile in path):
            safe_paths += 1
        else:
            unsafe_paths += 1
    order_changes = safe_paths > 0 and unsafe_paths > 0

    coefficients = mobius_coefficients(risk)
    pair_interactions = tuple(
        PairInteraction(
            pair=(left, right),
            contrast=float(coefficients[frozenset((left, right))]),
            harmful=float(coefficients[frozenset((left, right))]) > 0.0,
            meets_sesoi=float(coefficients[frozenset((left, right))]) >= interaction_sesoi,
        )
        for left, right in combinations(range(n_agents), 2)
    )
    higher = max(
        (abs(float(value)) for subset, value in coefficients.items() if len(subset) >= 3),
        default=0.0,
    )
    decision_changing = (
        boundary_safe
        and order_changes
        and any(item.harmful and item.meets_sesoi for item in pair_interactions)
    )
    return NaturalCensusSummary(
        n_agents=n_agents,
        boundary_canaries_safe=boundary_safe,
        safe_path_count=safe_paths,
        unsafe_path_count=unsafe_paths,
        order_changes_feasibility=order_changes,
        pair_interactions=pair_interactions,
        maximum_absolute_higher_order_interaction=higher,
        decision_changing_natural_interaction=decision_changing,
    )

