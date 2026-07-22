"""Fail-closed input contract for natural-interaction N0-B campaigns.

The contract validates provenance and scope only.  It never loads a checkpoint,
runs a rollout, or inspects sealed assets.
"""

from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .protocol import ALLOWED_CHANGE_AXES, ALLOWED_TOPOLOGIES


class N0ReadinessError(ValueError):
    """Raised when N0-B inputs are incomplete or violate the frozen boundary."""


@dataclass(frozen=True)
class N0Readiness:
    ready: bool
    errors: tuple[str, ...]
    campaign_count: int
    profile_campaign_count: int
    lineage_count: int


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value.lower()
    )


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _module_exists(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, AttributeError):
        return False


def validate_lineage_registry(
    registry: Mapping[str, Any], *, verify_files: bool = True
) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    ids: set[str] = set()
    if registry.get("sealed") is not False:
        errors.append("registry.sealed must be explicit false")
    if registry.get("natural_versions") is not True:
        errors.append("registry.natural_versions must be explicit true")
    lineages = registry.get("lineages")
    if not isinstance(lineages, list) or not lineages:
        return errors + ["registry.lineages must be a nonempty list"], ids

    for index, item in enumerate(lineages):
        prefix = f"registry.lineages[{index}]"
        if not isinstance(item, Mapping):
            errors.append(f"{prefix} must be an object")
            continue
        lineage_id = item.get("lineage_id")
        if not _nonempty_string(lineage_id):
            errors.append(f"{prefix}.lineage_id is required")
            continue
        if lineage_id in ids:
            errors.append(f"duplicate lineage_id: {lineage_id}")
        ids.add(str(lineage_id))
        if item.get("generation_kind") not in {"independent_training", "frozen_finetune"}:
            errors.append(f"{prefix}.generation_kind is not a natural-version rule")
        for key in ("selection_rule_id", "training_budget_id", "training_seed"):
            value = item.get(key)
            if key == "training_seed":
                if not isinstance(value, int) or value < 0:
                    errors.append(f"{prefix}.{key} must be a nonnegative integer")
            elif not _nonempty_string(value):
                errors.append(f"{prefix}.{key} is required")
        for version in ("old", "new"):
            asset = item.get(version)
            asset_prefix = f"{prefix}.{version}"
            if not isinstance(asset, Mapping):
                errors.append(f"{asset_prefix} must be an object")
                continue
            path_value = asset.get("path")
            expected_hash = asset.get("sha256")
            if not _nonempty_string(path_value):
                errors.append(f"{asset_prefix}.path is required")
                continue
            if not _is_sha256(expected_hash):
                errors.append(f"{asset_prefix}.sha256 must be a 64-hex digest")
                continue
            if verify_files:
                path = Path(str(path_value))
                if not path.is_file():
                    errors.append(f"{asset_prefix}.path does not exist: {path}")
                elif sha256_file(path) != str(expected_hash).lower():
                    errors.append(f"{asset_prefix}.sha256 mismatch: {path}")
    return errors, ids


