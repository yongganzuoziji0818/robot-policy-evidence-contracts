from __future__ import annotations

import json
import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

from agc_rlrd.certification import (
    certify_locked_path,
    clopper_pearson_upper_bound,
    hoeffding_upper_bound,
)
from agc_rlrd.guard import ExperimentNotAuthorized, load_manifest, require_authorized
from agc_rlrd.metrics import adaptation_delay, recurrence_regression_gap, summarize_safety_debt
from agc_rlrd.n0_contract import assess_n0_readiness, validate_campaign_manifest
from agc_rlrd.n0_analysis import summarize_natural_census
from agc_rlrd.planning import find_minimum_debt_path
from agc_rlrd.protocol import CampaignKey, NonstationaryProtocol, PhaseSpec
from agc_rlrd.profiles import (
    binary_profiles,
    identify_pairwise_landscape,
    mobius_coefficients,
    reconstruct_risk,
)


WITNESS_RISK = {
    (0, 0, 0): 0.020,
    (1, 0, 0): 0.017,
    (0, 1, 0): 0.017,
    (0, 0, 1): 0.017,
    (1, 1, 0): 0.064,
    (1, 0, 1): 0.008,
    (0, 1, 1): 0.008,
    (1, 1, 1): 0.049,
}

HAS_NUMPY = importlib.util.find_spec("numpy") is not None
if HAS_NUMPY:
    from agc_rlrd.g0 import evaluate_method, generate_landscape


