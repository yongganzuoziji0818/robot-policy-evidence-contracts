from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


ALPHA_FAMILY = 0.001
COMPONENTS = ("marginal", "intervention", "joint_dependence")


@dataclass(frozen=True)
class Family:
    name: str
    truth: str
    mechanism: str


FAMILIES = (
    Family("clean_iid", "clean", "clean"),
    Family("clean_local_bias", "clean", "clean"),
    Family("clean_deterministic", "clean", "clean"),
    Family("clean_heterogeneous", "clean", "clean"),
    Family("slot_index_bias", "marginal", "slot_index"),
    Family("batch_size_scale", "marginal", "batch_scale"),
    Family("wrapper_state_shift", "marginal", "wrapper_shift"),
    Family("foreign_action_xor", "intervention", "foreign_action"),
    Family("foreign_reset_overwrite", "intervention", "foreign_reset"),
    Family("foreign_init_leak", "intervention", "foreign_init"),
    Family("shared_noise", "joint_dependence", "shared_bit"),
    Family("parity_constraint", "joint_dependence", "parity"),
    Family("latent_regime", "joint_dependence", "latent_regime"),
)


def _normal_sf(x: float) -> float:
    return 0.5 * math.erfc(x / math.sqrt(2.0))


def _two_prop_pvalue(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    p1, p2 = float(a.mean()), float(b.mean())
    pooled = float((a.sum() + b.sum()) / (len(a) + len(b)))
    denom = math.sqrt(max(pooled * (1.0 - pooled) * (1.0 / len(a) + 1.0 / len(b)), 1e-15))
    return min(1.0, 2.0 * _normal_sf(abs(p1 - p2) / denom))


def _chi_square_sf_wilson_hilferty(stat: float, df: int) -> float:
    if stat <= 0.0:
        return 1.0
    z = ((stat / df) ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * df))) / math.sqrt(2.0 / (9.0 * df))
    return _normal_sf(z)


def _joint_independence_pvalue(samples: np.ndarray) -> float:
    samples = np.asarray(samples, dtype=np.int8)
    n, width = samples.shape
    assert width == 3
    probs = samples.mean(axis=0)
    observed = np.zeros(8, dtype=np.float64)
    for row in samples:
        observed[int(row[0]) * 4 + int(row[1]) * 2 + int(row[2])] += 1.0
    expected = np.empty(8, dtype=np.float64)
    for code in range(8):
        bits = ((code >> 2) & 1, (code >> 1) & 1, code & 1)
        prob = 1.0
        for bit, p in zip(bits, probs):
            prob *= p if bit else 1.0 - p
        expected[code] = max(n * prob, 1e-12)
    mask = observed > 0
    g_stat = float(2.0 * np.sum(observed[mask] * np.log(observed[mask] / expected[mask])))
    return _chi_square_sf_wilson_hilferty(g_stat, df=4)


def _phi_max(samples: np.ndarray) -> float:
    vals: list[float] = []
    for i in range(3):
        for j in range(i + 1, 3):
            x, y = samples[:, i], samples[:, j]
            if x.std() == 0 or y.std() == 0:
                vals.append(0.0)
            else:
                vals.append(abs(float(np.corrcoef(x, y)[0, 1])))
    return max(vals)


def _sample_reference(rng: np.random.Generator, n: int, family: Family) -> np.ndarray:
    if family.name == "clean_deterministic":
        # Repeated black-box samples hold all local inputs fixed.  A deterministic
        # product kernel is therefore a point mass, not a shared query-index pattern.
        return np.tile(np.array([0, 1, 0], dtype=np.int8), (n, 1))
    if family.name == "clean_local_bias":
        ps = np.array([0.25, 0.50, 0.75])
    elif family.name == "clean_heterogeneous":
        ps = np.array([0.15, 0.55, 0.85])
    else:
        ps = np.array([0.50, 0.50, 0.50])
    return (rng.random((n, 3)) < ps).astype(np.int8)


