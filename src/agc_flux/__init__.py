"""FLUX-v8 analytic source/deposition identifiability primitives."""

from .inverse import (
    FluxModel,
    determinant_2x2,
    information_matrix,
    min_eigenvalue_2x2,
    nullspace_projected_information,
)
from .simulation import (
    Campaign,
    FieldConfig,
    MethodResult,
    make_campaign,
    run_method,
)
from .g1_simulation import (
    G1Campaign,
    G1Config,
    G1MethodResult,
    G1_METHODS,
    MISMATCH_FAMILIES,
    make_g1_campaign,
    run_g1_method,
)

__all__ = [
    "FluxModel",
    "determinant_2x2",
    "information_matrix",
    "min_eigenvalue_2x2",
    "nullspace_projected_information",
    "Campaign",
    "FieldConfig",
    "MethodResult",
    "make_campaign",
    "run_method",
    "G1Campaign",
    "G1Config",
    "G1MethodResult",
    "G1_METHODS",
    "MISMATCH_FAMILIES",
    "make_g1_campaign",
    "run_g1_method",
]
