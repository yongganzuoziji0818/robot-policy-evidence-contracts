"""Fail-closed registry validation for BASIL natural bug-fix assets.

This module does not download, execute, or qualify upstream software.  It only
validates a registry whose evidence fields have already been populated by an
authorized source-lock workflow.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


LOCKED_STATUS = "ELIGIBLE_LOCKED"
ALLOWED_COMPONENTS = {"C1", "C2", "C3", "mixed"}
SHA256_HEX_LENGTH = 64


class AssetLockError(ValueError):
    """Raised when a registry cannot support a frozen chronological selection."""


@dataclass(frozen=True)
class LockedAsset:
    asset_id: str
    project: str
    upstream_time: datetime
    source_url: str
    before_revision: str
    after_revision: str
    source_bundle_path: str
    source_bundle_sha256: str
    reproducer_path: str
    reproducer_sha256: str
    license_spdx: str
    component: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_text(entry: dict[str, Any], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AssetLockError(f"{entry.get('id', '<unknown>')}: missing {key}")
    return value.strip()


def _require_sha256(entry: dict[str, Any], key: str) -> str:
    value = _require_text(entry, key).lower()
    if len(value) != SHA256_HEX_LENGTH or any(ch not in "0123456789abcdef" for ch in value):
        raise AssetLockError(f"{entry.get('id', '<unknown>')}: invalid {key}")
    return value


def _parse_upstream_time(entry: dict[str, Any]) -> datetime:
    raw = _require_text(entry, "upstream_time")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssetLockError(f"{entry.get('id', '<unknown>')}: invalid upstream_time") from exc
    if parsed.tzinfo is None:
        raise AssetLockError(f"{entry.get('id', '<unknown>')}: upstream_time must include a timezone")
    return parsed


def validate_locked_asset(entry: dict[str, Any]) -> LockedAsset:
    if entry.get("status") != LOCKED_STATUS:
        raise AssetLockError(f"{entry.get('id', '<unknown>')}: status is not {LOCKED_STATUS}")

    component = _require_text(entry, "component")
    if component not in ALLOWED_COMPONENTS:
        raise AssetLockError(f"{entry.get('id', '<unknown>')}: invalid component {component}")

    before_revision = _require_text(entry, "before_revision")
    after_revision = _require_text(entry, "after_revision")
    if before_revision == after_revision:
        raise AssetLockError(f"{entry.get('id', '<unknown>')}: before and after revisions are identical")

    return LockedAsset(
        asset_id=_require_text(entry, "id"),
        project=_require_text(entry, "project"),
        upstream_time=_parse_upstream_time(entry),
        source_url=_require_text(entry, "source_url"),
        before_revision=before_revision,
        after_revision=after_revision,
        source_bundle_path=_require_text(entry, "source_bundle_path"),
        source_bundle_sha256=_require_sha256(entry, "source_bundle_sha256"),
        reproducer_path=_require_text(entry, "reproducer_path"),
        reproducer_sha256=_require_sha256(entry, "reproducer_sha256"),
        license_spdx=_require_text(entry, "license_spdx"),
        component=component,
    )


def select_chronological_pairs(registry: dict[str, Any], count: int) -> list[LockedAsset]:
    """Return the first ``count`` locked assets by upstream time, failing closed."""

    if count <= 0:
        raise AssetLockError("selection count must be positive")
    entries = registry.get("assets")
    if not isinstance(entries, list):
        raise AssetLockError("registry.assets must be a list")

    ids = [entry.get("id") for entry in entries if isinstance(entry, dict)]
    if len(ids) != len(set(ids)):
        raise AssetLockError("registry contains duplicate asset ids")

    locked = [validate_locked_asset(entry) for entry in entries if entry.get("status") == LOCKED_STATUS]
    locked.sort(key=lambda item: (item.upstream_time, item.asset_id))
    if len(locked) < count:
        raise AssetLockError(f"N0_ASSET_FAIL_STOP: need {count} locked pairs, found {len(locked)}")
    return locked[:count]


def load_registry(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        registry = json.load(handle)
    if not isinstance(registry, dict):
        raise AssetLockError("registry root must be an object")
    return registry


def selection_record(registry_path: Path, assets: Iterable[LockedAsset]) -> dict[str, Any]:
    selected = list(assets)
    return {
        "schema_version": "p5-basil-v94-asset-selection-v1",
        "registry_path": registry_path.as_posix(),
        "registry_sha256": sha256_file(registry_path),
        "selection_rule": "first eligible locked pairs ordered by upstream_time then asset_id",
        "selected_count": len(selected),
        "selected_ids": [asset.asset_id for asset in selected],
        "selected": [
            {
                "id": asset.asset_id,
                "project": asset.project,
                "upstream_time": asset.upstream_time.isoformat(),
                "before_revision": asset.before_revision,
                "after_revision": asset.after_revision,
                "component": asset.component,
                "reproducer_sha256": asset.reproducer_sha256,
            }
            for asset in selected
        ],
    }