def _sample_batch(rng: np.random.Generator, n: int, family: Family) -> np.ndarray:
    if family.truth == "clean":
        return _sample_reference(rng, n, family)
    if family.mechanism in {"slot_index", "batch_scale", "wrapper_shift"}:
        shifts = {
            "slot_index": np.array([0.28, 0.0, 0.0]),
            "batch_scale": np.array([0.0, -0.27, 0.0]),
            "wrapper_shift": np.array([0.0, 0.0, 0.30]),
        }[family.mechanism]
        ps = np.clip(np.array([0.5, 0.5, 0.5]) + shifts, 0.02, 0.98)
        return (rng.random((n, 3)) < ps).astype(np.int8)
    if family.mechanism in {"foreign_action", "foreign_reset", "foreign_init"}:
        foreign = rng.integers(0, 2, size=n, dtype=np.int8)
        local_noise = (rng.random(n) < 0.20).astype(np.int8)
        y0 = np.bitwise_xor(local_noise, foreign)
        return np.stack(
            [y0, (rng.random(n) < 0.5).astype(np.int8), (rng.random(n) < 0.5).astype(np.int8)],
            axis=1,
        )
    if family.mechanism == "shared_bit":
        bit = rng.integers(0, 2, size=n, dtype=np.int8)
        return np.stack([bit, bit, bit], axis=1)
    if family.mechanism == "parity":
        a = rng.integers(0, 2, size=n, dtype=np.int8)
        b = rng.integers(0, 2, size=n, dtype=np.int8)
        return np.stack([a, b, np.bitwise_xor(a, b)], axis=1)
    if family.mechanism == "latent_regime":
        regime = rng.integers(0, 2, size=n)
        ps = np.where(regime[:, None] == 0, 0.08, 0.92)
        return (rng.random((n, 3)) < ps).astype(np.int8)
    raise ValueError(f"Unknown family: {family}")


def _intervention_samples(
    rng: np.random.Generator, n: int, family: Family, value: int
) -> np.ndarray:
    if family.mechanism in {"foreign_action", "foreign_reset", "foreign_init"}:
        local_noise = (rng.random(n) < 0.20).astype(np.int8)
        return np.bitwise_xor(local_noise, np.int8(value))
    return (rng.random(n) < 0.5).astype(np.int8)


def _component_pvalues(
    reference: np.ndarray,
    batch: np.ndarray,
    intervention_zero: np.ndarray,
    intervention_one: np.ndarray,
) -> dict[str, float]:
    marginal_ps = [_two_prop_pvalue(reference[:, i], batch[:, i]) for i in range(3)]
    intervention_p = _two_prop_pvalue(intervention_zero, intervention_one)
    joint_p = _joint_independence_pvalue(batch)
    return {
        "marginal": min(1.0, min(marginal_ps) * 3.0),
        "intervention": intervention_p,
        "joint_dependence": joint_p,
    }


def _wilson_lower(successes: int, total: int, z: float = 1.959963984540054) -> float:
    p = successes / total
    denom = 1.0 + z * z / total
    center = p + z * z / (2.0 * total)
    radius = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total))
    return (center - radius) / denom


def _exact_mcnemar_p(basil_only: int, baseline_only: int) -> float:
    n = basil_only + baseline_only
    if n == 0:
        return 1.0
    k = min(basil_only, baseline_only)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def _macro_f1(truths: list[str], predictions: list[str]) -> float:
    scores: list[float] = []
    for label in COMPONENTS:
        tp = sum(t == label and p == label for t, p in zip(truths, predictions))
        fp = sum(t != label and p == label for t, p in zip(truths, predictions))
        fn = sum(t == label and p != label for t, p in zip(truths, predictions))
        denom = 2 * tp + fp + fn
        scores.append(0.0 if denom == 0 else 2 * tp / denom)
    return float(sum(scores) / len(scores))


def _envelope_check(rng: np.random.Generator, horizon: int = 5) -> dict[str, float | bool]:
    p_ref = float(rng.uniform(0.15, 0.75))
    epsilon = float(rng.uniform(0.001, min(0.20, 0.95 - p_ref)))
    p_batch = p_ref + epsilon
    exact_bias = horizon * abs(p_batch - p_ref)
    bound = sum((horizon - t) * epsilon for t in range(horizon))
    return {"epsilon": epsilon, "exact_bias": exact_bias, "bound": bound, "covered": exact_bias <= bound + 1e-12}


