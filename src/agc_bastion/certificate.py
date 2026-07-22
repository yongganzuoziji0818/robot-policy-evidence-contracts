"""Fail-closed finite-cover certificate-retention utilities.

The functions in this module implement only deterministic analytic checks for
the BASTION-v7.41 theory gate.  They are not an experiment runner.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable, Sequence


def _vector(values: Sequence[float], *, name: str) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if not result:
        raise ValueError(f"{name} must be non-empty")
    return result


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("dimension mismatch")
    return sum(a * b for a, b in zip(left, right))


def _norm(values: Sequence[float]) -> float:
    return sqrt(_dot(values, values))


def support_box(
    coefficient: Sequence[float],
    lower: Sequence[float],
    upper: Sequence[float],
) -> float:
    """Return ``sup_{u in [lower, upper]} coefficient.T @ u`` exactly."""

    a = _vector(coefficient, name="coefficient")
    lo = _vector(lower, name="lower")
    hi = _vector(upper, name="upper")
    if not (len(a) == len(lo) == len(hi)):
        raise ValueError("dimension mismatch")
    if any(l > h for l, h in zip(lo, hi)):
        raise ValueError("box lower bound exceeds upper bound")
    return sum(max(ai * l, ai * h) for ai, l, h in zip(a, lo, hi))


def support_lipschitz_bound(
    *, scalar_term_lipschitz: float, control_coefficient_lipschitz: float,
    control_radius: float,
) -> float:
    """Lipschitz bound for ``b(x) + sigma_U(a(x))``.

    For a compact control set contained in an Euclidean ball of radius R,
    ``|sigma_U(a)-sigma_U(a')| <= R ||a-a'||``.
    """

    values = (scalar_term_lipschitz, control_coefficient_lipschitz, control_radius)
    if any(value < 0 for value in values):
        raise ValueError("Lipschitz constants and radius must be nonnegative")
    return scalar_term_lipschitz + control_radius * control_coefficient_lipschitz


def model_gap_bound(
    *, gradient_norm_bound: float, drift_error_bound: float,
    control_matrix_error_bound: float, control_radius: float,
) -> float:
    """Bound the true/estimated CBF residual gap.

    If ``||f-fhat|| <= eps_f``, ``||g-ghat||_op <= eps_g`` and
    ``||u|| <= R``, the gap is at most
    ``||grad h|| (eps_f + eps_g R)``.
    """

    values = (
        gradient_norm_bound,
        drift_error_bound,
        control_matrix_error_bound,
        control_radius,
    )
    if any(value < 0 for value in values):
        raise ValueError("model-gap inputs must be nonnegative")
    return gradient_norm_bound * (
        drift_error_bound + control_matrix_error_bound * control_radius
    )


def certified_boundary_lower_bound(
    witness_residuals: Iterable[float], *, lipschitz: float,
    cover_radius: float, model_gap: float = 0.0, numerical_tolerance: float = 0.0,
) -> float:
    """Lower-bound the true residual over a covered continuous boundary."""

    residuals = tuple(float(value) for value in witness_residuals)
    if not residuals:
        raise ValueError("at least one witness residual is required")
    values = (lipschitz, cover_radius, model_gap, numerical_tolerance)
    if any(value < 0 for value in values):
        raise ValueError("certificate margins must be nonnegative")
    return min(residuals) - lipschitz * cover_radius - model_gap - numerical_tolerance


@dataclass(frozen=True)
class Halfspace:
    """Closed halfspace ``normal.T @ theta >= lower_bound``."""

    normal: tuple[float, ...]
    lower_bound: float

    def __init__(self, normal: Sequence[float], lower_bound: float) -> None:
        vector = _vector(normal, name="normal")
        if _norm(vector) == 0:
            raise ValueError("halfspace normal must be nonzero")
        object.__setattr__(self, "normal", vector)
        object.__setattr__(self, "lower_bound", float(lower_bound))

    def slack(self, theta: Sequence[float]) -> float:
        return _dot(self.normal, theta) - self.lower_bound


def project_onto_halfspaces(
    theta: Sequence[float], constraints: Sequence[Halfspace], *,
    tolerance: float = 1e-10, max_passes: int = 10_000,
) -> tuple[float, ...]:
    """Cyclically project onto retention halfspaces and verify fail-closed.

    This deterministic utility is suitable for small analytic witnesses.  A
    production implementation may replace it with a QP, but must retain the
    final explicit feasibility check.
    """

    point = list(_vector(theta, name="theta"))
    if tolerance < 0 or max_passes <= 0:
        raise ValueError("invalid projection tolerance or pass limit")
    if any(len(constraint.normal) != len(point) for constraint in constraints):
        raise ValueError("dimension mismatch")
    for _ in range(max_passes):
        largest_violation = 0.0
        for constraint in constraints:
            slack = constraint.slack(point)
            if slack < -tolerance:
                normal_sq = _dot(constraint.normal, constraint.normal)
                scale = -slack / normal_sq
                point = [
                    value + scale * normal
                    for value, normal in zip(point, constraint.normal)
                ]
                largest_violation = max(largest_violation, -slack)
        if largest_violation <= tolerance:
            break
    result = tuple(point)
    failed = [constraint.slack(result) for constraint in constraints if constraint.slack(result) < -tolerance]
    if failed:
        raise RuntimeError("retention projection did not reach a feasible point")
    return result


@dataclass(frozen=True)
class PairwiseCorridor:
    """Joint UAV--UGV first-order separation/connectivity certificate.

    The signed relative coordinate is ``d = x_uav - x_ugv`` and must remain in
    ``[minimum_distance, maximum_distance]``.  Its derivative depends on both
    agents' actions, so the certificate is genuinely joint rather than an
    agent-wise cost decomposition.
    """

    minimum_distance: float
    maximum_distance: float
    alpha: float

    def __post_init__(self) -> None:
        if self.minimum_distance < 0:
            raise ValueError("minimum distance must be nonnegative")
        if self.maximum_distance <= self.minimum_distance:
            raise ValueError("maximum distance must exceed minimum distance")
        if self.alpha <= 0:
            raise ValueError("alpha must be positive")

    def residuals(
        self, *, distance: float, uav_action: float, ugv_action: float,
        uav_gain: float, ugv_gain: float,
    ) -> tuple[float, float]:
        relative_rate = uav_gain * uav_action - ugv_gain * ugv_action
        lower = relative_rate + self.alpha * (distance - self.minimum_distance)
        upper = -relative_rate + self.alpha * (self.maximum_distance - distance)
        return lower, upper

    def feasible_relative_rate_interval(
        self, *, distance: float, margin: float = 0.0,
    ) -> tuple[float, float]:
        if margin < 0:
            raise ValueError("margin must be nonnegative")
        lower = -self.alpha * (distance - self.minimum_distance) + margin
        upper = self.alpha * (self.maximum_distance - distance) - margin
        return lower, upper

    def has_box_feasible_action(
        self, *, distance: float, uav_gain: float, ugv_gain: float,
        uav_bounds: tuple[float, float], ugv_bounds: tuple[float, float],
        margin: float = 0.0,
    ) -> bool:
        if uav_bounds[0] > uav_bounds[1] or ugv_bounds[0] > ugv_bounds[1]:
            raise ValueError("invalid action bounds")
        required_lo, required_hi = self.feasible_relative_rate_interval(
            distance=distance, margin=margin
        )
        attainable = (
            uav_gain * uav_bounds[0] - ugv_gain * ugv_bounds[1],
            uav_gain * uav_bounds[1] - ugv_gain * ugv_bounds[0],
        )
        attainable_lo, attainable_hi = min(attainable), max(attainable)
        return max(required_lo, attainable_lo) <= min(required_hi, attainable_hi)

