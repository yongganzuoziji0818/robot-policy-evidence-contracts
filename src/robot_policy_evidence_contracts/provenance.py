"""Fail-closed artifact identity checks for evaluator evidence packages."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class ArtifactCheck:
    name: str
    path: Path
    expected_sha256: str
    observed_sha256: str | None
    valid: bool
    reason: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_artifact_manifest(
    artifacts: Mapping[str, tuple[str | Path, str]]
) -> tuple[ArtifactCheck, ...]:
    """Verify named files against explicit SHA-256 digests.

    Missing files, malformed hashes, and mismatches are returned as invalid
    records rather than ignored. This verifies identity only, not scientific
    validity or fitness for a downstream claim.
    """
    checks: list[ArtifactCheck] = []
    for name, (path_value, expected_value) in artifacts.items():
        path = Path(path_value)
        expected = str(expected_value).lower()
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            checks.append(ArtifactCheck(name, path, expected, None, False, "malformed SHA-256"))
            continue
        if not path.is_file():
            checks.append(ArtifactCheck(name, path, expected, None, False, "file missing"))
            continue
        observed = _sha256(path)
        valid = observed == expected
        checks.append(
            ArtifactCheck(
                name,
                path,
                expected,
                observed,
                valid,
                "match" if valid else "SHA-256 mismatch",
            )
        )
    return tuple(checks)
