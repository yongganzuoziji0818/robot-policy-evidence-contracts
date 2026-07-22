"""Schema-only representation of piecewise-stationary P5 campaigns."""

from __future__ import annotations

from dataclasses import dataclass

ALLOWED_CHANGE_AXES = frozenset(
    {"task_distribution", "risk_pattern", "communication", "dynamics"}
)
ALLOWED_TOPOLOGIES = frozenset({"1U2G", "2U2G"})


@dataclass(frozen=True)
class CampaignKey:
    task_family: str
    topology: str
    version_lineage_seed: int
    change_axis: str

    def validate(self) -> None:
        if not self.task_family.strip():
            raise ValueError("task_family is required")
        if self.topology not in ALLOWED_TOPOLOGIES:
            raise ValueError(f"unsupported topology: {self.topology}")
        if self.change_axis not in ALLOWED_CHANGE_AXES:
            raise ValueError(f"unsupported change axis: {self.change_axis}")
        if self.version_lineage_seed < 0:
            raise ValueError("version_lineage_seed must be nonnegative")


@dataclass(frozen=True)
class PhaseSpec:
    phase_id: str
    key: CampaignKey
    distribution_id: str
    version_generation_rule_id: str
    rollout_seed_block_id: str
    deployment_exposure_schedule_id: str

    def validate(self) -> None:
        self.key.validate()
        for name, value in (
            ("phase_id", self.phase_id),
            ("distribution_id", self.distribution_id),
            ("version_generation_rule_id", self.version_generation_rule_id),
            ("rollout_seed_block_id", self.rollout_seed_block_id),
            ("deployment_exposure_schedule_id", self.deployment_exposure_schedule_id),
        ):
            if not value.strip():
                raise ValueError(f"{name} is required")


@dataclass(frozen=True)
class NonstationaryProtocol:
    phases: tuple[PhaseSpec, ...]
    locked_before_profile_observation: bool
    certification_within_stationary_phase: bool

    def validate(self, *, require_n0_scope: bool = False) -> None:
        if not self.phases:
            raise ValueError("at least one phase is required")
        if not self.locked_before_profile_observation:
            raise ValueError("version generation and thresholds must be locked before risk observation")
        if not self.certification_within_stationary_phase:
            raise ValueError("certification may not span a distribution change")
        phase_ids: set[str] = set()
        seed_blocks: set[str] = set()
        for phase in self.phases:
            phase.validate()
            if phase.phase_id in phase_ids:
                raise ValueError("phase_id values must be unique")
            if phase.rollout_seed_block_id in seed_blocks:
                raise ValueError("rollout seed blocks must be disjoint across phases")
            phase_ids.add(phase.phase_id)
            seed_blocks.add(phase.rollout_seed_block_id)
        if require_n0_scope:
            axes = {phase.key.change_axis for phase in self.phases}
            topologies = {phase.key.topology for phase in self.phases}
            lineages = {phase.key.version_lineage_seed for phase in self.phases}
            if len(axes) < 2 or len(topologies) < 2 or len(lineages) < 2:
                raise ValueError("N0 needs at least two axes, topologies, and lineages")
