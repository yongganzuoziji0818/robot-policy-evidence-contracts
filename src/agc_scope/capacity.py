"""Capacity-matched detector operating points for SCOPE-v8.

The module encodes only the single-zone M/M/1 theory witness and a small
routing counterexample.  It deliberately refuses unstable queue parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite
from typing import Collection, Mapping


def _positive(value: float, *, name: str) -> float:
    result = float(value)
    if not isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return result


@dataclass(frozen=True)
class CapacityModel:
    """Single-zone detector-to-verifier capacity model.

    ``recall`` is x and the false-positive response is x**kappa.  The model
    uses a class-blind FCFS M/M/1 confirmation abstraction with a relative
    deadline.  It is a falsifiable mechanism witness, not a routing model.
    """

    true_rate: float
    clutter_rate: float
    kappa: float
    service_rate: float
    deadline: float

    def __post_init__(self) -> None:
        for name in ("true_rate", "clutter_rate", "service_rate", "deadline"):
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))
        kappa = _positive(self.kappa, name="kappa")
        if kappa <= 1.0:
            raise ValueError("kappa must exceed one")
        object.__setattr__(self, "kappa", kappa)

    @staticmethod
    def _recall(value: float) -> float:
        recall = float(value)
        if not isfinite(recall) or not 0.0 <= recall <= 1.0:
            raise ValueError("recall must lie in [0, 1]")
        return recall

    def alert_rate(self, recall: float) -> float:
        x = self._recall(recall)
        return self.true_rate * x + self.clutter_rate * x**self.kappa

    def alert_rate_derivative(self, recall: float) -> float:
        x = self._recall(recall)
        return self.true_rate + self.kappa * self.clutter_rate * x ** (self.kappa - 1.0)

    def deadline_true_throughput(self, recall: float) -> float:
        """Return timely true-confirmation throughput for a stable point."""

        x = self._recall(recall)
        load = self.alert_rate(x)
        if load >= self.service_rate:
            raise ValueError("unstable operating point")
        timely = 1.0 - exp(-self.deadline * (self.service_rate - load))
        return self.true_rate * x * timely

    def stationarity_residual(self, recall: float) -> float:
        """Return H(x), whose unique zero is the interior optimum."""

        x = self._recall(recall)
        load = self.alert_rate(x)
        if load > self.service_rate:
            raise ValueError("stationarity residual is outside the stable closure")
        delta = self.service_rate - load
        return (
            exp(self.deadline * delta)
            - 1.0
            - self.deadline * x * self.alert_rate_derivative(x)
        )

    def stable_recall_cap(self, *, tolerance: float = 1e-12) -> float:
        """Return the closure of recalls satisfying alert_rate < service_rate."""

        if tolerance <= 0.0:
            raise ValueError("tolerance must be positive")
        if self.alert_rate(1.0) <= self.service_rate:
            return 1.0
        lo, hi = 0.0, 1.0
        while hi - lo > tolerance:
            mid = (lo + hi) / 2.0
            if self.alert_rate(mid) < self.service_rate:
                lo = mid
            else:
                hi = mid
        # Return the stable side of the bracket.  The midpoint can round to
        # the overloaded side and must not be fed to fail-closed evaluators.
        return lo

    def optimal_recall(self, *, tolerance: float = 1e-12) -> float:
        """Solve the unique capacity-matched operating point by bisection."""

        cap = self.stable_recall_cap(tolerance=tolerance)
        if cap == 1.0 and self.stationarity_residual(1.0) >= 0.0:
            return 1.0
        lo, hi = 0.0, cap
        if self.stationarity_residual(lo) <= 0.0:
            raise RuntimeError("invalid positive derivative at zero")
        if self.stationarity_residual(hi) >= 0.0:
            raise RuntimeError("interior optimum was not bracketed")
        while hi - lo > tolerance:
            mid = (lo + hi) / 2.0
            if self.stationarity_residual(mid) > 0.0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0


def class_blind_true_service_upper(
    *, true_alert_rate: float, false_alert_rate: float, service_rate: float
) -> float:
    """Upper bound on true service throughput under class-blind saturation."""

    true_rate = _positive(true_alert_rate, name="true_alert_rate")
    false_rate = _positive(false_alert_rate, name="false_alert_rate")
    service = _positive(service_rate, name="service_rate")
    total = true_rate + false_rate
    return min(true_rate, service * true_rate / total)


def route_value(
    available: Collection[str],
    feasible_tours: Collection[Collection[str]],
    weights: Mapping[str, float],
) -> float:
    """Return the maximum weight of an available feasible tour."""

    available_set = set(available)
    best = 0.0
    for tour in feasible_tours:
        tour_set = set(tour)
        if tour_set <= available_set:
            best = max(best, sum(float(weights[node]) for node in tour_set))
    return best


def routing_non_submodular_witness() -> tuple[float, float]:
    """Return the two marginals in the west/east routing counterexample."""

    tours = ((), ("a",), ("b",), ("c",), ("b", "c"))
    weights = {"a": 1.0, "b": 1.0, "c": 1.0}
    small = route_value({"a", "c"}, tours, weights) - route_value(
        {"a"}, tours, weights
    )
    large = route_value({"a", "b", "c"}, tours, weights) - route_value(
        {"a", "b"}, tours, weights
    )
    return small, large
