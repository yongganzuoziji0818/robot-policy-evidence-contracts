"""Fresh-split, simultaneous upper-bound certification for a locked path."""

from __future__ import annotations

from dataclasses import dataclass
from math import log, sqrt
from typing import Mapping, Sequence

from .profiles import Profile, validate_monotone_path


@dataclass(frozen=True)
class PathCertification:
    decision: str
    reason: str
    upper_bounds: dict[Profile, float]
    cumulative_debt_upper: float
    normalized_debt_upper: float
    maximum_risk_upper: float
    familywise_alpha: float
    certification_split_id: str

    @property
    def promote(self) -> bool:
        return self.decision == "PROMOTE"


def hoeffding_upper_bound(failures: int, trials: int, alpha: float) -> float:
    """A dependency-free, finite-sample one-sided Bernoulli upper bound."""
    if trials < 0 or failures < 0 or failures > trials:
        raise ValueError("require 0 <= failures <= trials")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie in (0, 1)")
    if trials == 0:
        return 1.0
    empirical = failures / trials
    return min(1.0, empirical + sqrt(log(1.0 / alpha) / (2.0 * trials)))


def clopper_pearson_upper_bound(failures: int, trials: int, alpha: float) -> float:
    """Exact one-sided Clopper--Pearson Bernoulli upper confidence bound."""
    if trials < 0 or failures < 0 or failures > trials:
        raise ValueError("require 0 <= failures <= trials")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie in (0, 1)")
    if trials == 0 or failures == trials:
        return 1.0
    if failures == 0:
        return 1.0 - alpha ** (1.0 / trials)
    try:
        from scipy.stats import beta
    except ImportError as error:
        raise RuntimeError("Clopper-Pearson bound requires scipy") from error
    return float(beta.ppf(1.0 - alpha, failures + 1, trials - failures))


def _upper_bound(failures: int, trials: int, alpha: float, method: str) -> float:
    if method == "hoeffding":
        return hoeffding_upper_bound(failures, trials, alpha)
    if method == "clopper_pearson":
        return clopper_pearson_upper_bound(failures, trials, alpha)
    raise ValueError(f"unknown bound method: {method}")


def certify_locked_path(
    path: Sequence[Profile],
    counts: Mapping[Profile, tuple[int, int]],
    *,
    familywise_alpha: float,
    tau_target: float,
    tau_hard: float,
    exposure_by_stage: Sequence[float],
    debt_budget: float,
    certification_split_id: str,
    discovery_split_id: str | None = None,
    bound_method: str = "hoeffding",
) -> PathCertification:
    """Certify a pre-locked path using only a named fresh data split.

    Bonferroni allocation gives simultaneous per-profile upper bounds.  This
    intentionally conservative G0 implementation can later be replaced only
    after a pre-registered validity comparison.
    """
    locked_path = validate_monotone_path(path)
    if not certification_split_id.strip():
        raise ValueError("certification_split_id is required")
    if discovery_split_id is not None and certification_split_id == discovery_split_id:
        raise ValueError("discovery and certification splits must be distinct")
    if not 0.0 < familywise_alpha < 1.0:
        raise ValueError("familywise_alpha must lie in (0, 1)")
    if not 0.0 <= tau_target < tau_hard <= 1.0:
        raise ValueError("require 0 <= tau_target < tau_hard <= 1")
    if debt_budget < 0:
        raise ValueError("debt_budget must be nonnegative")
    exposures = tuple(float(value) for value in exposure_by_stage)
    if len(exposures) != len(locked_path) or any(value < 0 for value in exposures):
        raise ValueError("one nonnegative exposure is required per path profile")

    per_profile_alpha = familywise_alpha / len(locked_path)
    upper_bounds: dict[Profile, float] = {}
    for profile in locked_path:
        failures, trials = counts.get(profile, (0, 0))
        upper_bounds[profile] = _upper_bound(
            failures, trials, per_profile_alpha, bound_method
        )

    maximum = max(upper_bounds.values())
    debt_upper = sum(
        exposure * max(upper_bounds[profile] - tau_target, 0.0)
        for profile, exposure in zip(locked_path, exposures)
    )
    total_exposure = sum(exposures)
    normalized = debt_upper / total_exposure if total_exposure else 0.0

    if maximum > tau_hard:
        decision, reason = "HOLD", "simultaneous hard-risk upper bound exceeded"
    elif debt_upper > debt_budget:
        decision, reason = "HOLD", "cumulative safety-debt upper bound exceeded"
    else:
        decision, reason = "PROMOTE", "both simultaneous risk and debt gates passed"
    return PathCertification(
        decision=decision,
        reason=reason,
        upper_bounds=upper_bounds,
        cumulative_debt_upper=debt_upper,
        normalized_debt_upper=normalized,
        maximum_risk_upper=maximum,
        familywise_alpha=familywise_alpha,
        certification_split_id=certification_split_id,
    )
