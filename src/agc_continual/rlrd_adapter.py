"""RLRD rollout adapter for frozen natural-version checkpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .environment import CampaignCondition, evaluate_profile
from .training import load_checkpoint


def run_profile(
    old_checkpoint_path: str | Path,
    new_checkpoint_path: str | Path,
    profile: Sequence[int],
    condition: CampaignCondition,
    *,
    trials: int,
    seed: int,
    device: str = "cuda:0",
    batch_size: int = 16384,
):
    old = load_checkpoint(old_checkpoint_path)
    new = load_checkpoint(new_checkpoint_path)
    return evaluate_profile(
        old,
        new,
        profile,
        condition,
        trials=trials,
        seed=seed,
        device=device,
        batch_size=batch_size,
    )

