from __future__ import annotations

import math
import unittest

from agc_flux import (
    FluxModel,
    determinant_2x2,
    information_matrix,
    min_eigenvalue_2x2,
    nullspace_projected_information,
)


class FluxTheoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = FluxModel(diffusion=0.2, loss_rate=0.05)

    def test_aerial_equivalence_class_holds_at_every_height(self) -> None:
        source, deposition = 3.0, 0.4
        amplitude = self.model.surface_amplitude(source, deposition)
        alternate_deposition = 1.7
        alternate_source = self.model.equivalent_source(amplitude, alternate_deposition)
        self.assertNotAlmostEqual(source, alternate_source)
        for height in (0.1, 1.0, 3.0, 10.0, 30.0):
            self.assertAlmostEqual(
                self.model.concentration(height, source, deposition),
                self.model.concentration(height, alternate_source, alternate_deposition),
                places=13,
            )

    def test_joint_observation_recovers_parameters(self) -> None:
        for source in (0.5, 2.0, 9.0):
            for deposition in (0.0, 0.1, 1.2):
                height = 4.0
                recovered = self.model.recover(
                    height,
                    self.model.concentration(height, source, deposition),
                    self.model.deposition_flux(source, deposition),
                )
                self.assertAlmostEqual(recovered[0], source, places=12)
                self.assertAlmostEqual(recovered[1], deposition, places=12)

    def test_aerial_information_is_rank_one_for_any_heights(self) -> None:
        matrix = information_matrix(
            self.model.aerial_rows((0.2, 1.0, 7.0, 25.0), 2.0, 0.3, sigma=0.1)
        )
        trace = matrix[0][0] + matrix[1][1]
        self.assertLessEqual(abs(determinant_2x2(matrix)) / (trace * trace), 1e-15)
        self.assertLessEqual(abs(min_eigenvalue_2x2(matrix)) / trace, 1e-15)

    def test_ground_flux_restores_full_rank(self) -> None:
        aerial = self.model.aerial_gradient(3.0, 2.0, 0.3)
        ground = self.model.ground_flux_gradient(2.0, 0.3)
        matrix = information_matrix(((aerial, 0.1), (ground, 0.1)))
        self.assertGreater(determinant_2x2(matrix), 0.0)
        self.assertGreater(min_eigenvalue_2x2(matrix), 0.0)

    def test_extra_aerial_sample_has_zero_nullspace_gain(self) -> None:
        anchor = self.model.aerial_gradient(2.0, 2.0, 0.3)
        extra = self.model.aerial_gradient(11.0, 2.0, 0.3)
        gain = nullspace_projected_information(anchor, ((extra, 0.1),))
        self.assertAlmostEqual(gain, 0.0, places=15)

    def test_ground_flux_has_positive_nullspace_gain(self) -> None:
        anchor = self.model.aerial_gradient(2.0, 2.0, 0.3)
        ground = self.model.ground_flux_gradient(2.0, 0.3)
        gain = nullspace_projected_information(anchor, ((ground, 0.1),))
        self.assertGreater(gain, 0.0)

    def test_near_ground_concentration_does_not_restore_rank(self) -> None:
        anchor = self.model.aerial_gradient(2.0, 2.0, 0.3)
        near_ground = self.model.aerial_gradient(0.0, 2.0, 0.3)
        matrix = information_matrix(((anchor, 0.1), (near_ground, 0.1)))
        trace = matrix[0][0] + matrix[1][1]
        self.assertLessEqual(abs(determinant_2x2(matrix)) / (trace * trace), 1e-15)

    def test_closed_form_jacobian_determinant(self) -> None:
        source, deposition, height = 2.3, 0.7, 4.2
        aerial = self.model.aerial_gradient(height, source, deposition)
        ground = self.model.ground_flux_gradient(source, deposition)
        observed = aerial[0] * ground[1] - aerial[1] * ground[0]
        denominator = self.model.escape_coefficient + deposition
        expected = math.exp(-self.model.decay * height) * source / (denominator**2)
        self.assertAlmostEqual(observed, expected, places=13)

    def test_invalid_inputs_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            FluxModel(0.0, 0.1)
        with self.assertRaises(ValueError):
            self.model.concentration(-1.0, 1.0, 0.1)
        with self.assertRaises(ValueError):
            self.model.recover(1.0, 0.0, 0.1)
        with self.assertRaises(ValueError):
            information_matrix((((1.0, 2.0), 0.0),))


if __name__ == "__main__":
    unittest.main()
