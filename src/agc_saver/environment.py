"""Vectorized physical environment for SAVER-v7 N0.

The environment receives only a physical plan, a campaign condition and frozen
lineage offsets.  It never receives a hazard-memory identifier or lifecycle
decision.  Memory activation is implemented outside this module by filtering
plans, so no retain/retire outcome can be planted in the simulator.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from typing import Iterable

import torch


TOPOLOGY_ROLES = {
    "1U2G": ("uav", "ugv", "ugv"),
    "2U2G": ("uav", "uav", "ugv", "ugv"),
}


@dataclass(frozen=True)
class PlanSpec:
    route_clearance: float
    communication_reliance: float
    drive_authority: float

    @property
    def plan_id(self) -> str:
        return (
            f"c{self.route_clearance:.2f}-"
            f"q{self.communication_reliance:.2f}-"
            f"d{self.drive_authority:.2f}"
        )

    def to_dict(self) -> dict[str, float | str]:
        return {"plan_id": self.plan_id, **asdict(self)}


@dataclass(frozen=True)
class CampaignCondition:
    topology: str
    change_axis: str
    phase: str
    communication_loss: float
    dynamics_inertia: float
    action_noise: float = 0.025
    radio_drift_scale: float = 0.18
    hazard_half_width: float = 0.17
    formation_tolerance: float = 0.105
    progress_floor: float = 0.50
    desired_progress: float = 0.65

    def validate(self) -> None:
        if self.topology not in TOPOLOGY_ROLES:
            raise ValueError(f"unsupported topology: {self.topology}")
        if self.change_axis not in {"communication", "dynamics"}:
            raise ValueError(f"unsupported change axis: {self.change_axis}")
        if self.phase not in {"source", "target"}:
            raise ValueError(f"unsupported phase: {self.phase}")
        for name, value in (
            ("communication_loss", self.communication_loss),
            ("dynamics_inertia", self.dynamics_inertia),
            ("action_noise", self.action_noise),
        ):
            if not 0.0 <= value < 1.0:
                raise ValueError(f"{name} must lie in [0, 1)")


@dataclass(frozen=True)
class Lineage:
    topology: str
    seed: int
    sensor_bias: tuple[float, ...]
    radio_drift: tuple[float, ...]
    actuator_efficiency: tuple[float, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def make_plan_library(grid: dict[str, Iterable[float]]) -> list[PlanSpec]:
    plans = [
        PlanSpec(float(clearance), float(comm), float(drive))
        for clearance, comm, drive in product(
            grid["route_clearance"],
            grid["communication_reliance"],
            grid["drive_authority"],
        )
    ]
    if len({plan.plan_id for plan in plans}) != len(plans):
        raise ValueError("plan grid produces duplicate plan ids")
    return plans


def make_lineage(topology: str, seed: int, *, radio_drift_scale: float = 0.18) -> Lineage:
    if topology not in TOPOLOGY_ROLES:
        raise ValueError(f"unsupported topology: {topology}")
    roles = TOPOLOGY_ROLES[topology]
    generator = torch.Generator(device="cpu")
    generator.manual_seed(int(seed))
    n_agents = len(roles)
    sensor_bias = 0.012 * torch.randn(n_agents, generator=generator)
    radio_drift = radio_drift_scale * torch.randn(n_agents, generator=generator)
    role_base = torch.tensor([1.06 if role == "uav" else 0.94 for role in roles])
    actuator_efficiency = role_base + 0.018 * torch.randn(n_agents, generator=generator)
    return Lineage(
        topology=topology,
        seed=int(seed),
        sensor_bias=tuple(float(x) for x in sensor_bias),
        radio_drift=tuple(float(x) for x in radio_drift),
        actuator_efficiency=tuple(float(x) for x in actuator_efficiency),
    )


@torch.inference_mode()
def evaluate_plan(
    plan: PlanSpec,
    condition: CampaignCondition,
    lineage: Lineage,
    *,
    trials: int,
    seed: int,
    device: str = "cuda:0",
    batch_size: int = 32768,
) -> dict[str, float | int | str]:
    condition.validate()
    if lineage.topology != condition.topology:
        raise ValueError("lineage topology does not match campaign")
    if trials < 1 or batch_size < 1:
        raise ValueError("trials and batch_size must be positive")
    n_agents = len(TOPOLOGY_ROLES[condition.topology])
    if not all(
        len(values) == n_agents
        for values in (lineage.sensor_bias, lineage.radio_drift, lineage.actuator_efficiency)
    ):
        raise ValueError("lineage agent count mismatch")

    sensor_bias = torch.tensor(lineage.sensor_bias, dtype=torch.float32, device=device)
    radio_drift = torch.tensor(lineage.radio_drift, dtype=torch.float32, device=device)
    actuator = torch.tensor(lineage.actuator_efficiency, dtype=torch.float32, device=device)
    generator = torch.Generator(device=device)
    generator.manual_seed(int(seed))

    totals = {
        "failures": 0,
        "hazard_failures": 0,
        "formation_failures": 0,
        "progress_failures": 0,
    }
    utility_sum = 0.0
    dispersion_sum = 0.0
    progress_sum = 0.0
    processed = 0
    while processed < trials:
        current = min(batch_size, trials - processed)
        local_noise = condition.action_noise * torch.randn(
            current, n_agents, generator=generator, device=device
        )
        local_preference = plan.route_clearance + sensor_bias.unsqueeze(0) + local_noise
        fresh_team_reference = local_preference.mean(dim=1, keepdim=True)
        received = (
            torch.rand(current, n_agents, generator=generator, device=device)
            >= condition.communication_loss
        )
        stale_noise = 0.30 * condition.action_noise * torch.randn(
            current, n_agents, generator=generator, device=device
        )
        stale_reference = plan.route_clearance + radio_drift.unsqueeze(0) + stale_noise
        reference = torch.where(received, fresh_team_reference, stale_reference)
        lateral = local_preference + plan.communication_reliance * (
            reference - local_preference
        )

        dispersion = lateral.std(dim=1, unbiased=False)
        mean_clearance = lateral.mean(dim=1).abs()
        progress_by_agent = (
            plan.drive_authority
            * (1.0 - condition.dynamics_inertia)
            * actuator.unsqueeze(0)
        )
        progress_noise = 0.012 * torch.randn(
            current, n_agents, generator=generator, device=device
        )
        progress = (progress_by_agent + progress_noise).mean(dim=1)

        hazard_failure = mean_clearance < condition.hazard_half_width
        formation_failure = dispersion > condition.formation_tolerance
        progress_failure = progress < condition.progress_floor
        failure = hazard_failure | formation_failure | progress_failure

        communication_benefit = (
            0.20
            * plan.communication_reliance
            * (1.0 - condition.communication_loss)
        )
        utility = (
            1.0
            - (progress - condition.desired_progress).abs()
            - 0.80 * mean_clearance
            - 1.50 * dispersion
            + communication_benefit
        )
        totals["failures"] += int(failure.sum().item())
        totals["hazard_failures"] += int(hazard_failure.sum().item())
        totals["formation_failures"] += int(formation_failure.sum().item())
        totals["progress_failures"] += int(progress_failure.sum().item())
        utility_sum += float(utility.sum().item())
        dispersion_sum += float(dispersion.sum().item())
        progress_sum += float(progress.sum().item())
        processed += current

    return {
        "plan_id": plan.plan_id,
        "seed": int(seed),
        "trials": int(trials),
        **totals,
        "failure_rate": totals["failures"] / trials,
        "hazard_failure_rate": totals["hazard_failures"] / trials,
        "formation_failure_rate": totals["formation_failures"] / trials,
        "progress_failure_rate": totals["progress_failures"] / trials,
        "task_utility": utility_sum / trials,
        "mean_route_dispersion": dispersion_sum / trials,
        "mean_progress": progress_sum / trials,
    }
