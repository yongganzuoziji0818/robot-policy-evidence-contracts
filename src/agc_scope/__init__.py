"""Deterministic theory utilities for the SCOPE-v8 preflight.

These functions are analytic checks, not experiment runners and not empirical
evidence for a manuscript claim.
"""

from .capacity import (
    CapacityModel,
    class_blind_true_service_upper,
    route_value,
    routing_non_submodular_witness,
)

__all__ = [
    "CapacityModel",
    "class_blind_true_service_upper",
    "route_value",
    "routing_non_submodular_witness",
]

