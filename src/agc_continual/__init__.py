"""Development-only natural-version environment for P5 N0-B.

The package generates independently trained policy versions.  It contains no
profile-specific risk terms and is not a real-system or sealed environment.
"""

from .environment import CampaignCondition, evaluate_profile
from .training import TrainingSpec, train_team_version

__all__ = ["CampaignCondition", "TrainingSpec", "evaluate_profile", "train_team_version"]

