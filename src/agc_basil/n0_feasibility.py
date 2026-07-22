"""Static satisfiability audit for the frozen BASIL-v9.4 N0 gate.

This module never imports or executes upstream projects.  It reasons only from
the frozen asset registry, mechanical selection, and comparison contract.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class N0FeasibilityError(ValueError):
    """Raised when the frozen selection cannot be audited mechanically."""


@dataclass(frozen=True)
class N0Feasibility:
    selected_count: int
    pure_c1_ids: tuple[str, ...]
    non_marginal_ids: tuple[str, ...]
    maximum_possible_incremental_detections: int
    required_incremental_detections: int
    superiority_gate_satisfiable: bool
    disposition: str

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["pure_c1_ids"] = list(self.pure_c1_ids)
        result["non_marginal_ids"] = list(self.non_marginal_ids)
        result["proof_contract"] = {
            "frozen_baseline": "single-vs-batch marginal KS/MMD (marginal-only)",
            "basil_c1": "the same D_M witness inside the familywise C1/C2/C3 union",
            "dominance": (
                "A C1-only BASIL detection cannot be BASIL-only because the frozen "
                "strongest non-oracle union contains the marginal-only D_M check."
            ),
            "upper_bound": (
                "Only assets with a frozen C2 or C3 mapping can possibly contribute "
                "an incremental BASIL detection beyond the marginal-only baseline."
            ),
        }
        result["evidence_boundary"] = (
            "Static protocol satisfiability audit only; no dependency import, upstream "
            "reproducer, preflight, replay, N0, sealed access, or claim generation."
        )
        return result


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise N0FeasibilityError(f"{path}: JSON root must be an object")
    return value


def audit_n0_feasibility(
    selection_path: Path,
    registry_path: Path,
    *,
    required_incremental_detections: int = 2,
) -> N0Feasibility:
    """Bound the strongest-baseline improvement before any natural replay.

    Under the frozen comparison contract, the marginal-only baseline contains
    the same C1 statistic used by BASIL.  Consequently, a selected pair whose
    only mapped component is C1 cannot be an incremental BASIL detection.
    """

    if required_incremental_detections < 0:
        raise N0FeasibilityError("required increment must be non-negative")
    selection = _load_object(selection_path)
    registry = _load_object(registry_path)
    selected_ids = selection.get("selected_ids")
    if not isinstance(selected_ids, list) or not selected_ids:
        raise N0FeasibilityError("selection.selected_ids must be a non-empty list")
    if len(selected_ids) != len(set(selected_ids)):
        raise N0FeasibilityError("selection contains duplicate ids")

    entries = registry.get("assets")
    if not isinstance(entries, list):
        raise N0FeasibilityError("registry.assets must be a list")
    by_id = {
        entry.get("id"): entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }
    missing = [asset_id for asset_id in selected_ids if asset_id not in by_id]
    if missing:
        raise N0FeasibilityError(f"selected ids missing from registry: {missing}")

    pure_c1: list[str] = []
    non_marginal: list[str] = []
    for asset_id in selected_ids:
        entry = by_id[asset_id]
        if entry.get("status") != "ELIGIBLE_LOCKED":
            raise N0FeasibilityError(f"{asset_id}: selected asset is not ELIGIBLE_LOCKED")
        components = {
            value
            for value in (entry.get("component"), entry.get("secondary_component"))
            if isinstance(value, str) and value
        }
        if not components or not components <= {"C1", "C2", "C3"}:
            raise N0FeasibilityError(f"{asset_id}: unsupported component mapping {components}")
        if components == {"C1"}:
            pure_c1.append(asset_id)
        else:
            non_marginal.append(asset_id)

    maximum = len(non_marginal)
    satisfiable = maximum >= required_incremental_detections
    disposition = (
        "STATIC_GATE_NOT_REFUTED"
        if satisfiable
        else "N0_PREEXECUTION_SCIENTIFIC_FAIL_STOP_IMPOSSIBLE_SUPERIORITY_GATE"
    )
    return N0Feasibility(
        selected_count=len(selected_ids),
        pure_c1_ids=tuple(pure_c1),
        non_marginal_ids=tuple(non_marginal),
        maximum_possible_incremental_detections=maximum,
        required_incremental_detections=required_incremental_detections,
        superiority_gate_satisfiable=satisfiable,
        disposition=disposition,
    )

