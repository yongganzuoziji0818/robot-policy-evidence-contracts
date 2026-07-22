from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agc_basil.experiment import (  # noqa: E402
    FAMILIES,
    _component_pvalues,
    _joint_independence_pvalue,
    _sample_reference,
    _wilson_lower,
    run_g0,
)


def test_family_contract_counts() -> None:
    assert len(FAMILIES) == 13
    assert sum(f.truth == "clean" for f in FAMILIES) == 4
    assert sum(f.truth != "clean" for f in FAMILIES) == 9


def test_parity_is_pairwise_independent_but_joint_detectable() -> None:
    rng = np.random.default_rng(7)
    a = rng.integers(0, 2, 4096, dtype=np.int8)
    b = rng.integers(0, 2, 4096, dtype=np.int8)
    samples = np.stack([a, b, np.bitwise_xor(a, b)], axis=1)
    assert max(abs(np.corrcoef(samples, rowvar=False)[np.triu_indices(3, 1)])) < 0.06
    assert _joint_independence_pvalue(samples) < 1e-10


def test_component_tests_do_not_confuse_clean_data() -> None:
    rng = np.random.default_rng(11)
    reference = rng.integers(0, 2, (8192, 3), dtype=np.int8)
    batch = rng.integers(0, 2, (8192, 3), dtype=np.int8)
    int0 = rng.integers(0, 2, 8192, dtype=np.int8)
    int1 = rng.integers(0, 2, 8192, dtype=np.int8)
    pvalues = _component_pvalues(reference, batch, int0, int1)
    assert all(p > 0.001 / 3 for p in pvalues.values())


def test_clean_deterministic_is_a_fixed_input_product_point_mass() -> None:
    family = next(f for f in FAMILIES if f.name == "clean_deterministic")
    samples = _sample_reference(np.random.default_rng(5), 128, family)
    assert np.all(samples == np.array([0, 1, 0], dtype=np.int8))
    assert _joint_independence_pvalue(samples) == 1.0


def test_wilson_contract() -> None:
    assert _wilson_lower(96, 96) >= 0.96
    assert _wilson_lower(95, 96) < 0.96


def test_small_g0_is_reproducible(tmp_path: Path) -> None:
    first = run_g0(tmp_path / "a", blocks_per_family=2, queries=256)
    second = run_g0(tmp_path / "b", blocks_per_family=2, queries=256)
    assert first == second
    assert (tmp_path / "a" / "raw_blocks.jsonl").read_bytes() == (tmp_path / "b" / "raw_blocks.jsonl").read_bytes()
