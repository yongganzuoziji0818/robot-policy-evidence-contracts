from __future__ import annotations

import unittest

from agc_flux import FieldConfig, make_campaign, run_method


class FluxSimulationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = FieldConfig()

    def test_all_methods_obey_matched_count(self) -> None:
        campaign = make_campaign(seed=7, deposition=0.5, aerial_sigma=0.05, ground_sigma=0.02)
        for method in ("uav_only", "ugv_only", "fixed_joint", "random_joint", "flux", "oracle_joint"):
            result = run_method(self.config, campaign, method)
            self.assertEqual(result.aerial_count + result.ground_count, 10)

    def test_noiseless_joint_is_nearly_exact(self) -> None:
        campaign = make_campaign(seed=11, deposition=0.5, aerial_sigma=1e-9, ground_sigma=1e-9)
        result = run_method(self.config, campaign, "oracle_joint")
        self.assertLess(result.source_relative_error, 1e-4)
        self.assertLess(result.deposition_absolute_error, 1e-4)
        self.assertLess(result.location_absolute_error, 0.13)

    def test_aerial_only_has_structural_source_bias(self) -> None:
        campaign = make_campaign(seed=11, deposition=0.5, aerial_sigma=1e-9, ground_sigma=1e-9)
        result = run_method(self.config, campaign, "uav_only")
        expected = campaign.deposition / (self.config.escape_coefficient + campaign.deposition)
        self.assertAlmostEqual(result.source_relative_error, expected, places=4)

    def test_method_results_are_deterministic(self) -> None:
        campaign = make_campaign(seed=19, deposition=0.05, aerial_sigma=0.2, ground_sigma=0.1)
        self.assertEqual(
            run_method(self.config, campaign, "flux"),
            run_method(self.config, campaign, "flux"),
        )

    def test_unknown_method_fails_closed(self) -> None:
        campaign = make_campaign(seed=3, deposition=0.05, aerial_sigma=0.05, ground_sigma=0.02)
        with self.assertRaises(ValueError):
            run_method(self.config, campaign, "renamed_baseline")


if __name__ == "__main__":
    unittest.main()
