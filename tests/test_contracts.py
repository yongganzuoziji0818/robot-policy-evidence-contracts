from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from robot_policy_evidence_contracts import (
    bonferroni_hoeffding_upper_bounds,
    certify_ranking,
    hoeffding_upper_bound,
    verify_artifact_manifest,
)


class BoundTests(unittest.TestCase):
    def test_zero_trials_fail_closed(self) -> None:
        self.assertEqual(hoeffding_upper_bound(0, 0, 0.05), 1.0)

    def test_familywise_bound_is_at_least_empirical_risk(self) -> None:
        result = bonferroni_hoeffding_upper_bounds(
            {"policy-a": (2, 100), "policy-b": (5, 100)}, familywise_alpha=0.05
        )
        self.assertGreaterEqual(result["policy-a"], 0.02)
        self.assertGreaterEqual(result["policy-b"], 0.05)


class RankingTests(unittest.TestCase):
    def test_wide_margins_are_certified(self) -> None:
        result = certify_ranking(
            {"a": 0.90, "b": 0.70, "c": 0.40},
            {"a": 0.03, "b": 0.04, "c": 0.05},
        )
        self.assertTrue(result.fully_certified)
        self.assertEqual(result.ordered_policies, ("a", "b", "c"))

    def test_small_margin_remains_unresolved(self) -> None:
        result = certify_ranking(
            {"a": 0.80, "b": 0.77}, {"a": 0.02, "b": 0.02}
        )
        self.assertFalse(result.fully_certified)
        self.assertEqual(len(result.unresolved_pairs), 1)


class ProvenanceTests(unittest.TestCase):
    def test_hash_match_and_missing_file_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.txt"
            path.write_text("evidence", encoding="utf-8")
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            checks = verify_artifact_manifest(
                {
                    "present": (path, expected),
                    "missing": (Path(directory) / "missing.txt", "0" * 64),
                }
            )
        self.assertTrue(checks[0].valid)
        self.assertFalse(checks[1].valid)
        self.assertEqual(checks[1].reason, "file missing")


if __name__ == "__main__":
    unittest.main()
