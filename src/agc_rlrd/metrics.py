"""Pre-specified safety-debt and non-stationarity diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class SafetyDebtSummary:
    cumulative_debt: float
    normalized_debt: float
    maximum_risk: float
    hard_violation_count: int
    hard_violation_exposure: float


def summarize_safety_debt(
    risk: Sequence[float],
    exposure: Sequence[float],
    *,
    tau_target: float,
    tau_hard: float,
) -> SafetyDebtSummary:
    """Summarize excess failure exposure without conflating target and cap."""
    if len(risk) != len(exposure) or not risk:
        raise ValueError("risk and exposure must be nonempty and equally sized")
    if not 0.0 <= tau_target < tau_hard <= 1.0:
        raise ValueError("require 0 <= tau_target < tau_hard <= 1")
    if any(not 0.0 <= float(value) <= 1.0 for value in risk):
        raise ValueError("risk must lie in [0, 1]")
    if any(float(value) < 0.0 for value in exposure):
        raise ValueError("exposure must be nonnegative")
    cumulative = sum(
        float(weight) * max(float(value) - tau_target, 0.0)
        for value, weight in zip(risk, exposure)
    )
    total_exposure = sum(float(value) for value in exposure)
    violations = [float(value) > tau_hard for value in risk]
    return SafetyDebtSummary(
        cumulative_debt=cumulative,
        normalized_debt=cumulative / total_exposure if total_exposure else 0.0,
        maximum_risk=max(float(value) for value in risk),
        hard_violation_count=sum(violations),
        hard_violation_exposure=sum(
            float(weight) for weight, violated in zip(exposure, violations) if violated
        ),
    )


def adaptation_delay(
    risk_after_change: Sequence[float],
    *,
    tau_target: float,
    consecutive: int = 1,
) -> int | None:
    """First zero-based step starting a sustained return to target risk.

    This is a descriptive development diagnostic.  Inferential use requires a
    pre-registered risk estimator and censoring model.
    """
    if not 0.0 <= tau_target <= 1.0:
        raise ValueError("tau_target must lie in [0, 1]")
    if consecutive < 1:
        raise ValueError("consecutive must be positive")
    values = tuple(float(value) for value in risk_after_change)
    if any(not 0.0 <= value <= 1.0 for value in values):
        raise ValueError("risk must lie in [0, 1]")
    for start in range(0, len(values) - consecutive + 1):
        if all(value <= tau_target for value in values[start : start + consecutive]):
            return start
    return None


def recurrence_regression_gap(
    prior_phase_risk: Sequence[float],
    returned_phase_risk: Sequence[float],
) -> float:
    """Risk increase when a previously seen condition recurs.

    This audits the external version generator; it is not an RLRD novelty or
    causal effect endpoint.
    """
    if not prior_phase_risk or not returned_phase_risk:
        raise ValueError("both phase samples are required")
    prior = tuple(float(value) for value in prior_phase_risk)
    returned = tuple(float(value) for value in returned_phase_risk)
    if any(not 0.0 <= value <= 1.0 for value in prior + returned):
        raise ValueError("risk must lie in [0, 1]")
    return sum(returned) / len(returned) - sum(prior) / len(prior)
