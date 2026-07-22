"""Finite-sample bounds used by selection-valid evidence checks."""

from __future__ import annotations

from math import log, sqrt
from typing import Mapping


def hoeffding_upper_bound(failures: int, trials: int, alpha: float) -> float:
    """Return a one-sided Hoeffding upper bound for a Bernoulli risk.

    Zero trials fail closed at one. The function is dependency-free and is
    intentionally conservative; it is not a substitute for a prespecified
    sampling unit, dependence model, or target-domain transport argument.
    """
    if trials < 0 or failures < 0 or failures > trials:
        raise ValueError("require 0 <= failures <= trials")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie in (0, 1)")
    if trials == 0:
        return 1.0
    estimate = failures / trials
    return min(1.0, estimate + sqrt(log(1.0 / alpha) / (2.0 * trials)))


def bonferroni_hoeffding_upper_bounds(
    counts: Mapping[str, tuple[int, int]], *, familywise_alpha: float
) -> dict[str, float]:
    """Simultaneously bound several prespecified Bernoulli risks.

    The policy or endpoint family must be frozen before inspecting outcomes.
    An empty family is rejected because it cannot support a decision claim.
    """
    if not counts:
        raise ValueError("counts must contain at least one prespecified endpoint")
    if not 0.0 < familywise_alpha < 1.0:
        raise ValueError("familywise_alpha must lie in (0, 1)")
    per_endpoint_alpha = familywise_alpha / len(counts)
    return {
        name: hoeffding_upper_bound(failures, trials, per_endpoint_alpha)
        for name, (failures, trials) in counts.items()
    }
