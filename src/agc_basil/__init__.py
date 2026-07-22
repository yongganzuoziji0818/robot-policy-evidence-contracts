"""BASIL product-kernel conformance experiments for P5 v9.4."""

from __future__ import annotations


__all__ = ["AssetLockError", "run_g0", "select_chronological_pairs"]


def __getattr__(name: str):
    """Keep offline asset tooling independent from NumPy-backed experiments."""

    if name in {"AssetLockError", "select_chronological_pairs"}:
        from .assets import AssetLockError, select_chronological_pairs

        return {"AssetLockError": AssetLockError, "select_chronological_pairs": select_chronological_pairs}[name]
    if name == "run_g0":
        from .experiment import run_g0

        return run_g0
    raise AttributeError(name)
