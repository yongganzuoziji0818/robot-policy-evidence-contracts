from __future__ import annotations

import importlib.util
import inspect
import unittest


HAS_TORCH = importlib.util.find_spec("torch") is not None
if HAS_TORCH:
    import agc_saver.environment as environment_module
    from agc_saver.environment import CampaignCondition, PlanSpec, evaluate_plan, make_lineage, make_plan_library
    from agc_saver.n0 import build_memory_ontology, summarize_campaign, summarize_gate


@unittest.skipUnless(HAS_TORCH, "SAVER tests require torch")
class SaverNaturalAssetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.grid = {
            "route_clearance": [0.12, 0.22, 0.32, 0.42],
            "communication_reliance": [0.20, 0.60, 0.90],
            "drive_authority": [0.70, 1.00, 1.30],
        }

    def test_environment_has_no_lifecycle_input(self) -> None:
        signature = inspect.signature(evaluate_plan)
        self.assertNotIn("memory_id", signature.parameters)
        self.assertNotIn("lifecycle_decision", signature.parameters)
        source = inspect.getsource(environment_module)
        for forbidden in ("memory_id", "lifecycle_decision", "retain_reward", "retire_reward"):
            self.assertNotIn(forbidden, source)

    def test_frozen_plan_and_memory_counts(self) -> None:
        plans = make_plan_library(self.grid)
        self.assertEqual(len(plans), 36)
        for axis in ("communication", "dynamics"):
            memories = build_memory_ontology(axis)
            self.assertEqual(len(memories), 6)
            self.assertTrue(all(any(memory.matches(plan) for plan in plans) for memory in memories))

    def test_evaluation_is_deterministic_on_cpu(self) -> None:
        lineage = make_lineage("1U2G", 7101)
        condition = CampaignCondition(
            topology="1U2G",
            change_axis="communication",
            phase="source",
            communication_loss=0.70,
            dynamics_inertia=0.20,
        )
        plan = PlanSpec(0.22, 0.90, 1.00)
        first = evaluate_plan(plan, condition, lineage, trials=64, seed=99, device="cpu")
        second = evaluate_plan(plan, condition, lineage, trials=64, seed=99, device="cpu")
        self.assertEqual(first, second)

    def test_gate_requires_coverage_not_only_count(self) -> None:
        summaries = [
            {
                "campaign_id": f"c{i}",
                "change_axis": "communication",
                "topology": "1U2G",
                "lineage_replicate": 1,
                "source_memory_gate_pass": True,
                "two_sided_witness": True,
            }
            for i in range(4)
        ]
        gate = summarize_gate(summaries, minimum=4)
        self.assertFalse(gate["n0_gate_pass"])


if __name__ == "__main__":
    unittest.main()
