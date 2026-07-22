"""Vectorized heterogeneous coordination environment for natural version mixing.

Each independently trained checkpoint maps a role and noisy local context to a
lateral route.  A profile composes old/new controllers agent by agent.  Failure
is computed from formation disagreement, central-hazard exposure, and progress;
there is deliberately no term that receives or keys on the version profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import torch


TOPOLOGY_ROLES = {
    "1U2G": ("uav", "ugv", "ugv"),
    "2U2G": ("uav", "uav", "ugv", "ugv"),
}


@dataclass(frozen=True)
class CampaignCondition:
    topology: str
    change_axis: str
    communication_loss: float
    dynamics_inertia: float
    action_noise: float = 0.045
    hazard_half_width: float = 0.20
    formation_tolerance: float = 0.34
    progress_floor: float = 0.50

    def validate(self) -> None:
        if self.topology not in TOPOLOGY_ROLES:
            raise ValueError(f"unsupported topology: {self.topology}")
        if self.change_axis not in {"communication", "dynamics"}:
            raise ValueError(f"unsupported N0 axis: {self.change_axis}")
        for name, value in (
            ("communication_loss", self.communication_loss),
            ("dynamics_inertia", self.dynamics_inertia),
            ("action_noise", self.action_noise),
        ):
            if not 0.0 <= value < 1.0:
                raise ValueError(f"{name} must lie in [0, 1)")


def _checkpoint_tensor(checkpoint: Mapping[str, object], key: str, device: str) -> torch.Tensor:
    state = checkpoint.get("policy_state")
    if not isinstance(state, Mapping) or key not in state:
        raise ValueError(f"checkpoint missing policy_state.{key}")
    return torch.as_tensor(state[key], dtype=torch.float32, device=device)


@torch.inference_mode()
def evaluate_profile(
    old_checkpoint: Mapping[str, object],
    new_checkpoint: Mapping[str, object],
    profile: Sequence[int],
    condition: CampaignCondition,
    *,
    trials: int,
    seed: int,
    device: str = "cuda:0",
    batch_size: int = 16384,
) -> dict[str, float | int]:
    condition.validate()
    roles = TOPOLOGY_ROLES[condition.topology]
    profile_tuple = tuple(int(value) for value in profile)
    if len(profile_tuple) != len(roles) or any(value not in (0, 1) for value in profile_tuple):
        raise ValueError("profile must be binary with one entry per agent")
    if trials < 1 or batch_size < 1:
        raise ValueError("trials and batch_size must be positive")

    old_route = _checkpoint_tensor(old_checkpoint, "route_preference", device)
    new_route = _checkpoint_tensor(new_checkpoint, "route_preference", device)
    old_comm = _checkpoint_tensor(old_checkpoint, "communication_gain", device)
    new_comm = _checkpoint_tensor(new_checkpoint, "communication_gain", device)
    old_dyn = _checkpoint_tensor(old_checkpoint, "dynamics_gain", device)
    new_dyn = _checkpoint_tensor(new_checkpoint, "dynamics_gain", device)
    n_agents = len(roles)
    for tensor in (old_route, new_route, old_comm, new_comm, old_dyn, new_dyn):
        if tensor.shape != (n_agents,):
            raise ValueError("checkpoint topology/agent count mismatch")
    selector = torch.tensor(profile_tuple, device=device, dtype=torch.bool)
    route = torch.where(selector, new_route, old_route)
    comm_gain = torch.where(selector, new_comm, old_comm)
    dynamics_gain = torch.where(selector, new_dyn, old_dyn)
    role_speed = torch.tensor(
        [1.00 if role == "uav" else 0.82 for role in roles], device=device
    )

    generator = torch.Generator(device=device)
    generator.manual_seed(seed)
    failures = 0
    formation_failures = 0
    hazard_failures = 0
    progress_failures = 0
    processed = 0
    sum_dispersion = 0.0
    while processed < trials:
        current = min(batch_size, trials - processed)
        common_route_shock = 0.10 * torch.randn(
            current, 1, generator=generator, device=device
        )
        message_received = torch.rand(
            current, n_agents, generator=generator, device=device
        ) >= condition.communication_loss
        local_noise = condition.action_noise * torch.randn(
            current, n_agents, generator=generator, device=device
        )
        communicated_mean = route.mean().expand(current, 1)
        desired = route.unsqueeze(0).expand(current, -1) + local_noise
        desired = desired + message_received.float() * comm_gain.unsqueeze(0) * (
            communicated_mean - desired
        )
        desired = desired + common_route_shock
        lateral = torch.tanh(desired * dynamics_gain.unsqueeze(0))
        lateral = (1.0 - condition.dynamics_inertia) * lateral

        dispersion = lateral.std(dim=1, unbiased=False)
        mean_abs_route = lateral.mean(dim=1).abs()
        progress = (role_speed.unsqueeze(0) * dynamics_gain.unsqueeze(0)).mean(dim=1)
        formation_failure = dispersion > condition.formation_tolerance
        hazard_failure = mean_abs_route < condition.hazard_half_width
        progress_failure = progress < condition.progress_floor
        failure = formation_failure | hazard_failure | progress_failure
        failures += int(failure.sum().item())
        formation_failures += int(formation_failure.sum().item())
        hazard_failures += int(hazard_failure.sum().item())
        progress_failures += int(progress_failure.sum().item())
        sum_dispersion += float(dispersion.sum().item())
        processed += current
    return {
        "failures": failures,
        "trials": trials,
        "failure_rate": failures / trials,
        "formation_failure_rate": formation_failures / trials,
        "hazard_failure_rate": hazard_failures / trials,
        "progress_failure_rate": progress_failures / trials,
        "mean_route_dispersion": sum_dispersion / trials,
        "seed": seed,
    }

