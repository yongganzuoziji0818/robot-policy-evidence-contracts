from __future__ import annotations

import unittest

from agc_bastion import (
    Halfspace,
    PairwiseCorridor,
    certified_boundary_lower_bound,
    model_gap_bound,
    project_onto_halfspaces,
    support_box,
    support_lipschitz_bound,
)


class BastionAnalyticTests(unittest.TestCase):
    def test_box_support_is_exact(self) -> None:
        self.assertAlmostEqual(
            support_box((2.0, -3.0), (-1.0, -2.0), (4.0, 5.0)),
            14.0,
        )

    def test_support_lipschitz_bound(self) -> None:
        self.assertEqual(
            support_lipschitz_bound(
                scalar_term_lipschitz=2.0,
                control_coefficient_lipschitz=3.0,
                control_radius=4.0,
            ),
            14.0,
        )

    def test_model_gap_and_cover_margin_close_the_boundary(self) -> None:
        gap = model_gap_bound(
            gradient_norm_bound=2.0,
            drift_error_bound=0.01,
            control_matrix_error_bound=0.02,
            control_radius=3.0,
        )
        self.assertAlmostEqual(gap, 0.14)
        lower = certified_boundary_lower_bound(
            (0.51, 0.55, 0.60),
            lipschitz=1.5,
            cover_radius=0.2,
            model_gap=gap,
            numerical_tolerance=0.01,
        )
        self.assertAlmostEqual(lower, 0.06)

    def test_retention_projection_prevents_old_constraint_forgetting(self) -> None:
        old_regime = Halfspace((1.0, 1.0), 1.5)
        current_regime = Halfspace((-1.0, 2.0), 0.5)
        naive_update = (-1.0, 1.0)
        self.assertLess(old_regime.slack(naive_update), 0.0)
        retained = project_onto_halfspaces(
            naive_update, (old_regime, current_regime)
        )
        self.assertGreaterEqual(old_regime.slack(retained), -1e-10)
        self.assertGreaterEqual(current_regime.slack(retained), -1e-10)

    def test_joint_corridor_depends_on_both_agents(self) -> None:
        corridor = PairwiseCorridor(1.0, 4.0, alpha=2.0)
        first = corridor.residuals(
            distance=1.2, uav_action=0.3, ugv_action=0.1,
            uav_gain=1.0, ugv_gain=1.0,
        )
        second = corridor.residuals(
            distance=1.2, uav_action=0.3, ugv_action=0.4,
            uav_gain=1.0, ugv_gain=1.0,
        )
        self.assertNotEqual(first, second)
        self.assertTrue(
            corridor.has_box_feasible_action(
                distance=1.0, uav_gain=1.0, ugv_gain=0.5,
                uav_bounds=(-1.0, 1.0), ugv_bounds=(-1.0, 1.0),
                margin=0.2,
            )
        )

    def test_fail_closed_when_margin_exhausts_control_authority(self) -> None:
        corridor = PairwiseCorridor(1.0, 1.1, alpha=1.0)
        self.assertFalse(
            corridor.has_box_feasible_action(
                distance=1.05, uav_gain=0.01, ugv_gain=0.01,
                uav_bounds=(-1.0, 1.0), ugv_bounds=(-1.0, 1.0),
                margin=0.20,
            )
        )


if __name__ == "__main__":
    unittest.main()

