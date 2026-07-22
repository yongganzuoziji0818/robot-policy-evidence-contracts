"""Frozen SAVER-v7 N0 ontology, diagnostics and gate summaries."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable, Mapping

from .environment import PlanSpec


@dataclass(frozen=True)
class HazardMemory:
    memory_id: str
    family: str
    physical_antecedent: str
    clearance: float | None = None
    drive_authority: float | None = None
    communication_reliance_min: float | None = None
    drive_authority_max: float | None = None
    source_age: int = 1

    def matches(self, plan: PlanSpec) -> bool:
        if self.clearance is not None and abs(plan.route_clearance - self.clearance) > 1e-9:
            return False
        if self.drive_authority is not None and abs(plan.drive_authority - self.drive_authority) > 1e-9:
            return False
        if (
            self.communication_reliance_min is not None
            and plan.communication_reliance < self.communication_reliance_min
        ):
            return False
        if (
            self.drive_authority_max is not None
            and plan.drive_authority > self.drive_authority_max
        ):
            return False
        return True

    def to_dict(self) -> dict[str, object]:
        return {
            "memory_id": self.memory_id,
            "family": self.family,
            "physical_antecedent": self.physical_antecedent,
            "clearance": self.clearance,
            "drive_authority": self.drive_authority,
            "communication_reliance_min": self.communication_reliance_min,
            "drive_authority_max": self.drive_authority_max,
            "source_age": self.source_age,
        }


def build_memory_ontology(change_axis: str) -> list[HazardMemory]:
    memories = [
        HazardMemory(
            memory_id=f"central-drive-{drive:.2f}",
            family="central_clearance",
            physical_antecedent=f"route_clearance=0.12 and drive_authority={drive:.2f}",
            clearance=0.12,
            drive_authority=drive,
        )
        for drive in (0.70, 1.00, 1.30)
    ]
    if change_axis == "communication":
        memories.extend(
            HazardMemory(
                memory_id=f"high-comm-clearance-{clearance:.2f}",
                family="high_communication_reliance",
                physical_antecedent=(
                    f"route_clearance={clearance:.2f} and communication_reliance>=0.90"
                ),
                clearance=clearance,
                communication_reliance_min=0.90,
            )
            for clearance in (0.22, 0.32, 0.42)
        )
    elif change_axis == "dynamics":
        memories.extend(
            HazardMemory(
                memory_id=f"low-drive-clearance-{clearance:.2f}",
                family="low_drive_authority",
                physical_antecedent=(
                    f"route_clearance={clearance:.2f} and drive_authority<=0.70"
                ),
                clearance=clearance,
                drive_authority_max=0.70,
            )
            for clearance in (0.22, 0.32, 0.42)
        )
    else:
        raise ValueError(f"unsupported change axis: {change_axis}")
    if len(memories) != 6:
        raise AssertionError("SAVER N0 requires exactly six memories")
    return memories


def _aggregate_plan_rows(rows: Iterable[Mapping[str, object]]) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, float]] = {}
    for row in rows:
        plan_id = str(row["plan_id"])
        item = totals.setdefault(
            plan_id,
            {"trials": 0.0, "failures": 0.0, "task_utility_weighted": 0.0},
        )
        trials = float(row["trials"])
        item["trials"] += trials
        item["failures"] += float(row["failures"])
        item["task_utility_weighted"] += float(row["task_utility"]) * trials
    for item in totals.values():
        item["failure_rate"] = item["failures"] / item["trials"]
        item["task_utility"] = item["task_utility_weighted"] / item["trials"]
    return totals


def _wilson_upper(failures: float, trials: float, z: float = 1.959963984540054) -> float:
    if trials <= 0:
        return 1.0
    proportion = failures / trials
    denominator = 1.0 + z * z / trials
    centre = proportion + z * z / (2.0 * trials)
    radius = z * sqrt(proportion * (1.0 - proportion) / trials + z * z / (4.0 * trials * trials))
    return min(1.0, (centre + radius) / denominator)


def _memory_evidence(
    memories: Iterable[HazardMemory],
    plans_by_id: Mapping[str, PlanSpec],
    aggregate: Mapping[str, Mapping[str, float]],
    *,
    tau_obsolete: float,
    tau_persistent: float,
) -> list[dict[str, object]]:
    evidence = []
    for memory in memories:
        matched = [plan_id for plan_id, plan in plans_by_id.items() if memory.matches(plan)]
        if not matched:
            raise ValueError(f"memory matches no plans: {memory.memory_id}")
        trials = sum(float(aggregate[plan_id]["trials"]) for plan_id in matched)
        failures = sum(float(aggregate[plan_id]["failures"]) for plan_id in matched)
        risk = failures / trials
        if risk >= tau_persistent:
            state = "persistent"
        elif risk <= tau_obsolete:
            state = "obsolete"
        else:
            state = "unidentified"
        evidence.append(
            {
                **memory.to_dict(),
                "matched_plan_ids": matched,
                "trials": int(trials),
                "failures": int(failures),
                "risk": risk,
                "wilson_upper_95": _wilson_upper(failures, trials),
                "applicability_state": state,
            }
        )
    return evidence


def _select_plan(
    plan_aggregate: Mapping[str, Mapping[str, float]],
    plans_by_id: Mapping[str, PlanSpec],
    active_memories: Iterable[HazardMemory],
) -> dict[str, object]:
    active = tuple(active_memories)
    eligible = [
        plan_id
        for plan_id, plan in plans_by_id.items()
        if not any(memory.matches(plan) for memory in active)
    ]
    if not eligible:
        raise ValueError("active memories exclude every plan")
    selected = max(
        eligible,
        key=lambda plan_id: (float(plan_aggregate[plan_id]["task_utility"]), plan_id),
    )
    metrics = plan_aggregate[selected]
    return {
        "plan_id": selected,
        "active_memory_ids": [memory.memory_id for memory in active],
        "failure_rate": float(metrics["failure_rate"]),
        "task_utility": float(metrics["task_utility"]),
    }


def summarize_campaign(
    *,
    change_axis: str,
    plans: list[PlanSpec],
    source_rows: list[Mapping[str, object]],
    target_rows: list[Mapping[str, object]],
    thresholds: Mapping[str, float],
) -> dict[str, object]:
    memories = build_memory_ontology(change_axis)
    plans_by_id = {plan.plan_id: plan for plan in plans}
    source_aggregate = _aggregate_plan_rows(source_rows)
    target_aggregate = _aggregate_plan_rows(target_rows)
    source_evidence = _memory_evidence(
        memories,
        plans_by_id,
        source_aggregate,
        tau_obsolete=float(thresholds["tau_obsolete"]),
        tau_persistent=float(thresholds["tau_persistent"]),
    )
    target_evidence = _memory_evidence(
        memories,
        plans_by_id,
        target_aggregate,
        tau_obsolete=float(thresholds["tau_obsolete"]),
        tau_persistent=float(thresholds["tau_persistent"]),
    )
    target_by_id = {str(item["memory_id"]): item for item in target_evidence}
    source_by_id = {str(item["memory_id"]): item for item in source_evidence}
    persistent = [memory for memory in memories if target_by_id[memory.memory_id]["applicability_state"] == "persistent"]

    source_minimum_pass = all(
        float(item["risk"]) >= float(thresholds["minimum_source_memory_risk"])
        for item in source_evidence
    )
    oracle_ids = {memory.memory_id for memory in persistent}
    keep_all = _select_plan(target_aggregate, plans_by_id, memories)
    retire_all = _select_plan(target_aggregate, plans_by_id, ())
    oracle = _select_plan(target_aggregate, plans_by_id, persistent)

    age_active: list[HazardMemory] = []
    uncertainty_active = [
        memory
        for memory in memories
        if float(source_by_id[memory.memory_id]["wilson_upper_95"])
        >= float(thresholds["tau_persistent"])
    ]
    age = _select_plan(target_aggregate, plans_by_id, age_active)
    uncertainty = _select_plan(target_aggregate, plans_by_id, uncertainty_active)
    age_equivalent = {memory.memory_id for memory in age_active} == oracle_ids
    uncertainty_equivalent = {memory.memory_id for memory in uncertainty_active} == oracle_ids

    persistent_count = sum(
        item["applicability_state"] == "persistent" for item in target_evidence
    )
    obsolete_count = sum(
        item["applicability_state"] == "obsolete" for item in target_evidence
    )
    stale_task_cost = float(oracle["task_utility"]) - float(keep_all["task_utility"])
    forgotten_hazard_cost = float(retire_all["failure_rate"]) - float(oracle["failure_rate"])
    witness = bool(
        source_minimum_pass
        and persistent_count >= 1
        and obsolete_count >= 1
        and float(oracle["failure_rate"]) <= float(thresholds["tau_safe_plan"])
        and stale_task_cost >= float(thresholds["stale_task_cost_sesoi"])
        and forgotten_hazard_cost >= float(thresholds["forgotten_hazard_sesoi"])
        and not age_equivalent
        and not uncertainty_equivalent
    )
    return {
        "source_memory_gate_pass": source_minimum_pass,
        "persistent_memory_count": int(persistent_count),
        "obsolete_memory_count": int(obsolete_count),
        "unidentified_memory_count": 6 - int(persistent_count) - int(obsolete_count),
        "stale_task_cost": stale_task_cost,
        "forgotten_hazard_cost": forgotten_hazard_cost,
        "age_oracle_equivalent": age_equivalent,
        "source_uncertainty_oracle_equivalent": uncertainty_equivalent,
        "two_sided_witness": witness,
        "source_memory_evidence": source_evidence,
        "target_memory_evidence": target_evidence,
        "diagnostic_policies": {
            "keep_all": keep_all,
            "retire_all": retire_all,
            "age_decay": age,
            "source_uncertainty_filter": uncertainty,
            "oracle_applicability": oracle,
        },
    }


def summarize_gate(campaign_summaries: Iterable[Mapping[str, object]], minimum: int) -> dict[str, object]:
    summaries = list(campaign_summaries)
    witnesses = [item for item in summaries if bool(item["two_sided_witness"])]
    axes = {str(item["change_axis"]) for item in witnesses}
    topologies = {str(item["topology"]) for item in witnesses}
    replicates = {int(item["lineage_replicate"]) for item in witnesses}
    pass_gate = bool(
        len(witnesses) >= minimum
        and axes == {"communication", "dynamics"}
        and topologies == {"1U2G", "2U2G"}
        and replicates == {1, 2}
        and all(bool(item["source_memory_gate_pass"]) for item in summaries)
    )
    return {
        "witness_count": len(witnesses),
        "campaign_count": len(summaries),
        "witness_campaign_ids": [str(item["campaign_id"]) for item in witnesses],
        "covered_axes": sorted(axes),
        "covered_topologies": sorted(topologies),
        "covered_lineage_replicates": sorted(replicates),
        "n0_gate_pass": pass_gate,
        "decision": "N0_PASS_READY_FOR_SEPARATE_G0_DECISION" if pass_gate else "N0_FAIL_STOP",
    }
