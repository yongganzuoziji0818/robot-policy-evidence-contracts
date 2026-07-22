"""Two-dimensional joint-dynamics development model for BASTION G1."""

from __future__ import annotations

from math import cos, hypot, pi, sin, sqrt
from random import Random
from typing import Iterable

from .certificate import Halfspace, project_onto_halfspaces

Matrix = tuple[float, float, float, float]
Vector = tuple[float, float]


def matvec(matrix: Matrix, vector: Vector) -> Vector:
    return (
        matrix[0] * vector[0] + matrix[1] * vector[1],
        matrix[2] * vector[0] + matrix[3] * vector[1],
    )


def matadd(left: Matrix, right: Matrix) -> Matrix:
    return tuple(a + b for a, b in zip(left, right))  # type: ignore[return-value]


def rotate_diagonal(first: float, second: float, angle: float) -> Matrix:
    c, s = cos(angle), sin(angle)
    return (
        first * c * c + second * s * s,
        (first - second) * c * s,
        (first - second) * c * s,
        first * s * s + second * c * c,
    )


def target_matrix(
    drift: Matrix, control_gain: Vector, *, desired_decay: float,
) -> Matrix:
    if min(control_gain) <= 0 or desired_decay <= 0:
        raise ValueError("invalid gain or decay")
    return (
        -(drift[0] + desired_decay) / control_gain[0],
        -drift[1] / control_gain[0],
        -drift[2] / control_gain[1],
        -(drift[3] + desired_decay) / control_gain[1],
    )


def policy_matrix(theta: tuple[float, ...], context: float) -> Matrix:
    if len(theta) != 8:
        raise ValueError("theta must contain K0 and K1 matrices")
    return tuple(theta[index] + context * theta[index + 4] for index in range(4))  # type: ignore[return-value]


def coefficient_loss(theta: tuple[float, ...], context: float, target: Matrix) -> float:
    prediction = policy_matrix(theta, context)
    return 0.5 * sum((value - goal) ** 2 for value, goal in zip(prediction, target))


def boundary_constraints(
    *, drift: Matrix, control_gain: Vector, radius: float, context: float,
    witness_count: int, additive_gap: float, cover_margin: float,
) -> tuple[Halfspace, ...]:
    if witness_count < 4 or radius <= 0 or additive_gap < 0 or cover_margin < 0:
        raise ValueError("invalid boundary constraint design")
    constraints = []
    for index in range(witness_count):
        angle = 2.0 * pi * index / witness_count
        e = (radius * cos(angle), radius * sin(angle))
        drift_e = matvec(drift, e)
        rhs = e[0] * drift_e[0] + e[1] * drift_e[1] + additive_gap + cover_margin
        k_coeff = (
            e[0] * control_gain[0] * e[0],
            e[0] * control_gain[0] * e[1],
            e[1] * control_gain[1] * e[0],
            e[1] * control_gain[1] * e[1],
        )
        normal = tuple(-value for value in k_coeff) + tuple(
            -context * value for value in k_coeff
        )
        constraints.append(Halfspace(normal, rhs))
    return tuple(constraints)


def adapt_matrix(
    *, method: str, theta0: tuple[float, ...], old_target: Matrix,
    new_target: Matrix, old_constraints: tuple[Halfspace, ...], steps: int,
    learning_rate: float, ewc_lambda: float, replay_weight: float,
) -> tuple[float, ...]:
    theta = theta0
    if method == "always_stop":
        return theta
    for _ in range(steps):
        prediction = policy_matrix(theta, 1.0)
        error = tuple(value - target for value, target in zip(prediction, new_target))
        gradient = list(error + error)
        if method == "ewc":
            gradient = [
                grad + ewc_lambda * (value - initial)
                for grad, value, initial in zip(gradient, theta, theta0)
            ]
        elif method == "replay":
            for index in range(4):
                gradient[index] += replay_weight * (theta[index] - old_target[index])
        candidate = tuple(
            value - learning_rate * grad for value, grad in zip(theta, gradient)
        )
        if method in {"bastion", "bastion_no_gap", "bastion_sparse"}:
            theta = project_onto_halfspaces(
                candidate, old_constraints, tolerance=1e-9, max_passes=2_000
            )
        elif method in {"fine_tune", "ewc", "replay"}:
            theta = candidate
        else:
            raise ValueError(f"unknown method: {method}")
    return theta


def robust_certificate_slack(
    theta: tuple[float, ...], *, drift: Matrix, control_gain: Vector,
    radius: float, context: float, disturbance_bound: float,
    evaluation_angles: int = 720,
) -> float:
    matrix = policy_matrix(theta, context)
    minimum = float("inf")
    for index in range(evaluation_angles):
        angle = 2.0 * pi * index / evaluation_angles
        e = (radius * cos(angle), radius * sin(angle))
        drift_rate = matvec(drift, e)
        action = matvec(matrix, e)
        closed = (
            drift_rate[0] + control_gain[0] * action[0],
            drift_rate[1] + control_gain[1] * action[1],
        )
        inward = -(e[0] * closed[0] + e[1] * closed[1]) - radius * disturbance_bound
        minimum = min(minimum, inward)
    return minimum


def bounded_noise_trace(
    *, seed: int, rollouts: int, steps: int, bound: float,
) -> tuple[tuple[Vector, ...], ...]:
    rng = Random(seed)
    traces = []
    for _ in range(rollouts):
        trace = []
        for _ in range(steps):
            angle = rng.uniform(0.0, 2.0 * pi)
            magnitude = bound * sqrt(rng.random())
            trace.append((magnitude * cos(angle), magnitude * sin(angle)))
        traces.append(tuple(trace))
    return tuple(traces)


def simulate_2d_recurrence(
    theta: tuple[float, ...], *, drift: Matrix, control_gain: Vector,
    radius: float, initial_radius: float, context: float, dt: float,
    noise_traces: Iterable[tuple[Vector, ...]],
) -> dict[str, float]:
    debts = []
    maxima = []
    matrix = policy_matrix(theta, context)
    for rollout_index, trace in enumerate(noise_traces):
        angle = 2.0 * pi * rollout_index / 8.0 + pi / 16.0
        state = (initial_radius * cos(angle), initial_radius * sin(angle))
        debt = 0.0
        maximum = 0.0
        for noise in trace:
            drift_rate = matvec(drift, state)
            action = matvec(matrix, state)
            state = (
                state[0] + dt * (drift_rate[0] + control_gain[0] * action[0] + noise[0]),
                state[1] + dt * (drift_rate[1] + control_gain[1] * action[1] + noise[1]),
            )
            violation = max(hypot(*state) - radius, 0.0)
            debt += dt * violation
            maximum = max(maximum, violation)
        debts.append(debt)
        maxima.append(maximum)
    return {
        "mean_safety_debt": sum(debts) / len(debts),
        "max_safety_debt": max(debts),
        "max_violation": max(maxima),
    }

