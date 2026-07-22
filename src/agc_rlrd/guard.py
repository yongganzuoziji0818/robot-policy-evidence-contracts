"""Fail-closed manifest checks for every executable P5 stage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


class ExperimentNotAuthorized(PermissionError):
    """Raised when a manifest does not explicitly authorize the requested work."""


def load_manifest(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict):
        raise ValueError("manifest root must be an object")
    return manifest


def require_authorized(
    manifest: Mapping[str, Any],
    *,
    expected_direction_version: int = 5,
    formal: bool = False,
    sealed: bool = False,
    claim_generation: bool = False,
) -> None:
    """Require explicit booleans; absent or truthy non-booleans fail closed."""
    if manifest.get("direction_version") != expected_direction_version:
        raise ExperimentNotAuthorized("direction version mismatch")
    requirements = [("authorized", True)]
    if formal:
        requirements.append(("formal_experiment_authorized", True))
    if sealed:
        requirements.append(("sealed_data_authorized", True))
    if claim_generation:
        requirements.append(("claim_generation_allowed", True))
    denied = [key for key, required in requirements if manifest.get(key) is not required]
    if denied:
        raise ExperimentNotAuthorized("missing explicit authorization: " + ", ".join(denied))
