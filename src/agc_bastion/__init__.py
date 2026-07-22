"""Development-only analytic machinery for BASTION-v7.41.

This package contains theorem checks and deterministic engineering utilities.
It does not load sealed data, train policies, or generate scientific claims.
"""

from .certificate import (
    Halfspace,
    PairwiseCorridor,
    certified_boundary_lower_bound,
    model_gap_bound,
    project_onto_halfspaces,
    support_box,
    support_lipschitz_bound,
)

__all__ = [
    "Halfspace",
    "PairwiseCorridor",
    "certified_boundary_lower_bound",
    "model_gap_bound",
    "project_onto_halfspaces",
    "support_box",
    "support_lipschitz_bound",
]

