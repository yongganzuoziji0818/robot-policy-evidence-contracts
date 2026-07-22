from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agc_basil.n0_feasibility import audit_n0_feasibility  # noqa: E402


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


class N0FeasibilityTests(unittest.TestCase):
    def test_all_c1_selection_has_zero_possible_increment(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selection = _write(root / "selection.json", {"selected_ids": ["a", "b"]})
            registry = _write(
                root / "registry.json",
                {
                    "assets": [
                        {"id": "a", "status": "ELIGIBLE_LOCKED", "component": "C1"},
                        {"id": "b", "status": "ELIGIBLE_LOCKED", "component": "C1"},
                    ]
                },
            )
            result = audit_n0_feasibility(selection, registry)
            self.assertEqual(result.maximum_possible_incremental_detections, 0)
            self.assertFalse(result.superiority_gate_satisfiable)

    def test_only_non_marginal_mappings_can_raise_bound(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selection = _write(root / "selection.json", {"selected_ids": ["a", "b", "c"]})
            registry = _write(
                root / "registry.json",
                {
                    "assets": [
                        {"id": "a", "status": "ELIGIBLE_LOCKED", "component": "C1"},
                        {
                            "id": "b",
                            "status": "ELIGIBLE_LOCKED",
                            "component": "C1",
                            "secondary_component": "C2",
                        },
                        {"id": "c", "status": "ELIGIBLE_LOCKED", "component": "C3"},
                    ]
                },
            )
            result = audit_n0_feasibility(selection, registry)
            self.assertEqual(result.non_marginal_ids, ("b", "c"))
            self.assertEqual(result.maximum_possible_incremental_detections, 2)
            self.assertTrue(result.superiority_gate_satisfiable)

    def test_frozen_v94_selection_has_upper_bound_one(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            selected_ids = [
                "GYM-0915", "GYM-0952", "GYM-1027", "GYM-1018",
                "TRL-2291-2294", "TRL-2959", "GYM-1528", "GYM-1526",
            ]
            selection = _write(root / "selection.json", {"selected_ids": selected_ids})
            registry = _write(
                root / "registry.json",
                {
                    "assets": [
                        {
                            "id": asset_id,
                            "status": "ELIGIBLE_LOCKED",
                            "component": "C1",
                            **({"secondary_component": "C2"} if asset_id == "TRL-2959" else {}),
                        }
                        for asset_id in selected_ids
                    ]
                },
            )
            result = audit_n0_feasibility(selection, registry)
        self.assertEqual(result.selected_count, 8)
        self.assertEqual(result.non_marginal_ids, ("TRL-2959",))
        self.assertEqual(result.maximum_possible_incremental_detections, 1)
        self.assertEqual(result.required_incremental_detections, 2)
        self.assertFalse(result.superiority_gate_satisfiable)
        self.assertTrue(result.disposition.startswith("N0_PREEXECUTION_SCIENTIFIC_FAIL_STOP"))


if __name__ == "__main__":
    unittest.main()
