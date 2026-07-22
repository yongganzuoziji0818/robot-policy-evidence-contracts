"""Frozen independent-team training rule for natural old/new versions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch

from .environment import TOPOLOGY_ROLES


@dataclass(frozen=True)
class TrainingSpec:
    topology: str
    change_axis: str
    seed: int
    steps: int = 1200
    batch_size: int = 4096
    learning_rate: float = 0.025
    communication_loss: float = 0.25
    dynamics_inertia: float = 0.25
    device: str = "cuda:0"

    def validate(self) -> None:
        if self.topology not in TOPOLOGY_ROLES:
            raise ValueError(f"unsupported topology: {self.topology}")
        if self.change_axis not in {"communication", "dynamics"}:
            raise ValueError(f"unsupported axis: {self.change_axis}")
        if self.seed < 0 or self.steps < 1 or self.batch_size < 2:
            raise ValueError("invalid training seed/budget")


def train_team_version(spec: TrainingSpec, output_path: str | Path) -> dict[str, Any]:
    """Train a team jointly; no profile or mixed-version outcome is observed."""
    spec.validate()
    torch.manual_seed(spec.seed)
    if spec.device.startswith("cuda"):
        torch.cuda.manual_seed_all(spec.seed)
    n_agents = len(TOPOLOGY_ROLES[spec.topology])
    device = torch.device(spec.device)
    # Random sign symmetry is resolved only by optimization and the frozen seed.
    route = torch.nn.Parameter(0.08 * torch.randn(n_agents, device=device))
    communication_gain = torch.nn.Parameter(torch.full((n_agents,), 0.45, device=device))
    dynamics_gain = torch.nn.Parameter(torch.full((n_agents,), 0.90, device=device))
    optimizer = torch.optim.Adam(
        (route, communication_gain, dynamics_gain), lr=spec.learning_rate
    )
    generator = torch.Generator(device=spec.device)
    generator.manual_seed(spec.seed + 97)
    final_loss = float("nan")
    for _ in range(spec.steps):
        message_received = (
            torch.rand(spec.batch_size, n_agents, generator=generator, device=device)
            >= spec.communication_loss
        )
        noise = 0.05 * torch.randn(
            spec.batch_size, n_agents, generator=generator, device=device
        )
        raw = route.unsqueeze(0) + noise
        team_reference = route.mean().expand(spec.batch_size, 1)
        raw = raw + message_received.float() * torch.sigmoid(
            communication_gain
        ).unsqueeze(0) * (team_reference - raw)
        lateral = (1.0 - spec.dynamics_inertia) * torch.tanh(
            raw * torch.nn.functional.softplus(dynamics_gain).unsqueeze(0)
        )
        mean = lateral.mean(dim=1)
        disagreement = lateral.var(dim=1, unbiased=False)
        # Symmetric safe routes around a central hazard; no preferred sign is planted.
        route_loss = (mean.square() - 0.42**2).square()
        hazard_loss = torch.relu(0.22 - mean.abs()).square()
        progress_loss = torch.relu(
            0.72 - torch.nn.functional.softplus(dynamics_gain).mean()
        ).square()
        loss = (
            route_loss.mean()
            + 5.0 * disagreement.mean()
            + 6.0 * hazard_loss.mean()
            + progress_loss
            + 0.002 * route.square().mean()
        )
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        final_loss = float(loss.detach().cpu())
    checkpoint = {
        "schema_version": "agc-continual-natural-team-v1",
        "development_only": True,
        "sealed": False,
        "training_spec": asdict(spec),
        "training_final_loss": final_loss,
        "policy_state": {
            "route_preference": route.detach().cpu(),
            "communication_gain": torch.sigmoid(communication_gain.detach()).cpu(),
            "dynamics_gain": torch.nn.functional.softplus(dynamics_gain.detach()).cpu(),
        },
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, path)
    return checkpoint


def load_checkpoint(path: str | Path, *, device: str = "cpu") -> dict[str, Any]:
    checkpoint = torch.load(path, map_location=device, weights_only=True)
    if not isinstance(checkpoint, dict) or checkpoint.get("sealed") is not False:
        raise ValueError("invalid or non-development checkpoint")
    return checkpoint

