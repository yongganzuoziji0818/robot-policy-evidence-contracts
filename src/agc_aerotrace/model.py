"""Deterministic AeroTrace model used by frozen remote development runners.

The model is deliberately small and auditable.  It is not a CFD--DEM model and
must never be described as natural air--ground interaction evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Iterable


@dataclass(frozen=True)
class EdgeModel:
    base_cost: float
    soft_cost: float
    exposure_rate: float
    plume_cost: float
    roughness_cost: float
    max_dose: float
    traction_limit: float = math.inf
    redeposition_cost: float = 0.0

    def validate(self) -> None:
        positive = (
            self.base_cost,
            self.soft_cost,
            self.exposure_rate,
            self.plume_cost,
            self.roughness_cost,
            self.max_dose,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in positive):
            raise ValueError("edge parameters must be finite and positive")
        if not math.isfinite(self.redeposition_cost) or self.redeposition_cost < 0.0:
            raise ValueError("redeposition cost must be finite and non-negative")


def contact_cost(edge: EdgeModel, dose: float, *, ignore_roughness: bool = False) -> float:
    edge.validate()
    if not 0.0 <= dose <= edge.max_dose:
        raise ValueError("dose outside frozen edge interval")
    roughness = 0.0 if ignore_roughness else edge.roughness_cost * dose * dose
    return (
        edge.base_cost
        + edge.soft_cost * math.exp(-edge.exposure_rate * dose)
        + roughness
        + edge.redeposition_cost * dose
    )


def dose_objective(edge: EdgeModel, dose: float, *, ignore_roughness: bool = False) -> float:
    return contact_cost(edge, dose, ignore_roughness=ignore_roughness) + edge.plume_cost * dose


def objective_derivative(edge: EdgeModel, dose: float, *, ignore_roughness: bool = False) -> float:
    roughness = 0.0 if ignore_roughness else 2.0 * edge.roughness_cost * dose
    return (
        edge.plume_cost
        + edge.redeposition_cost
        + roughness
        - edge.soft_cost * edge.exposure_rate * math.exp(-edge.exposure_rate * dose)
    )


def contact_derivative(edge: EdgeModel, dose: float) -> float:
    return (
        edge.redeposition_cost
        + 2.0 * edge.roughness_cost * dose
        - edge.soft_cost * edge.exposure_rate * math.exp(-edge.exposure_rate * dose)
    )


def minimum_feasible_dose(edge: EdgeModel) -> float:
    """Smallest dose satisfying the deterministic traction limit."""
    if contact_cost(edge, 0.0) <= edge.traction_limit:
        return 0.0
    if contact_derivative(edge, 0.0) >= 0.0:
        return math.inf
    if contact_derivative(edge, edge.max_dose) <= 0.0:
        minimizer = edge.max_dose
    else:
        low, high = 0.0, edge.max_dose
        for _ in range(100):
            middle = 0.5 * (low + high)
            if contact_derivative(edge, middle) < 0.0:
                low = middle
            else:
                high = middle
        minimizer = 0.5 * (low + high)
    if contact_cost(edge, minimizer) > edge.traction_limit:
        return math.inf
    low, high = 0.0, minimizer
    for _ in range(100):
        middle = 0.5 * (low + high)
        if contact_cost(edge, middle) > edge.traction_limit:
            low = middle
        else:
            high = middle
    return high


def optimize_dose(edge: EdgeModel, *, ignore_roughness: bool = False) -> float:
    """Return the unique constrained optimum using monotone derivative bisection."""
    edge.validate()
    if objective_derivative(edge, 0.0, ignore_roughness=ignore_roughness) >= 0.0:
        return 0.0
    if objective_derivative(edge, edge.max_dose, ignore_roughness=ignore_roughness) <= 0.0:
        return edge.max_dose
    low, high = 0.0, edge.max_dose
    for _ in range(100):
        middle = 0.5 * (low + high)
        if objective_derivative(edge, middle, ignore_roughness=ignore_roughness) < 0.0:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


@dataclass(frozen=True)
class TerrainGrid:
    width: int
    height: int
    edges: dict[tuple[int, int, int, int], EdgeModel]

    def neighbors(self, node: tuple[int, int]) -> Iterable[tuple[tuple[int, int], EdgeModel]]:
        x, y = node
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            target = (x + dx, y + dy)
            if not (0 <= target[0] < self.width and 0 <= target[1] < self.height):
                continue
            key = (x, y, target[0], target[1])
            if key in self.edges:
                yield target, self.edges[key]


def solve_grid(
    grid: TerrainGrid,
    start: tuple[int, int],
    goal: tuple[int, int],
    *,
    mode: str = "aerotrace",
) -> tuple[float, tuple[tuple[int, int], ...], tuple[float, ...]]:
    """Shortest path under one of the frozen per-edge dose policies."""
    if mode not in {"ugv_only", "aerotrace", "uniform_low", "uniform_max", "no_roughness"}:
        raise ValueError("unknown frozen planning mode")
    distance = {start: 0.0}
    predecessor: dict[tuple[int, int], tuple[tuple[int, int], float]] = {}
    queue: list[tuple[float, tuple[int, int]]] = [(0.0, start)]
    while queue:
        cost, node = heapq.heappop(queue)
        if cost != distance.get(node):
            continue
        if node == goal:
            break
        for target, edge in grid.neighbors(node):
            if mode == "ugv_only":
                dose = 0.0
            elif mode == "uniform_low":
                dose = 0.25 * edge.max_dose
            elif mode == "uniform_max":
                dose = edge.max_dose
            elif mode == "no_roughness":
                dose = optimize_dose(edge, ignore_roughness=True)
            else:
                dose = optimize_dose(edge)
            feasible_dose = minimum_feasible_dose(edge)
            if mode in {"aerotrace", "no_roughness"}:
                dose = max(dose, feasible_dose)
            if not math.isfinite(dose) or contact_cost(edge, dose) > edge.traction_limit:
                continue
            edge_cost = dose_objective(edge, dose)
            candidate = cost + edge_cost
            if candidate < distance.get(target, math.inf):
                distance[target] = candidate
                predecessor[target] = (node, dose)
                heapq.heappush(queue, (candidate, target))
    if goal not in distance:
        return math.inf, (), ()
    nodes, doses = [goal], []
    current = goal
    while current != start:
        previous, dose = predecessor[current]
        nodes.append(previous)
        doses.append(dose)
        current = previous
    nodes.reverse()
    doses.reverse()
    return distance[goal], tuple(nodes), tuple(doses)
