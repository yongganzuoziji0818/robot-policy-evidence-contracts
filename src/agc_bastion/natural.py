"""Non-sealed physical lineage model for the one-shot BASTION N0 screen."""

from __future__ import annotations

from dataclasses import dataclass

from .certificate import Halfspace, project_onto_halfspaces


@dataclass(frozen=True)
class Regime:
    outward_drift: float
    control_gain: float
    context: float

    def __post_init__(self) -> None:
        if self.outward_drift < 0 or self.control_gain <= 0:
            raise ValueError("invalid physical regime")


@dataclass(frozen=True)
class Campaign:
    campaign_id: str
    topology: str
    shift_axis: str
    lineage: int
    old: Regime
    new: Regime


def target_coefficient(regime: Regime, *, desired_decay: float) -> float:
    """Action coefficient yielding ``e_dot=-desired_decay*e``."""

    if desired_decay <= 0:
        raise ValueError("desired decay must be positive")
    return -(regime.outward_drift + desired_decay) / regime.control_gain


def policy_coefficient(theta: tuple[float, float], context: float) -> float:
    return theta[0] + theta[1] * context


def current_loss(
    theta: tuple[float, float], regime: Regime, *, desired_decay: float,
) -> float:
    error = policy_coefficient(theta, regime.context) - target_coefficient(
        regime, desired_decay=desired_decay
    )
    return 0.5 * error * error


def old_certificate_slack(theta: tuple[float, float], old: Regime) -> float:
    """Minimum normalized inward CBF residual at either corridor boundary."""

    coefficient = policy_coefficient(theta, old.context)
    return -(old.outward_drift + old.control_gain * coefficient)


def adapt(
    *, method: str, theta0: tuple[float, float], old: Regime, new: Regime,
    desired_decay: float, steps: int, learning_rate: float, ewc_lambda: float,
) -> tuple[float, float]:
    theta = theta0
    feature = (1.0, new.context)
    target = target_coefficient(new, desired_decay=desired_decay)
    constraint = Halfspace(
        (-old.control_gain, -old.control_gain * old.context),
        old.outward_drift,
    )
    if method == "always_stop":
        return theta
    for _ in range(steps):
        prediction = policy_coefficient(theta, new.context)
        error = prediction - target
        gradient = (error * feature[0], error * feature[1])
        if method == "ewc":
            gradient = (
                gradient[0] + ewc_lambda * (theta[0] - theta0[0]),
                gradient[1] + ewc_lambda * (theta[1] - theta0[1]),
            )
        candidate = (
            theta[0] - learning_rate * gradient[0],
            theta[1] - learning_rate * gradient[1],
        )
        if method == "bastion":
            projected = project_onto_halfspaces(candidate, (constraint,))
            theta = (projected[0], projected[1])
        elif method in {"fine_tune", "ewc"}:
            theta = candidate
        else:
            raise ValueError(f"unknown method: {method}")
    return theta


def simulate_recurrence(
    theta: tuple[float, float], regime: Regime, *, initial_distance: float,
    goal_distance: float, minimum_distance: float, maximum_distance: float,
    dt: float, steps: int,
) -> dict[str, float]:
    if not minimum_distance < initial_distance < maximum_distance:
        raise ValueError("initial distance must be strictly safe")
    distance = initial_distance
    debt = 0.0
    maximum_violation = 0.0
    coefficient = policy_coefficient(theta, regime.context)
    for _ in range(steps):
        error = distance - goal_distance
        action = coefficient * error
        distance += dt * (
            regime.outward_drift * error + regime.control_gain * action
        )
        violation = max(minimum_distance - distance, distance - maximum_distance, 0.0)
        debt += dt * violation
        maximum_violation = max(maximum_violation, violation)
    return {
        "final_distance": distance,
        "safety_debt": debt,
        "maximum_violation": maximum_violation,
    }

