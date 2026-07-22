from __future__ import annotations

import tempfile
import unittest
import importlib.util
from pathlib import Path

HAS_TORCH = importlib.util.find_spec("torch") is not None
if HAS_TORCH:
    import torch
    from agc_continual.environment import CampaignCondition, evaluate_profile
    from agc_continual.training import TrainingSpec, load_checkpoint, train_team_version


@unittest.skipUnless(HAS_TORCH, "agc_continual tests require torch")
class ContinualEnvironmentTests(unittest.TestCase):
    def test_checkpoint_generation_is_deterministic_on_cpu(self) -> None:
        spec = TrainingSpec(
            topology="1U2G", change_axis="communication", seed=42,
            steps=4, batch_size=32, device="cpu",
        )
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.pt"
            second = Path(directory) / "second.pt"
            train_team_version(spec, first)
            train_team_version(spec, second)
            a, b = load_checkpoint(first), load_checkpoint(second)
        for key in a["policy_state"]:
            self.assertTrue(torch.equal(a["policy_state"][key], b["policy_state"][key]))

    def test_profile_evaluation_is_deterministic_and_version_blind(self) -> None:
        checkpoint = {
            "policy_state": {
                "route_preference": torch.tensor([0.8, 0.8, 0.8]),
                "communication_gain": torch.tensor([0.5, 0.5, 0.5]),
                "dynamics_gain": torch.tensor([1.0, 1.0, 1.0]),
            }
        }
        condition = CampaignCondition("1U2G", "communication", 0.3, 0.2)
        first = evaluate_profile(checkpoint, checkpoint, (0, 1, 0), condition, trials=128, seed=9, device="cpu")
        second = evaluate_profile(checkpoint, checkpoint, (1, 0, 1), condition, trials=128, seed=9, device="cpu")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
