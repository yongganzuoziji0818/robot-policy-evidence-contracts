"""Correctness primitives for RLRD direction-version 5.

This package supports analytic and synthetic G0 checks only.  Importing it
does not authorize development, formal, or sealed-data experiments.
"""

from .certification import (
    PathCertification,
    certify_locked_path,
    clopper_pearson_upper_bound,
)
from .guard import ExperimentNotAuthorized, require_authorized
from .metrics import (
    SafetyDebtSummary,
    adaptation_delay,
    recurrence_regression_gap,
    summarize_safety_debt,
)
from .n0_contract import N0Readiness, N0ReadinessError, assess_n0_readiness
from .n0_analysis import NaturalCensusSummary, PairInteraction, summarize_natural_census
from .planning import UpgradePlan, find_minimum_debt_path
from .protocol import CampaignKey, NonstationaryProtocol, PhaseSpec
from .profiles import (
    PairwiseIdentification,
    Profile,
    all_monotone_paths,
    binary_profiles,
    identify_pairwise_landscape,
    mobius_coefficients,
    reconstruct_risk,
)

__all__ = [
    "ExperimentNotAuthorized",
    "CampaignKey",
    "NonstationaryProtocol",
    "N0Readiness",
    "N0ReadinessError",
    "NaturalCensusSummary",
    "PathCertification",
    "PairwiseIdentification",
    "PairInteraction",
    "Profile",
    "PhaseSpec",
    "SafetyDebtSummary",
    "UpgradePlan",
    "all_monotone_paths",
    "adaptation_delay",
    "assess_n0_readiness",
    "binary_profiles",
    "certify_locked_path",
    "clopper_pearson_upper_bound",
    "find_minimum_debt_path",
    "identify_pairwise_landscape",
    "mobius_coefficients",
    "recurrence_regression_gap",
    "reconstruct_risk",
    "require_authorized",
    "summarize_safety_debt",
    "summarize_natural_census",
]
