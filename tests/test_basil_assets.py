from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agc_basil.assets import (  # noqa: E402
    AssetLockError,
    load_registry,
    select_chronological_pairs,
    selection_record,
)


FAKE_SHA_A = "a" * 64
FAKE_SHA_B = "b" * 64
FAKE_SHA_C = "c" * 64


def _locked(asset_id: str, when: str) -> dict[str, str]:
    return {
        "id": asset_id,
        "project": "fixture-project",
        "source_url": f"https://example.test/{asset_id}",
        "status": "ELIGIBLE_LOCKED",
        "component": "C1",
        "upstream_time": when,
        "before_revision": f"{asset_id}-before",
        "after_revision": f"{asset_id}-after",
        "source_bundle_path": f"bundles/{asset_id}.zip",
        "source_bundle_sha256": FAKE_SHA_A,
        "reproducer_path": f"reproducers/{asset_id}.py",
        "reproducer_sha256": FAKE_SHA_C,
        "license_spdx": "MIT",
    }


class AssetRegistryTests(unittest.TestCase):
    def test_draft_registry_fails_closed(self) -> None:
        registry = {"assets": [{"id": "candidate", "status": "PENDING_REPRODUCTION"}]}
        with self.assertRaisesRegex(AssetLockError, "N0_ASSET_FAIL_STOP"):
            select_chronological_pairs(registry, 1)

    def test_selection_is_chronological_not_input_order(self) -> None:
        registry = {
            "assets": [
                _locked("late", "2026-07-20T12:00:00+00:00"),
                _locked("early", "2024-01-01T12:00:00+00:00"),
            ]
        }
        self.assertEqual(
            [asset.asset_id for asset in select_chronological_pairs(registry, 1)],
            ["early"],
        )

    def test_duplicate_ids_fail_before_selection(self) -> None:
        registry = {
            "assets": [
                _locked("same", "2024-01-01T12:00:00+00:00"),
                _locked("same", "2025-01-01T12:00:00+00:00"),
            ]
        }
        with self.assertRaisesRegex(AssetLockError, "duplicate"):
            select_chronological_pairs(registry, 1)

    def test_invalid_hash_fails_closed(self) -> None:
        entry = _locked("bad", "2024-01-01T12:00:00+00:00")
        entry["reproducer_sha256"] = "not-a-hash"
        with self.assertRaisesRegex(AssetLockError, "invalid reproducer_sha256"):
            select_chronological_pairs({"assets": [entry]}, 1)

    def test_selection_record_binds_registry_hash(self) -> None:
        with TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.json"
            registry_path.write_text(
                json.dumps({"assets": [_locked("one", "2024-01-01T12:00:00+00:00")]}),
                encoding="utf-8",
            )
            registry = load_registry(registry_path)
            selected = select_chronological_pairs(registry, 1)
            record = selection_record(registry_path, selected)
            self.assertEqual(record["selected_ids"], ["one"])
            self.assertEqual(len(record["registry_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
