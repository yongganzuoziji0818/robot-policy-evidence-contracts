from __future__ import annotations

import math
import unittest

from agc_aerotrace import (
    EdgeModel,
    TerrainGrid,
    dose_objective,
    minimum_feasible_dose,
    optimize_dose,
    solve_grid,
)


class AeroTraceModelTests(unittest.TestCase):
    def test_zero_dose_threshold(self) -> None:
        edge = EdgeModel(1.0, 1.0, 1.0, 1.2, 0.1, 2.0)
        self.assertEqual(optimize_dose(edge), 0.0)

    def test_positive_dose_strictly_improves_objective(self) -> None:
        edge = EdgeModel(1.0, 2.0, 1.5, 0.5, 0.2, 2.0)
        dose = optimize_dose(edge)
        self.assertGreater(dose, 0.0)
        self.assertLess(dose_objective(edge, dose), dose_objective(edge, 0.0))

    def test_redeposition_can_trigger_abstention(self) -> None:
        edge = EdgeModel(1.0, 1.0, 1.0, 0.2, 0.1, 2.0, redeposition_cost=1.0)
        self.assertEqual(optimize_dose(edge), 0.0)

    def test_unknown_mode_fails_closed(self) -> None:
        edge = EdgeModel(1.0, 1.0, 1.0, 0.2, 0.1, 2.0)
        grid = TerrainGrid(2, 1, {(0, 0, 1, 0): edge})
        with self.assertRaises(ValueError):
            solve_grid(grid, (0, 0), (1, 0), mode="renamed")

    def test_minimum_feasible_dose_recovers_traction(self) -> None:
        edge = EdgeModel(1.0, 3.0, 2.0, 0.2, 0.05, 2.0, traction_limit=2.5)
        dose = minimum_feasible_dose(edge)
        self.assertGreater(dose, 0.0)
        self.assertLessEqual(abs(dose_objective(edge, dose) - edge.plume_cost * dose - 2.5), 1e-10)

    def test_joint_path_can_differ_from_ugv_only(self) -> None:
        direct = EdgeModel(1.0, 5.0, 2.0, 0.2, 0.1, 2.0)
        detour = EdgeModel(1.0, 0.5, 0.2, 0.2, 0.1, 2.0)
        edges = {
            (0, 0, 1, 0): direct,
            (1, 0, 2, 0): direct,
            (0, 0, 0, 1): detour,
            (0, 1, 1, 1): detour,
            (1, 1, 2, 1): detour,
            (2, 1, 2, 0): detour,
        }
        grid = TerrainGrid(3, 2, edges)
        ugv = solve_grid(grid, (0, 0), (2, 0), mode="ugv_only")
        joint = solve_grid(grid, (0, 0), (2, 0), mode="aerotrace")
        self.assertTrue(math.isfinite(ugv[0]))
        self.assertTrue(math.isfinite(joint[0]))
        self.assertNotEqual(ugv[1], joint[1])


if __name__ == "__main__":
    unittest.main()