def validate_campaign_manifest(
    manifest: Mapping[str, Any], *, lineage_ids: set[str]
) -> tuple[list[str], int, int]:
    errors: list[str] = []
    if manifest.get("direction_version") != 5:
        errors.append("manifest.direction_version must equal 5")
    if manifest.get("authorized") is not True:
        errors.append("manifest.authorized must be explicit true")
    if manifest.get("development_experiment_authorized") is not True:
        errors.append("development_experiment_authorized must be explicit true")
    for key in ("formal_experiment_authorized", "sealed_data_authorized", "claim_generation_allowed"):
        if manifest.get(key) is not False:
            errors.append(f"{key} must be explicit false")
    thresholds = manifest.get("risk_thresholds")
    if not isinstance(thresholds, Mapping):
        errors.append("risk_thresholds must be an object")
    else:
        target, hard = thresholds.get("tau_target"), thresholds.get("tau_hard")
        if not isinstance(target, (int, float)) or not isinstance(hard, (int, float)) or not 0 <= target < hard <= 1:
            errors.append("risk_thresholds must satisfy 0 <= tau_target < tau_hard <= 1")
        if thresholds.get("frozen_before_profile_observation") is not True:
            errors.append("risk thresholds must be frozen before profile observation")

    campaigns = manifest.get("campaigns")
    if not isinstance(campaigns, list) or not campaigns:
        return errors + ["campaigns must be a nonempty list"], 0, 0
    campaign_ids: set[str] = set()
    seed_blocks: set[str] = set()
    axes: set[str] = set()
    topologies: set[str] = set()
    used_lineages: set[str] = set()
    cell_lineages: dict[tuple[str, str], set[str]] = {}
    profile_campaign_count = 0
    for index, campaign in enumerate(campaigns):
        prefix = f"campaigns[{index}]"
        if not isinstance(campaign, Mapping):
            errors.append(f"{prefix} must be an object")
            continue
        campaign_id = campaign.get("campaign_id")
        topology = campaign.get("topology")
        axis = campaign.get("change_axis")
        lineage_id = campaign.get("lineage_id")
        seed_block = campaign.get("rollout_seed_block_id")
        for key in ("campaign_id", "task_family", "distribution_id", "failure_event_id", "exposure_schedule_id", "rollout_seed_block_id"):
            if not _nonempty_string(campaign.get(key)):
                errors.append(f"{prefix}.{key} is required")
        if campaign_id in campaign_ids:
            errors.append(f"duplicate campaign_id: {campaign_id}")
        campaign_ids.add(str(campaign_id))
        if seed_block in seed_blocks:
            errors.append(f"duplicate rollout_seed_block_id: {seed_block}")
        seed_blocks.add(str(seed_block))
        if topology not in ALLOWED_TOPOLOGIES:
            errors.append(f"{prefix}.topology unsupported: {topology}")
        else:
            topologies.add(str(topology))
            profile_campaign_count += 2 ** (3 if topology == "1U2G" else 4)
        if axis not in ALLOWED_CHANGE_AXES:
            errors.append(f"{prefix}.change_axis unsupported: {axis}")
        else:
            axes.add(str(axis))
        if lineage_id not in lineage_ids:
            errors.append(f"{prefix}.lineage_id absent from registry: {lineage_id}")
        else:
            if lineage_id in used_lineages:
                errors.append(f"lineage_id may appear in only one campaign: {lineage_id}")
            used_lineages.add(str(lineage_id))
            if topology in ALLOWED_TOPOLOGIES and axis in ALLOWED_CHANGE_AXES:
                cell_lineages.setdefault((str(topology), str(axis)), set()).add(str(lineage_id))
        if campaign.get("all_profiles_required") is not True:
            errors.append(f"{prefix}.all_profiles_required must be explicit true")

    if len(axes) < 2:
        errors.append("N0-B requires at least two change axes")
    if len(topologies) < 2:
        errors.append("N0-B requires both 1U2G and 2U2G topologies")
    if axes and topologies:
        for topology in sorted(topologies):
            for axis in sorted(axes):
                if len(cell_lineages.get((topology, axis), set())) < 2:
                    errors.append(
                        f"N0-B requires two independent lineages in cell {topology}/{axis}"
                    )
    return errors, len(campaigns), profile_campaign_count


def assess_n0_readiness(
    registry: Mapping[str, Any],
    manifest: Mapping[str, Any],
    *,
    environment_package: str = "agc_continual",
    rollout_adapter_module: str | None = None,
    verify_files: bool = True,
) -> N0Readiness:
    errors, lineage_ids = validate_lineage_registry(registry, verify_files=verify_files)
    manifest_errors, campaigns, profile_campaigns = validate_campaign_manifest(
        manifest, lineage_ids=lineage_ids
    )
    errors.extend(manifest_errors)
    if not _module_exists(environment_package):
        errors.append(f"environment package not importable: {environment_package}")
    if not rollout_adapter_module:
        errors.append("rollout_adapter_module is required")
    elif not _module_exists(rollout_adapter_module):
        errors.append(f"rollout adapter not importable: {rollout_adapter_module}")
    return N0Readiness(
        ready=not errors,
        errors=tuple(errors),
        campaign_count=campaigns,
        profile_campaign_count=profile_campaigns,
        lineage_count=len(lineage_ids),
    )
