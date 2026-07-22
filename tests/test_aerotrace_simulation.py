from __future__ import annotations

import unittest

from agc_aerotrace import FAMILIES, METHODS, make_terrain, run_method


class AeroTraceSimulationTests(unittest.TestCase):
    def test_all_methods_are_deterministic_and_finite(self) -> None:
        for family in FAMILIES:
            grid = make_terrain(seed=101, family=family)
            for method in METHODS:
                first = run_method(grid, method)
                second = run_method(grid, method)
                self.assertEqual(first, second)
                self.assertGreaterEqual(first.total_cost, 0.0)

    def test_homogeneous_family_allows_abstention(self) -> None:
        grid = make_terrain(seed=111, family="homogeneous_loose")
        result = run_method(grid, "aerotrace")
        self.assertEqual(result.total_dose, 0.0)

    def test_unknown_family_and_method_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            make_terrain(seed=1, family="renamed")
        grid = make_terrain(seed=1, family="weak_over_strong")
        with self.assertRaises(ValueError):
            run_method(grid, "renamed")


if __name__ == "__main__":
    unittest.main()
