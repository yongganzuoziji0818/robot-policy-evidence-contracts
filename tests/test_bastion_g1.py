from __future__ import annotations

import unittest

from agc_bastion.g1 import (
    boundary_constraints,
    coefficient_loss,
    policy_matrix,
    rotate_diagonal,
    target_matrix,
)


class BastionG1MechanicsTests(unittest.TestCase):
    def test_rotated_drift_is_symmetric(self) -> None:
        matrix = rotate_diagonal(0.8, 0.4, 0.3)
        self.assertAlmostEqual(matrix[1], matrix[2])

    def test_target_matrix_closes_loop_at_desired_decay(self) -> None:
        drift = rotate_diagonal(0.8, 0.4, 0.2)
        target = target_matrix(drift, (1.0, 2.0), desired_decay=0.2)
        self.assertAlmostEqual(drift[0] + target[0], -0.2)
        self.assertAlmostEqual(drift[1] + target[1], 0.0)
        self.assertAlmostEqual(drift[2] + 2.0 * target[2], 0.0)
        self.assertAlmostEqual(drift[3] + 2.0 * target[3], -0.2)

    def test_policy_context_and_loss(self) -> None:
        theta = tuple(range(8))
        self.assertEqual(policy_matrix(theta, 0.0), (0.0, 1.0, 2.0, 3.0))
        target = policy_matrix(theta, 1.0)
        self.assertEqual(coefficient_loss(theta, 1.0, target), 0.0)

    def test_boundary_constraint_count(self) -> None:
        constraints = boundary_constraints(
            drift=rotate_diagonal(0.8, 0.4, 0.2), control_gain=(1.0, 1.0),
            radius=1.0, context=0.0, witness_count=16,
            additive_gap=0.02, cover_margin=0.1,
        )
        self.assertEqual(len(constraints), 16)
        self.assertTrue(all(len(item.normal) == 8 for item in constraints))


if __name__ == "__main__":
    unittest.main()