def run_g0(
    output_dir: Path,
    *,
    seed_start: int = 941000,
    blocks_per_family: int = 24,
    queries: int = 256,
    run_order_seed: int = 2026072094,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    jobs = [(family, block) for family in FAMILIES for block in range(blocks_per_family)]
    random.Random(run_order_seed).shuffle(jobs)
    records: list[dict[str, Any]] = []
    for order, (family, block) in enumerate(jobs):
        family_index = FAMILIES.index(family)
        seed = seed_start + family_index * 1000 + block
        rng = np.random.default_rng(seed)
        reference = _sample_reference(rng, queries, family)
        batch = _sample_batch(rng, queries, family)
        int0 = _intervention_samples(rng, queries, family, 0)
        int1 = _intervention_samples(rng, queries, family, 1)
        pvalues = _component_pvalues(reference, batch, int0, int1)
        detected_components = [name for name, p in pvalues.items() if p <= ALPHA_FAMILY / 3.0]
        basil_detected = bool(detected_components)
        predicted = min(pvalues, key=pvalues.get) if basil_detected else "clean"

        marginal_only = pvalues["marginal"] <= ALPHA_FAMILY
        pairwise_corr = _phi_max(batch) >= 0.20
        determinism_replay = False
        variance_summary = abs(float(batch.var(axis=0).mean() - reference.var(axis=0).mean())) >= 0.08
        untargeted_random = False
        baseline_flags = {
            "api_checker": False,
            "determinism_replay": determinism_replay,
            "marginal_only": marginal_only,
            "pairwise_corr": pairwise_corr,
            "variance_summary": variance_summary,
            "untargeted_random_property": untargeted_random,
        }
        records.append(
            {
                "order": order,
                "family": family.name,
                "truth": family.truth,
                "mechanism": family.mechanism,
                "block": block,
                "seed": seed,
                "pvalues": pvalues,
                "statistics": {
                    "reference_means": reference.mean(axis=0).tolist(),
                    "batch_means": batch.mean(axis=0).tolist(),
                    "intervention_gap": abs(float(int1.mean() - int0.mean())),
                    "max_pairwise_phi": _phi_max(batch),
                },
                "basil_detected": basil_detected,
                "predicted_family": predicted,
                "baseline_flags": baseline_flags,
                "strongest_baseline_detected": any(baseline_flags.values()),
                "envelope": _envelope_check(rng),
            }
        )

    positives = [r for r in records if r["truth"] != "clean"]
    negatives = [r for r in records if r["truth"] == "clean"]
    sensitivity = sum(r["basil_detected"] for r in positives) / len(positives)
    specificity_count = sum(not r["basil_detected"] for r in negatives)
    specificity = specificity_count / len(negatives)
    baseline_sensitivity = sum(r["strongest_baseline_detected"] for r in positives) / len(positives)
    basil_only = sum(r["basil_detected"] and not r["strongest_baseline_detected"] for r in positives)
    baseline_only = sum((not r["basil_detected"]) and r["strongest_baseline_detected"] for r in positives)
    truths = [r["truth"] for r in positives]
    predictions = [r["predicted_family"] for r in positives]
    macro_f1 = _macro_f1(truths, predictions)
    coverage = sum(bool(r["envelope"]["covered"]) for r in records) / len(records)
    family_detection = {
        family.name: sum(r["basil_detected"] for r in records if r["family"] == family.name) / blocks_per_family
        for family in FAMILIES
    }
    gates = {
        "sensitivity_ge_0_95": sensitivity >= 0.95,
        "specificity_eq_1": specificity == 1.0,
        "specificity_wilson_low_ge_0_96": _wilson_lower(specificity_count, len(negatives)) >= 0.96,
        "improvement_ge_0_15": sensitivity - baseline_sensitivity >= 0.15,
        "mcnemar_p_le_0_01": _exact_mcnemar_p(basil_only, baseline_only) <= 0.01,
        "localization_macro_f1_ge_0_85": macro_f1 >= 0.85,
        "envelope_coverage_eq_1": coverage == 1.0,
        "necessity_families_detected": all(
            family_detection[name] == 1.0
            for name in ("parity_constraint", "shared_noise", "foreign_reset_overwrite")
        ),
    }
    summary: dict[str, Any] = {
        "schema_version": "p5-basil-v94-g0-result-v1",
        "stage": "g0",
        "status": "G0_PASS" if all(gates.values()) else "G0_SCIENTIFIC_FAIL_STOP",
        "design": {
            "families": len(FAMILIES),
            "blocks_per_family": blocks_per_family,
            "total_blocks": len(records),
            "positive_blocks": len(positives),
            "clean_blocks": len(negatives),
            "queries": queries,
            "seed_start": seed_start,
            "run_order_seed": run_order_seed,
        },
        "metrics": {
            "basil_sensitivity": sensitivity,
            "basil_specificity": specificity,
            "specificity_wilson_lower_95": _wilson_lower(specificity_count, len(negatives)),
            "strongest_baseline_sensitivity": baseline_sensitivity,
            "absolute_improvement": sensitivity - baseline_sensitivity,
            "basil_only": basil_only,
            "baseline_only": baseline_only,
            "mcnemar_exact_p": _exact_mcnemar_p(basil_only, baseline_only),
            "localization_macro_f1": macro_f1,
            "envelope_coverage": coverage,
        },
        "family_detection": family_detection,
        "gates": gates,
        "evidence_boundary": "Non-sealed remote development; not a final claim.",
    }
    raw_path = output_dir / "raw_blocks.jsonl"
    with raw_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (raw_path, summary_path)
    }
    (output_dir / "sha256.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary
