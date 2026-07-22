"""Margin-aware certificates for prespecified robot-policy rankings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class PairCertificate:
    higher: str
    lower: str
    estimated_gap: float
    required_gap: float
    certified: bool


@dataclass(frozen=True)
class RankingCertificate:
    ordered_policies: tuple[str, ...]
    adjacent_pairs: tuple[PairCertificate, ...]

    @property
    def fully_certified(self) -> bool:
        return bool(self.adjacent_pairs) and all(pair.certified for pair in self.adjacent_pairs)

    @property
    def unresolved_pairs(self) -> tuple[PairCertificate, ...]:
        return tuple(pair for pair in self.adjacent_pairs if not pair.certified)


def certify_ranking(
    estimates: Mapping[str, float], error_bounds: Mapping[str, float]
) -> RankingCertificate:
    """Certify an estimated total order using per-policy absolute error bounds.

    For policies ``a`` and ``b``, an estimated order is certified only when
    ``estimate[a] - estimate[b] > error[a] + error[b]``. Equalities remain
    unresolved. The check addresses a fixed, prespecified set; adaptive policy
    generation requires an additional selection-validity argument.
    """
    if len(estimates) < 2:
        raise ValueError("at least two policies are required")
    if set(estimates) != set(error_bounds):
        raise ValueError("estimates and error_bounds must name the same policies")
    if any(float(bound) < 0.0 for bound in error_bounds.values()):
        raise ValueError("error bounds must be nonnegative")
    if any(not 0.0 <= float(value) <= 1.0 for value in estimates.values()):
        raise ValueError("policy estimates must lie in [0, 1]")

    ordered = tuple(sorted(estimates, key=lambda name: (-float(estimates[name]), name)))
    pairs: list[PairCertificate] = []
    for higher, lower in zip(ordered, ordered[1:]):
        gap = float(estimates[higher]) - float(estimates[lower])
        required = float(error_bounds[higher]) + float(error_bounds[lower])
        pairs.append(PairCertificate(higher, lower, gap, required, gap > required))
    return RankingCertificate(ordered, tuple(pairs))
