from __future__ import annotations

import unittest

from agc_flux import G1Config, G1_METHODS, MISMATCH_FAMILIES, make_g1_campaign, run_g1_method


class FluxG1SimulationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = G1Config()

    def test_all_methods_use_exactly_ten_measurements(self) -> None:
        campaign = make_g1_campaign(
            seed=71, deposition=0.5, noise_tier="high", mismatch_family="transport_shift"
        )
        for method in G1_METHODS:
            result = run_g1_method(self.config, campaign, method)
            self.assertEqual(result.aerial_count + result.ground_count + result.near_ground_count, 10)

    def test_all_families_are_deterministic(self) -> None:
        for family in MISMATCH_FAMILIES:
            campaign = make_g1_campaign(seed=81, deposition=0.05, noise_tier="low", mismatch_family=family)
            self.assertEqual(
                run_g1_method(self.config, campaign, "flux"),
                run_g1_method(self.config, campaign, "flux"),
            )

    def test_nullspace_projection_preserves_aerial_location(self) -> None:
        campaign = make_g1_campaign(
            seed=91, deposition=0.5, noise_tier="low", mismatch_family="deposition_patchiness"
        )
        flux = run_g1_method(self.config, campaign, "flux")
        no_projection = run_g1_method(self.config, campaign, "flux_no_projection")
        self.assertTrue(flux.projected_update)
        self.assertFalse(no_projection.projected_update)
        self.assertNotEqual(flux.source_x_hat, no_projection.source_x_hat)

    def test_d_opt_uses_unique_ground_positions(self) -> None:
        campaign = make_g1_campaign(
            seed=101, deposition=0.05, noise_tier="high", mismatch_family="detection_censoring"
        )
        result = run_g1_method(self.config, campaign, "joint_d_opt")
        self.assertEqual(len(result.selected_ground_positions), 4)
        self.assertEqual(len(set(result.selected_ground_positions)), 4)

    def test_near_ground_air_does_not_count_as_boundary_flux(self) -> None:
        campaign = make_g1_campaign(
            seed=111, deposition=0.5, noise_tier="low", mismatch_family="transport_shift"
        )
        result = run_g1_method(self.config, campaign, "near_ground_joint")
        self.assertEqual(result.ground_count, 0)
        self.assertEqual(result.near_ground_count, 4)
        self.assertEqual(result.deposition_hat, 0.0)

    def test_unknown_method_fails_closed(self) -> None:
        campaign = make_g1_campaign(
            seed=121, deposition=0.05, noise_tier="low", mismatch_family="transport_shift"
        )
        with self.assertRaises(ValueError):
            run_g1_method(self.config, campaign, "renamed_method")


if __name__ == "__main__":
    unittest.main()
