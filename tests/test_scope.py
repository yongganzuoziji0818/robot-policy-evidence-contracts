from __future__ import annotations

import unittest

from agc_scope import (
    CapacityModel,
    class_blind_true_service_upper,
    routing_non_submodular_witness,
)


class ScopeTheoryTests(unittest.TestCase):
    def test_capacity_optimum_is_unique_and_stable(self) -> None:
        model = CapacityModel(
            true_rate=0.2,
            clutter_rate=4.0,
            kappa=2.0,
            service_rate=1.0,
            deadline=3.0,
        )
        optimum = model.optimal_recall()
        self.assertGreater(optimum, 0.0)
        self.assertLess(optimum, model.stable_recall_cap())
        self.assertAlmostEqual(model.stationarity_residual(optimum), 0.0, places=9)
        eps = 1e-4
        center = model.deadline_true_throughput(optimum)
        self.assertGreater(center, model.deadline_true_throughput(optimum - eps))
        self.assertGreater(center, model.deadline_true_throughput(optimum + eps))

    def test_full_recall_is_boundary_optimum_when_capacity_is_abundant(self) -> None:
        model = CapacityModel(
            true_rate=0.1,
            clutter_rate=0.1,
            kappa=2.0,
            service_rate=10.0,
            deadline=1.0,
        )
        self.assertEqual(model.optimal_recall(), 1.0)

    def test_comparative_statics_match_theorem(self) -> None:
        base = CapacityModel(0.2, 4.0, 2.0, 1.0, 3.0).optimal_recall()
        more_capacity = CapacityModel(0.2, 4.0, 2.0, 1.2, 3.0).optimal_recall()
        more_clutter = CapacityModel(0.2, 6.0, 2.0, 1.0, 3.0).optimal_recall()
        self.assertGreater(more_capacity, base)
        self.assertLess(more_clutter, base)

    def test_unstable_operating_point_fails_closed(self) -> None:
        model = CapacityModel(0.2, 4.0, 2.0, 1.0, 3.0)
        with self.assertRaisesRegex(ValueError, "unstable"):
            model.deadline_true_throughput(1.0)

    def test_class_blind_true_service_is_diluted_by_false_alerts(self) -> None:
        low = class_blind_true_service_upper(
            true_alert_rate=1.0, false_alert_rate=1.0, service_rate=1.0
        )
        high = class_blind_true_service_upper(
            true_alert_rate=1.0, false_alert_rate=99.0, service_rate=1.0
        )
        self.assertEqual(low, 0.5)
        self.assertEqual(high, 0.01)

    def test_routing_value_violates_diminishing_returns(self) -> None:
        small, large = routing_non_submodular_witness()
        self.assertEqual(small, 0.0)
        self.assertEqual(large, 1.0)
        self.assertLess(small, large)

    def test_invalid_parameters_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CapacityModel(0.2, 4.0, 1.0, 1.0, 3.0)
        with self.assertRaises(ValueError):
            CapacityModel(0.2, 4.0, 2.0, 1.0, -3.0)


if __name__ == "__main__":
    unittest.main()

