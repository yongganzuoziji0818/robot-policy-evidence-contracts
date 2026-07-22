from __future__ import annotations

import unittest

from agc_bastion.natural import (
    Regime,
    old_certificate_slack,
    policy_coefficient,
    simulate_recurrence,
    target_coefficient,
)


class BastionNaturalMechanicsTests(unittest.TestCase):
    def test_target_coefficient_produces_desired_decay(self) -> None:
        regime = Regime(outward_drift=0.8, control_gain=2.0, context=0.0)
        coefficient = target_coefficient(regime, desired_decay=0.2)
        self.assertAlmostEqual(regime.outward_drift + regime.control_gain * coefficient, -0.2)

    def test_certificate_slack_matches_boundary_rate(self) -> None:
        regime = Regime(outward_drift=0.5, control_gain=1.0, context=0.0)
        self.assertAlmostEqual(old_certificate_slack((-0.7, 9.0), regime), 0.2)

    def test_safe_linear_recurrence_stays_inside_corridor(self) -> None:
        regime = Regime(outward_drift=0.5, control_gain=1.0, context=0.0)
        result = simulate_recurrence(
            (-0.7, 0.0), regime, initial_distance=3.8,
            goal_distance=2.5, minimum_distance=1.0, maximum_distance=4.0,
            dt=0.05, steps=200,
        )
        self.assertEqual(result["safety_debt"], 0.0)
        self.assertLess(result["final_distance"], 3.8)

    def test_context_changes_policy_coefficient(self) -> None:
        self.assertNotEqual(
            policy_coefficient((-1.0, 0.5), 0.0),
            policy_coefficient((-1.0, 0.5), 1.0),
        )


if __name__ == "__main__":
    unittest.main()

