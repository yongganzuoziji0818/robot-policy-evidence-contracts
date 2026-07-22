"""Frozen dimensionless G1 terrain generator and method evaluator.

Parameter ranges are constrained by public qualitative/ratio evidence, but the
generated terrains are not natural robot data.  Outputs are development-only.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
import random

from .model import (
    EdgeModel,
    TerrainGrid,
    contact_cost,
    dose_objective,
    minimum_feasible_dose,
    optimize_dose,
    solve_grid,
)


FAMILIES = ("weak_over_strong", "homogeneous_loose", "redeposition", "crater_sensitive")
METHODS = (
    "ugv_only",
    "uniform_low",
    "uniform_max",
    "sequential",
    "aerotrace",
    "aerotrace_no_abstention",
    "aerotrace_no_roughness",
    "ground_conditioner_oracle",
)


@dataclass(frozen=True)
class PlanResult:
    method: str
    total_cost: float
    success: bool
    path_length: int
    total_dose: float
    max_dose: float
    contact_component: float
    conditioning_component: float


def _edge_for_family(rng: random.Random, family: str) -> EdgeModel:
    base = rng.uniform(0.9, 1.2)
    max_dose = 1.0
    if family == "weak_over_strong":
        soft, beta = rng.uniform(2.0, 4.0), rng.uniform(1.0, 2.0)
        plume, roughness, redeposition = rng.uniform(0.4, 0.9), rng.uniform(0.1, 0.4), 0.0
        traction = rng.uniform(2.8, 4.0)
    elif family == "homogeneous_loose":
        soft, beta = rng.uniform(0.4, 1.0), rng.uniform(0.05, 0.2)
        plume, roughness, redeposition = rng.uniform(0.5, 1.0), rng.uniform(0.1, 0.3), 0.0
        traction = math.inf
    elif family == "redeposition":
        soft, beta = rng.uniform(2.0, 4.0), rng.uniform(1.0, 2.0)
        plume, roughness = rng.uniform(0.3, 0.7), rng.uniform(0.1, 0.4)
        redeposition, traction = rng.uniform(0.8, 1.8), math.inf
    elif family == "crater_sensitive":
        soft, beta = rng.uniform(2.0, 4.0), rng.uniform(1.0, 2.0)
        plume, roughness, redeposition = rng.uniform(0.3, 0.7), rng.uniform(1.5, 3.0), 0.0
        traction = math.inf
    else:
        raise ValueError("unknown frozen terrain family")
    return EdgeModel(base, soft, beta, plume, roughness, max_dose, traction, redeposition)


def make_terrain(*, seed: int, family: str, width: int = 8, height: int = 8) -> TerrainGrid:
    if family not in FAMILIES:
        raise ValueError("unknown frozen terrain family")
    rng = random.Random(seed)
    edges: dict[tuple[int, int, int, int], EdgeModel] = {}
    for y in range(height):
        for x in range(width):
            for dx, dy in ((1, 0), (0, 1)):
                target = (x + dx, y + dy)
                if target[0] >= width or target[1] >= height:
                    continue
                edge = _edge_for_family(rng, family)
                edges[(x, y, target[0], target[1])] = edge
                edges[(target[0], target[1], x, y)] = edge
    return TerrainGrid(width, height, edges)


def _edge(grid: TerrainGrid, source: tuple[int, int], target: tuple[int, int]) -> EdgeModel:
    return grid.edges[(source[0], source[1], target[0], target[1])]


def _evaluate(
    grid: TerrainGrid,
    method: str,
    path: tuple[tuple[int, int], ...],
    doses: tuple[float, ...],
    *,
    plume_multiplier: float = 1.0,
) -> PlanResult:
    if not path or len(path) != len(doses) + 1:
        return PlanResult(method, 1_000.0, False, 0, 0.0, 0.0, 1_000.0, 0.0)
    contact_total = conditioning_total = 0.0
    success = True
    for source, target, dose in zip(path[:-1], path[1:], doses):
        edge = _edge(grid, source, target)
        contact = contact_cost(edge, dose)
        if contact > edge.traction_limit:
            success = False
        contact_total += contact
        conditioning_total += plume_multiplier * edge.plume_cost * dose
    total = contact_total + conditioning_total
    if not success:
        total += 1_000.0
    return PlanResult(
        method,
        total,
        success,
        len(doses),
        sum(doses),
        max(doses, default=0.0),
        contact_total,
        conditioning_total,
    )


def _nominal_sequential(grid: TerrainGrid) -> tuple[tuple[tuple[int, int], ...], tuple[float, ...]]:
    unconstrained = TerrainGrid(
        grid.width,
        grid.height,
        {key: replace(edge, traction_limit=math.inf) for key, edge in grid.edges.items()},
    )
    _, path, _ = solve_grid(unconstrained, (0, 0), (grid.width - 1, grid.height - 1), mode="ugv_only")
    doses = []
    for source, target in zip(path[:-1], path[1:]):
        edge = _edge(grid, source, target)
        dose = max(optimize_dose(edge), minimum_feasible_dose(edge))
        doses.append(dose)
    return path, tuple(doses)


def run_method(grid: TerrainGrid, method: str) -> PlanResult:
    if method not in METHODS:
        raise ValueError("unknown frozen G1 method")
    start, goal = (0, 0), (grid.width - 1, grid.height - 1)
    if method in {"ugv_only", "uniform_low", "uniform_max", "aerotrace"}:
        _, path, doses = solve_grid(grid, start, goal, mode=method)
        return _evaluate(grid, method, path, doses)
    if method == "aerotrace_no_roughness":
        _, path, doses = solve_grid(grid, start, goal, mode="no_roughness")
        return _evaluate(grid, method, path, doses)
    if method == "sequential":
        path, doses = _nominal_sequential(grid)
        return _evaluate(grid, method, path, doses)
    if method == "aerotrace_no_abstention":
        _, path, doses = solve_grid(grid, start, goal, mode="aerotrace")
        forced = tuple(max(dose, 0.15 * _edge(grid, a, b).max_dose) for a, b, dose in zip(path[:-1], path[1:], doses))
        return _evaluate(grid, method, path, forced)
    if method == "ground_conditioner_oracle":
        oracle_grid = TerrainGrid(
            grid.width,
            grid.height,
            {key: replace(edge, plume_cost=0.75 * edge.plume_cost) for key, edge in grid.edges.items()},
        )
        _, path, doses = solve_grid(oracle_grid, start, goal, mode="aerotrace")
        return _evaluate(grid, method, path, doses, plume_multiplier=0.75)
    raise AssertionError("unreachable method branch")