class ProfileTests(unittest.TestCase):
    def test_mobius_round_trip_and_pair_interaction(self) -> None:
        coefficients = mobius_coefficients(WITNESS_RISK)
        for profile, expected in WITNESS_RISK.items():
            self.assertAlmostEqual(reconstruct_risk(profile, coefficients), expected)
        self.assertAlmostEqual(coefficients[frozenset((0, 1))], 0.050)
        self.assertAlmostEqual(coefficients[frozenset((0, 2))], -0.006)
        self.assertAlmostEqual(coefficients[frozenset((1, 2))], -0.006)

    def test_middle_layer_exact_lower_bound_size(self) -> None:
        for n_agents in range(1, 13):
            middle = sum(
                1 for profile in binary_profiles(n_agents) if sum(profile) == n_agents // 2
            )
            self.assertEqual(middle, math.comb(n_agents, n_agents // 2))

    def test_known_sparse_pair_graph_needs_one_plus_n_plus_edges_queries(self) -> None:
        coefficients = {
            frozenset(): 0.030,
            frozenset((0,)): -0.002,
            frozenset((1,)): 0.001,
            frozenset((2,)): -0.003,
            frozenset((3,)): 0.002,
            frozenset((0, 1)): 0.015,
            frozenset((1, 3)): -0.008,
        }
        truth = {
            profile: reconstruct_risk(profile, coefficients)
            for profile in binary_profiles(4)
        }
        identified = identify_pairwise_landscape(
            truth.__getitem__, 4, edges=((0, 1), (1, 3))
        )
        self.assertEqual(identified.query_count, 1 + 4 + 2)
        for profile, expected in truth.items():
            self.assertAlmostEqual(identified.reconstructed_risk[profile], expected)


class PlanningTests(unittest.TestCase):
    def test_planner_avoids_unsafe_pair_and_tracks_nonzero_debt(self) -> None:
        plan = find_minimum_debt_path(
            WITNESS_RISK,
            tau_target=0.010,
            tau_hard=0.050,
            exposure_by_stage=(1.0, 1.0, 1.0, 1.0),
        )
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertNotIn((1, 1, 0), plan.path)
        self.assertLessEqual(plan.maximum_risk, 0.050)
        self.assertGreater(plan.cumulative_debt, 0.0)

    def test_planner_fails_closed_when_goal_is_unsafe(self) -> None:
        risk = dict(WITNESS_RISK)
        risk[(1, 1, 1)] = 0.051
        self.assertIsNone(
            find_minimum_debt_path(risk, tau_target=0.010, tau_hard=0.050)
        )


class CertificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.path = ((0, 0), (1, 0), (1, 1))

    def test_fresh_low_failure_split_can_promote(self) -> None:
        counts = {profile: (0, 50_000) for profile in self.path}
        result = certify_locked_path(
            self.path,
            counts,
            familywise_alpha=0.05,
            tau_target=0.010,
            tau_hard=0.050,
            exposure_by_stage=(1.0, 1.0, 1.0),
            debt_budget=0.030,
            certification_split_id="cert-001",
            discovery_split_id="discover-001",
        )
        self.assertTrue(result.promote)

    def test_missing_samples_hold_fail_closed(self) -> None:
        result = certify_locked_path(
            self.path,
            {},
            familywise_alpha=0.05,
            tau_target=0.010,
            tau_hard=0.050,
            exposure_by_stage=(1.0, 1.0, 1.0),
            debt_budget=1.0,
            certification_split_id="cert-002",
        )
        self.assertFalse(result.promote)
        self.assertEqual(result.maximum_risk_upper, 1.0)

    def test_reused_discovery_split_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            certify_locked_path(
                self.path,
                {},
                familywise_alpha=0.05,
                tau_target=0.010,
                tau_hard=0.050,
                exposure_by_stage=(1.0, 1.0, 1.0),
                debt_budget=1.0,
                certification_split_id="same",
                discovery_split_id="same",
            )

    @unittest.skipUnless(HAS_NUMPY, "Clopper-Pearson test requires scipy stack")
    def test_clopper_pearson_is_tighter_than_hoeffding_in_operating_region(self) -> None:
        exact = clopper_pearson_upper_bound(640, 8000, 0.05 / 9)
        conservative = hoeffding_upper_bound(640, 8000, 0.05 / 9)
        self.assertLess(exact, conservative)
        self.assertLess(exact, 0.10)


class AuthorizationTests(unittest.TestCase):
    def test_draft_manifest_refuses_every_experiment_stage(self) -> None:
        draft = {
            "direction_version": 5,
            "authorized": False,
            "formal_experiment_authorized": False,
            "sealed_data_authorized": False,
            "claim_generation_allowed": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(draft), encoding="utf-8")
            manifest = load_manifest(path)
        with self.assertRaises(ExperimentNotAuthorized):
            require_authorized(manifest)
        with self.assertRaises(ExperimentNotAuthorized):
            require_authorized(manifest, formal=True, sealed=True, claim_generation=True)


class MetricTests(unittest.TestCase):
    def test_target_debt_and_hard_cap_are_distinct(self) -> None:
        summary = summarize_safety_debt(
            (0.008, 0.020, 0.049, 0.051),
            (10.0, 10.0, 5.0, 1.0),
            tau_target=0.010,
            tau_hard=0.050,
        )
        self.assertAlmostEqual(summary.cumulative_debt, 0.336)
        self.assertEqual(summary.hard_violation_count, 1)
        self.assertEqual(summary.hard_violation_exposure, 1.0)

    def test_adaptation_and_recurrence_diagnostics(self) -> None:
        self.assertEqual(
            adaptation_delay((0.08, 0.04, 0.03, 0.06), tau_target=0.05, consecutive=2),
            1,
        )
        self.assertIsNone(
            adaptation_delay((0.08, 0.04, 0.06), tau_target=0.05, consecutive=2)
        )
        self.assertAlmostEqual(
            recurrence_regression_gap((0.02, 0.03), (0.04, 0.05)), 0.02
        )


class ProtocolTests(unittest.TestCase):
    @staticmethod
    def phase(index: int, axis: str, topology: str, lineage: int) -> PhaseSpec:
        return PhaseSpec(
            phase_id=f"phase-{index}",
            key=CampaignKey("delivery", topology, lineage, axis),
            distribution_id=f"dist-{index}",
            version_generation_rule_id=f"rule-{index}",
            rollout_seed_block_id=f"seeds-{index}",
            deployment_exposure_schedule_id="schedule-frozen-001",
        )

    def test_n0_scope_requires_cross_axis_topology_and_lineage(self) -> None:
        valid = NonstationaryProtocol(
            phases=(
                self.phase(1, "communication", "1U2G", 101),
                self.phase(2, "dynamics", "2U2G", 202),
            ),
            locked_before_profile_observation=True,
            certification_within_stationary_phase=True,
        )
        valid.validate(require_n0_scope=True)
        invalid = NonstationaryProtocol(
            phases=(self.phase(3, "communication", "1U2G", 101),),
            locked_before_profile_observation=True,
            certification_within_stationary_phase=True,
        )
        with self.assertRaises(ValueError):
            invalid.validate(require_n0_scope=True)


class N0ContractTests(unittest.TestCase):
    def test_manifest_counts_profiles_and_requires_independent_scope(self) -> None:
        campaigns = []
        lineage_ids = set()
        for replicate in (1, 2):
            for topology in ("1U2G", "2U2G"):
                for axis in ("communication", "dynamics"):
                    lineage = f"L-{topology}-{axis}-{replicate}"
                    lineage_ids.add(lineage)
                    tag = f"{lineage}-{topology}-{axis}"
                    campaigns.append(
                        {
                            "campaign_id": tag,
                            "task_family": "delivery",
                            "topology": topology,
                            "change_axis": axis,
                            "lineage_id": lineage,
                            "distribution_id": f"dist-{tag}",
                            "failure_event_id": "failure-v1",
                            "exposure_schedule_id": "exposure-v1",
                            "rollout_seed_block_id": f"seeds-{tag}",
                            "all_profiles_required": True,
                        }
                    )
        manifest = {
            "direction_version": 5,
            "authorized": True,
            "development_experiment_authorized": True,
            "formal_experiment_authorized": False,
            "sealed_data_authorized": False,
            "claim_generation_allowed": False,
            "risk_thresholds": {
                "tau_target": 0.03,
                "tau_hard": 0.10,
                "frozen_before_profile_observation": True,
            },
            "campaigns": campaigns,
        }
        errors, campaign_count, profile_campaigns = validate_campaign_manifest(
            manifest, lineage_ids=lineage_ids
        )
        self.assertEqual(errors, [])
        self.assertEqual(campaign_count, 8)
        self.assertEqual(profile_campaigns, 96)

    def test_readiness_fails_closed_on_missing_external_assets(self) -> None:
        registry = {"sealed": False, "natural_versions": True, "lineages": []}
        result = assess_n0_readiness(
            registry,
            {},
            environment_package="definitely_missing_p5_environment",
            rollout_adapter_module="definitely_missing_p5_environment.adapter",
        )
        self.assertFalse(result.ready)
        self.assertTrue(any("environment package" in item for item in result.errors))
        self.assertTrue(any("rollout adapter" in item for item in result.errors))


class N0AnalysisTests(unittest.TestCase):
    def test_analytic_witness_is_measured_as_decision_changing(self) -> None:
        summary = summarize_natural_census(
            WITNESS_RISK, tau_hard=0.05, interaction_sesoi=0.0175
        )
        self.assertTrue(summary.boundary_canaries_safe)
        self.assertGreater(summary.safe_path_count, 0)
        self.assertGreater(summary.unsafe_path_count, 0)
        self.assertTrue(summary.decision_changing_natural_interaction)
        self.assertAlmostEqual(
            next(item.contrast for item in summary.pair_interactions if item.pair == (0, 1)),
            0.05,
        )

    def test_additive_safe_census_does_not_pass_natural_gate(self) -> None:
        risk = {
            profile: 0.02 + 0.001 * sum(profile)
            for profile in binary_profiles(3)
        }
        summary = summarize_natural_census(
            risk, tau_hard=0.05, interaction_sesoi=0.0175
        )
        self.assertFalse(summary.order_changes_feasibility)
        self.assertFalse(summary.decision_changing_natural_interaction)


@unittest.skipUnless(HAS_NUMPY, "optional G0 tests require numpy")
class G0PipelineTests(unittest.TestCase):
    def test_landscape_generation_is_deterministic_and_typed_graph_is_sparse(self) -> None:
        first = generate_landscape(8, "typed_sparse_pairwise", 12345)
        second = generate_landscape(8, "typed_sparse_pairwise", 12345)
        self.assertEqual(first.risk, second.risk)
        self.assertLess(len(first.typed_edges), math.comb(8, 2))
        self.assertLessEqual(first.risk[(1,) * 8], 0.10)
        coefficients = mobius_coefficients(first.risk)
        self.assertTrue(
            all(abs(value) < 1e-12 for subset, value in coefficients.items() if len(subset) > 2)
        )

    def test_oracle_exact_never_labels_invalid_path_as_valid(self) -> None:
        landscape = generate_landscape(6, "higher_order_misspecified", 54321)
        result = evaluate_method(
            landscape,
            "oracle_safest_path",
            mode="exact",
            discovery_trials=20,
            certification_trials=100,
            familywise_alpha=0.05,
            tau_target=0.03,
            tau_hard=0.10,
            debt_budget=0.20,
        )
        self.assertFalse(result["false_approval"])
        if result["promoted"]:
            self.assertTrue(result["true_valid"])

    def test_exact_typed_rlrd_finds_a_valid_path(self) -> None:
        landscape = generate_landscape(8, "typed_sparse_pairwise", 777)
        result = evaluate_method(
            landscape,
            "rlrd_full",
            mode="exact",
            discovery_trials=20,
            certification_trials=100,
            familywise_alpha=0.05,
            tau_target=0.03,
            tau_hard=0.10,
            debt_budget=0.20,
        )
        self.assertTrue(result["promoted"])
        self.assertTrue(result["true_valid"])

    def test_pairwise_generator_labels_hold_across_sizes_and_seeds(self) -> None:
        for landscape_class in ("sparse_pairwise", "typed_sparse_pairwise"):
            for n_agents in (4, 6, 8):
                for seed in range(20):
                    landscape = generate_landscape(n_agents, landscape_class, seed)
                    coefficients = mobius_coefficients(landscape.risk)
                    offenders = {
                        tuple(sorted(subset)): value
                        for subset, value in coefficients.items()
                        if len(subset) > 2 and abs(value) >= 1e-12
                    }
                    self.assertFalse(
                        offenders,
                        msg=f"{landscape_class=} {n_agents=} {seed=} {offenders=}",
                    )
                    self.assertLessEqual(landscape.risk[(1,) * n_agents], 0.10)
                    self.assertTrue(any(value > 0.10 for value in landscape.risk.values()))


if __name__ == "__main__":
    unittest.main()
