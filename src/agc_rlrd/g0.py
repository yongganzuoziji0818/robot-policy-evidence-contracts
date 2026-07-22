"""Synthetic G0-A/G0-B development landscapes and evaluation pipeline.

Nothing in this module represents a natural N0-B version pair.  Synthetic G0
results are algorithm-validity development evidence only.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from itertools import combinations
from math import log, sqrt
from typing import Iterable, Mapping, Sequence

import numpy as np

from .certification import (
    certify_locked_path,
    clopper_pearson_upper_bound,
    hoeffding_upper_bound,
)
from .metrics import summarize_safety_debt
from .planning import find_minimum_debt_path
from .profiles import (
    Interaction,
    Profile,
    binary_profiles,
    identify_pairwise_landscape,
    reconstruct_risk,
)


@dataclass(frozen=True)
class Landscape:
    n_agents: int
    landscape_class: str
    seed: int
    risk: dict[Profile, float]
    agent_types: tuple[str, ...]
    typed_edges: tuple[tuple[int, int], ...]


def stable_seed(*parts: object) -> int:
    digest = sha256("|".join(map(str, parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _agent_types(n_agents: int) -> tuple[str, ...]:
    if n_agents < 4:
        raise ValueError("G0 uses n_agents >= 4")
    return ("U", "U") + ("G",) * (n_agents - 2)


def _typed_edges(types: Sequence[str]) -> tuple[tuple[int, int], ...]:
    return tuple(
        (left, right)
        for left, right in combinations(range(len(types)), 2)
        if types[left] != types[right]
    )


def _coefficient_risk(
    n_agents: int, coefficients: Mapping[Interaction, float]
) -> dict[Profile, float]:
    risk = {
        profile: reconstruct_risk(profile, coefficients)
        for profile in binary_profiles(n_agents)
    }
    if any(value < 0.0 or value > 1.0 for value in risk.values()):
        raise ValueError("coefficient generator produced an invalid probability")
    return risk


def generate_landscape(n_agents: int, landscape_class: str, seed: int) -> Landscape:
    """Generate one frozen exact Boolean risk landscape."""
    rng = np.random.default_rng(seed)
    types = _agent_types(n_agents)
    typed_edges = _typed_edges(types)
    profiles = binary_profiles(n_agents)
    baseline = float(rng.uniform(0.023, 0.027))

    if landscape_class == "adversarial_middle_layer":
        middle = n_agents // 2
        risk = {profile: 0.03 for profile in profiles}
        middle_profiles = [profile for profile in profiles if sum(profile) == middle]
        for profile in middle_profiles:
            risk[profile] = 0.13
        if seed % 2 == 0:
            risk[middle_profiles[int(rng.integers(0, len(middle_profiles)))]] = 0.025
        risk[(0,) * n_agents] = baseline
        risk[(1,) * n_agents] = 0.04
        return Landscape(n_agents, landscape_class, seed, risk, types, typed_edges)

    if landscape_class == "additive_null":
        coefficients: dict[Interaction, float] = {frozenset(): baseline}
        for index in range(n_agents):
            coefficients[frozenset((index,))] = float(rng.uniform(-0.001, 0.001))
    elif landscape_class == "sparse_pairwise":
        baseline = 0.04
        coefficients = {frozenset(): baseline}
        for index in range(n_agents):
            coefficients[frozenset((index,))] = 0.0
        possible = list(combinations(range(n_agents), 2))
        rng.shuffle(possible)
        dangerous_edge, compensating_edge = possible[:2]
        positive = float(rng.uniform(0.075, 0.080))
        coefficients[frozenset(dangerous_edge)] = positive
        coefficients[frozenset(compensating_edge)] = 0.04 - positive
    elif landscape_class == "typed_sparse_pairwise":
        baseline = 0.04
        coefficients = {frozenset(): baseline}
        for index in range(n_agents):
            coefficients[frozenset((index,))] = 0.0
        possible = list(typed_edges)
        rng.shuffle(possible)
        dangerous_edge, compensating_edge = possible[:2]
        positive = float(rng.uniform(0.075, 0.080))
        coefficients[frozenset(dangerous_edge)] = positive
        coefficients[frozenset(compensating_edge)] = 0.04 - positive
    elif landscape_class == "higher_order_misspecified":
        baseline = 0.04
        coefficients = {frozenset(): baseline}
        for index in range(n_agents):
            coefficients[frozenset((index,))] = 0.0
        triples = list(combinations(range(n_agents), 3))
        dangerous_triple = triples[int(rng.integers(0, len(triples)))]
        positive = float(rng.uniform(0.075, 0.080))
        compensators = [
            pair
            for pair in combinations(range(n_agents), 2)
            if not set(pair) <= set(dangerous_triple)
        ]
        compensating_pair = compensators[int(rng.integers(0, len(compensators)))]
        coefficients[frozenset(dangerous_triple)] = positive
        coefficients[frozenset(compensating_pair)] = 0.04 - positive
    else:
        raise ValueError(f"unknown landscape_class: {landscape_class}")

    risk = _coefficient_risk(n_agents, coefficients)
    return Landscape(n_agents, landscape_class, seed, risk, types, typed_edges)


def order_path(order: Iterable[int], n_agents: int) -> tuple[Profile, ...]:
    current = [0] * n_agents
    path: list[Profile] = [tuple(current)]
    seen: set[int] = set()
    for index in order:
        if index in seen or index < 0 or index >= n_agents:
            raise ValueError("order must be a permutation")
        seen.add(index)
        current[index] = 1
        path.append(tuple(current))
    if len(seen) != n_agents:
        raise ValueError("order must include every agent")
    return tuple(path)


def _pairwise_model(
    landscape: Landscape,
    edges: Sequence[tuple[int, int]],
    observe,
) -> dict[Profile, float]:
    identified = identify_pairwise_landscape(observe, landscape.n_agents, edges)
    return {
        profile: min(1.0, max(0.0, value))
        for profile, value in identified.reconstructed_risk.items()
    }


def choose_path(
    method: str,
    landscape: Landscape,
    *,
    mode: str,
    discovery_trials: int,
    discovery_alpha: float,
    tau_target: float,
    tau_hard: float,
    rng: np.random.Generator,
) -> tuple[tuple[Profile, ...] | None, int]:
    """Choose a path and report discovery calls (profiles in exact, trials in noisy)."""
    n_agents = landscape.n_agents
    start, goal = (0,) * n_agents, (1,) * n_agents
    cache: dict[Profile, float] = {}
    calls = 0

    def observe(profile: Profile) -> float:
        nonlocal calls
        if profile not in cache:
            if mode == "exact":
                cache[profile] = landscape.risk[profile]
                calls += 1
            elif mode == "noisy":
                failures = int(rng.binomial(discovery_trials, landscape.risk[profile]))
                cache[profile] = failures / discovery_trials
                calls += discovery_trials
            else:
                raise ValueError("mode must be exact or noisy")
        return cache[profile]

    if method == "oracle_safest_path":
        plan = find_minimum_debt_path(
            landscape.risk, tau_target=tau_target, tau_hard=tau_hard
        )
        return (None if plan is None else plan.path), 0
    if method == "fail_closed_no_upgrade":
        return (start,), 0
    if method == "atomic":
        return (start, goal), 0
    if method == "random_order":
        return order_path(rng.permutation(n_agents).tolist(), n_agents), 0
    if method == "uav_first":
        order = [i for i, value in enumerate(landscape.agent_types) if value == "U"]
        order += [i for i, value in enumerate(landscape.agent_types) if value == "G"]
        return order_path(order, n_agents), 0
    if method == "ugv_first":
        order = [i for i, value in enumerate(landscape.agent_types) if value == "G"]
        order += [i for i, value in enumerate(landscape.agent_types) if value == "U"]
        return order_path(order, n_agents), 0
    if method == "reward_dependency_order":
        degree = {index: 0 for index in range(n_agents)}
        for left, right in landscape.typed_edges:
            degree[left] += 1
            degree[right] += 1
        order = sorted(range(n_agents), key=lambda index: (degree[index], index))
        return order_path(order, n_agents), 0
    if method == "independent_singleton_canary":
        singletons = []
        for index in range(n_agents):
            profile = tuple(1 if i == index else 0 for i in range(n_agents))
            singletons.append((observe(profile), index))
        return order_path([index for _, index in sorted(singletons)], n_agents), calls

    if method == "rlrd_full":
        predicted = _pairwise_model(landscape, landscape.typed_edges, observe)
    elif method == "generic_pairwise_active":
        predicted = _pairwise_model(
            landscape, tuple(combinations(range(n_agents), 2)), observe
        )
    elif method in {"uniform_exhaustive", "generic_ucb_shortest_path"}:
        predicted = {profile: observe(profile) for profile in binary_profiles(n_agents)}
        if method == "generic_ucb_shortest_path" and mode == "noisy":
            per_profile_alpha = discovery_alpha / len(predicted)
            radius = sqrt(log(1.0 / per_profile_alpha) / (2.0 * discovery_trials))
            predicted = {profile: min(1.0, value + radius) for profile, value in predicted.items()}
    else:
        raise ValueError(f"unknown method: {method}")

    # Discovery proposes an order; it does not certify safety.  Observe the goal
    # directly and avoid converting noisy model uncertainty into a premature hard
    # rejection.  Fresh locked-path certification remains the only promotion gate.
    predicted[goal] = observe(goal)
    plan = find_minimum_debt_path(predicted, tau_target=tau_target, tau_hard=1.0)
    return (None if plan is None else plan.path), calls


def _certify_atomic(
    path: Sequence[Profile],
    landscape: Landscape,
    *,
    trials: int,
    alpha: float,
    tau_target: float,
    tau_hard: float,
    debt_budget: float,
    bound_method: str,
    rng: np.random.Generator,
) -> tuple[bool, str, int]:
    per_profile_alpha = alpha / len(path)
    bounds = []
    for profile in path:
        failures = int(rng.binomial(trials, landscape.risk[profile]))
        if bound_method == "clopper_pearson":
            bounds.append(
                clopper_pearson_upper_bound(failures, trials, per_profile_alpha)
            )
        else:
            bounds.append(hoeffding_upper_bound(failures, trials, per_profile_alpha))
    debt = sum(max(value - tau_target, 0.0) for value in bounds)
    if max(bounds) > tau_hard:
        return False, "HOLD_HARD_CAP", trials * len(path)
    if debt > debt_budget:
        return False, "HOLD_DEBT", trials * len(path)
    return True, "PROMOTE", trials * len(path)


def evaluate_method(
    landscape: Landscape,
    method: str,
    *,
    mode: str,
    discovery_trials: int,
    certification_trials: int,
    familywise_alpha: float,
    tau_target: float,
    tau_hard: float,
    debt_budget: float,
    certification_bound: str = "hoeffding",
) -> dict[str, object]:
    method_seed = stable_seed(landscape.seed, landscape.landscape_class, method, mode)
    rng = np.random.default_rng(method_seed)
    oracle = find_minimum_debt_path(
        landscape.risk, tau_target=tau_target, tau_hard=tau_hard
    )
    path, discovery_calls = choose_path(
        method,
        landscape,
        mode=mode,
        discovery_trials=discovery_trials,
        discovery_alpha=familywise_alpha,
        tau_target=tau_target,
        tau_hard=tau_hard,
        rng=rng,
    )
    operationally_eligible = method not in {"atomic", "fail_closed_no_upgrade", "oracle_safest_path"}
    base = {
        "mode": mode,
        "landscape_class": landscape.landscape_class,
        "n_agents": landscape.n_agents,
        "landscape_seed": landscape.seed,
        "method": method,
        "oracle_feasible": oracle is not None,
        "operationally_eligible": operationally_eligible,
        "discovery_calls": discovery_calls,
        "certification_calls": 0,
        "path": "" if path is None else ">".join("".join(map(str, p)) for p in path),
    }
    if path is None:
        return base | {
            "decision": "HOLD_NO_PATH",
            "promoted": False,
            "true_valid": False,
            "false_approval": False,
            "safe_completion": False,
            "true_normalized_debt": None,
            "true_maximum_risk": None,
            "optimality_gap": None,
            "total_calls": discovery_calls,
        }
    if method == "fail_closed_no_upgrade":
        return base | {
            "decision": "NO_UPGRADE",
            "promoted": False,
            "true_valid": True,
            "false_approval": False,
            "safe_completion": False,
            "true_normalized_debt": 0.0,
            "true_maximum_risk": landscape.risk[path[0]],
            "optimality_gap": None,
            "total_calls": 0,
        }

    risks = tuple(landscape.risk[profile] for profile in path)
    debt = summarize_safety_debt(
        risks,
        (1.0,) * len(path),
        tau_target=tau_target,
        tau_hard=tau_hard,
    )
    true_valid = debt.maximum_risk <= tau_hard and debt.cumulative_debt <= debt_budget
    oracle_gap = None if oracle is None else debt.cumulative_debt - oracle.cumulative_debt

    if mode == "exact":
        promoted = true_valid
        decision = "PATH_VALID" if true_valid else "PATH_INVALID"
        certification_calls = 0
    elif method == "atomic":
        promoted, decision, certification_calls = _certify_atomic(
            path,
            landscape,
            trials=certification_trials,
            alpha=familywise_alpha,
            tau_target=tau_target,
            tau_hard=tau_hard,
            debt_budget=debt_budget,
            bound_method=certification_bound,
            rng=rng,
        )
    else:
        counts = {
            profile: (
                int(failures := rng.binomial(certification_trials, landscape.risk[profile])),
                certification_trials,
            )
            for profile in path
        }
        result = certify_locked_path(
            path,
            counts,
            familywise_alpha=familywise_alpha,
            tau_target=tau_target,
            tau_hard=tau_hard,
            exposure_by_stage=(1.0,) * len(path),
            debt_budget=debt_budget,
            certification_split_id=f"cert-{method_seed}",
            discovery_split_id=f"discover-{method_seed}",
            bound_method=certification_bound,
        )
        promoted = result.promote
        decision = result.decision + "_" + result.reason.replace(" ", "_").upper()
        certification_calls = certification_trials * len(path)

    return base | {
        "decision": decision,
        "promoted": promoted,
        "true_valid": true_valid,
        "false_approval": bool(promoted and not true_valid),
        "safe_completion": bool(promoted and true_valid),
        "true_normalized_debt": debt.normalized_debt,
        "true_maximum_risk": debt.maximum_risk,
        "optimality_gap": oracle_gap,
        "certification_calls": certification_calls,
        "total_calls": discovery_calls + certification_calls,
    }
