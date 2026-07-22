"""Binary mixed-version profiles and exact interaction decompositions."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, permutations, product
from typing import Callable, Iterable, Mapping, TypeAlias

Profile: TypeAlias = tuple[int, ...]
Interaction: TypeAlias = frozenset[int]


@dataclass(frozen=True)
class PairwiseIdentification:
    coefficients: dict[Interaction, float]
    reconstructed_risk: dict[Profile, float]
    queried_profiles: tuple[Profile, ...]

    @property
    def query_count(self) -> int:
        return len(self.queried_profiles)


def binary_profiles(n_agents: int) -> tuple[Profile, ...]:
    """Return every old/new version profile in lexicographic order."""
    if n_agents < 1:
        raise ValueError("n_agents must be positive")
    return tuple(product((0, 1), repeat=n_agents))


def _validate_profile(profile: Profile, n_agents: int | None = None) -> None:
    if n_agents is not None and len(profile) != n_agents:
        raise ValueError("profile length mismatch")
    if any(value not in (0, 1) for value in profile):
        raise ValueError("profiles must be binary")


def profile_for_subset(n_agents: int, subset: Iterable[int]) -> Profile:
    profile = [0] * n_agents
    for index in subset:
        if index < 0 or index >= n_agents:
            raise ValueError("agent index out of range")
        profile[index] = 1
    return tuple(profile)


def mobius_coefficients(risk: Mapping[Profile, float]) -> dict[Interaction, float]:
    """Compute the unique Boolean-lattice Möbius expansion of a full table.

    The returned coefficients satisfy
    p(v) = sum(beta[S] for S whose members are all upgraded in v).
    """
    if not risk:
        raise ValueError("risk table is empty")
    n_agents = len(next(iter(risk)))
    expected = set(binary_profiles(n_agents))
    if set(risk) != expected:
        missing = expected.difference(risk)
        extra = set(risk).difference(expected)
        raise ValueError(f"risk table must be complete; missing={missing}, extra={extra}")
    for profile, value in risk.items():
        _validate_profile(profile, n_agents)
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError("risk values must lie in [0, 1]")

    coefficients: dict[Interaction, float] = {}
    indices = tuple(range(n_agents))
    for size in range(n_agents + 1):
        for subset_tuple in combinations(indices, size):
            subset = frozenset(subset_tuple)
            coefficient = 0.0
            for inner_size in range(size + 1):
                for inner in combinations(subset_tuple, inner_size):
                    sign = -1.0 if (size - inner_size) % 2 else 1.0
                    coefficient += sign * float(risk[profile_for_subset(n_agents, inner)])
            coefficients[subset] = coefficient
    return coefficients


def reconstruct_risk(profile: Profile, coefficients: Mapping[Interaction, float]) -> float:
    """Evaluate a Möbius expansion at one profile."""
    _validate_profile(profile)
    upgraded = frozenset(index for index, value in enumerate(profile) if value)
    return sum(value for subset, value in coefficients.items() if subset <= upgraded)


def identify_pairwise_landscape(
    query: Callable[[Profile], float],
    n_agents: int,
    edges: Iterable[tuple[int, int]],
) -> PairwiseIdentification:
    """Exactly identify a landscape assumed sparse on a known pair graph.

    It queries the baseline, every singleton, and one profile per unique edge:
    exactly ``1 + n_agents + |E|`` queries.  Exactness is conditional on the
    absence of unlisted and higher-order interactions.
    """
    if n_agents < 1:
        raise ValueError("n_agents must be positive")
    normalized_edges: set[tuple[int, int]] = set()
    for left, right in edges:
        if left == right or min(left, right) < 0 or max(left, right) >= n_agents:
            raise ValueError("edges must join distinct valid agent indices")
        normalized_edges.add(tuple(sorted((left, right))))

    queried: list[Profile] = []

    def observe(profile: Profile) -> float:
        value = float(query(profile))
        if not 0.0 <= value <= 1.0:
            raise ValueError("queried risk must lie in [0, 1]")
        queried.append(profile)
        return value

    baseline_profile = (0,) * n_agents
    baseline = observe(baseline_profile)
    singleton_risk: dict[int, float] = {}
    coefficients: dict[Interaction, float] = {frozenset(): baseline}
    for index in range(n_agents):
        profile = profile_for_subset(n_agents, (index,))
        singleton_risk[index] = observe(profile)
        coefficients[frozenset((index,))] = singleton_risk[index] - baseline
    for left, right in sorted(normalized_edges):
        pair_risk = observe(profile_for_subset(n_agents, (left, right)))
        coefficients[frozenset((left, right))] = (
            pair_risk - singleton_risk[left] - singleton_risk[right] + baseline
        )

    reconstructed = {
        profile: reconstruct_risk(profile, coefficients)
        for profile in binary_profiles(n_agents)
    }
    return PairwiseIdentification(coefficients, reconstructed, tuple(queried))


def all_monotone_paths(n_agents: int) -> tuple[tuple[Profile, ...], ...]:
    """Enumerate paths that upgrade exactly one agent at every transition."""
    if n_agents < 1:
        raise ValueError("n_agents must be positive")
    paths: list[tuple[Profile, ...]] = []
    for order in permutations(range(n_agents)):
        current = [0] * n_agents
        path: list[Profile] = [tuple(current)]
        for index in order:
            current[index] = 1
            path.append(tuple(current))
        paths.append(tuple(path))
    return tuple(paths)


def validate_monotone_path(path: Iterable[Profile]) -> tuple[Profile, ...]:
    """Validate and materialize an all-old to all-new one-at-a-time path."""
    materialized = tuple(path)
    if len(materialized) < 2:
        raise ValueError("path needs at least two profiles")
    n_agents = len(materialized[0])
    for profile in materialized:
        _validate_profile(profile, n_agents)
    if materialized[0] != (0,) * n_agents or materialized[-1] != (1,) * n_agents:
        raise ValueError("path must run from all-old to all-new")
    for left, right in zip(materialized, materialized[1:]):
        differences = [r - l for l, r in zip(left, right)]
        if differences.count(1) != 1 or any(delta not in (0, 1) for delta in differences):
            raise ValueError("each transition must upgrade exactly one agent")
    return materialized
