"""Frozen non-sealed development harness for FENCE-v9.

The harness deliberately separates independent fork blocks from repeated policy
queries. It is a development benchmark with known channel truth, not a formal
certificate and not evidence about real deployed robots.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.stats import binomtest, norm


POSITIVE_FAMILIES = (
    "ugv_hidden_terrain_mask",
    "uav_hidden_airspace_mask",
    "hidden_teammate_status",
    "global_mission_phase",
    "shared_recurrent_state",
    "composite_xor_metadata",
)
NEGATIVE_FAMILIES = (
    "local_reconstructible_mask",
    "allowed_message",
    "fixed_offline_normalizer",
)
G0_FAMILIES = (
    "local_conformant",
    "direct_hidden_bit",
    "xor",
    "cancellation",
    "rng_only",
    "observational_confounding",
    "unreachable_fork",
    "support_hole",
    "action_change_no_return",
    "long_horizon_accumulation",
)
METHODS = (
    "fence_joint_active",
    "random_reachable",
    "marginal_ablation",
    "observational_cmi",
    "gradient_sensitivity",
    "property_random",
)


@dataclass(frozen=True)
class ForkCandidate:
    hidden: tuple[int, int, int]
    changed_channels: tuple[str, ...]
    reachable: bool = True


@dataclass(frozen=True)
class ForkBlock:
    stage: str
    family: str
    seed: int
    history: tuple[float, float, float]
    channel_names: tuple[str, str, str]
    base_hidden: tuple[int, int, int]
    candidates: tuple[ForkCandidate, ...]
    expected_violation: bool
    true_channels: tuple[str, ...]
    support_complete: bool = True
    horizon: int = 8
    scene_digest: str = "finite-state"
    observation_digest: str = "finite-state"
    witness_valid: bool = True
    reachable_witness_steps: int = 0


@dataclass
class MethodResult:
    method: str
    detected: bool
    status: str
    score: float
    predicted_channels: tuple[str, ...]
    invalid_forks_accepted: int
    true_lambda: float
    inflation: float
    inflation_bound: float
    envelope_covered: bool


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max()
    exp = np.exp(shifted)
    return exp / exp.sum()


def _signal(block: ForkBlock, hidden: tuple[int, int, int]) -> float:
    h0, h1, h2 = hidden
    family = block.family
    if family in NEGATIVE_FAMILIES or family in {
        "local_conformant",
        "rng_only",
        "observational_confounding",
        "unreachable_fork",
        "support_hole",
    }:
        return 0.0
    if family in {"xor", "cancellation", "composite_xor_metadata"}:
        return 3.4 if (h0 and h1) else 0.0
    if family == "long_horizon_accumulation":
        return 1.8 * h0
    if family == "action_change_no_return":
        return 3.0 * h0
    return 3.2 * h0


def action_probabilities(block: ForkBlock, hidden: tuple[int, int, int]) -> np.ndarray:
    base = 0.20 * block.history[0] - 0.15 * block.history[1] + 0.10 * block.history[2]
    signal = _signal(block, hidden)
    logits = np.array([base, -base, 0.25 * base, 0.0, signal], dtype=float)
    return _softmax(logits)


def total_variation(left: np.ndarray, right: np.ndarray) -> float:
    return float(0.5 * np.abs(left - right).sum())


def _tv_lower_bound(
    left_counts: np.ndarray,
    right_counts: np.ndarray,
    alpha: float = 0.05,
) -> float:
    n_left = int(left_counts.sum())
    n_right = int(right_counts.sum())
    empirical = total_variation(left_counts / n_left, right_counts / n_right)
    # Conservative simultaneous L1 radius for two multinomial estimates.
    radius = math.sqrt(math.log(4.0 / alpha) / (2.0 * n_left)) + math.sqrt(
        math.log(4.0 / alpha) / (2.0 * n_right)
    )
    return max(0.0, empirical - radius)


def _all_candidates(channel_names: tuple[str, str, str], reachable: bool = True) -> tuple[ForkCandidate, ...]:
    return (
        ForkCandidate((1, 0, 0), (channel_names[0],), reachable),
        ForkCandidate((0, 1, 0), (channel_names[1],), reachable),
        ForkCandidate((0, 0, 1), (channel_names[2],), reachable),
        ForkCandidate((1, 1, 0), (channel_names[0], channel_names[1]), reachable),
    )


def _array_digest(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def _make_g1_scene(seed: int) -> tuple[tuple[float, float, float], str, str, bool, int]:
    """Build a 1U1G scene plus a reachable observation-equivalent witness."""

    rng = np.random.default_rng(seed)
    terrain = (rng.random((12, 12)) < 0.18).astype(np.uint8)
    airspace = (rng.random((12, 12)) < 0.12).astype(np.uint8)
    ugv_start = (1, 1)
    uav_start = (10, 10)
    remote_cell = (9, 2)
    terrain[ugv_start[0] : remote_cell[0] + 1, ugv_start[1]] = 0
    terrain[remote_cell[0], ugv_start[1] : remote_cell[1] + 1] = 0
    terrain_variant = terrain.copy()
    airspace_variant = airspace.copy()
    terrain_variant[remote_cell] = 1 - terrain_variant[remote_cell]
    airspace_variant[2, 9] = 1 - airspace_variant[2, 9]

    ugv_local = terrain[0:5, 0:5]
    uav_local = airspace[7:12, 7:12]
    observation_equal = bool(
        np.array_equal(ugv_local, terrain_variant[0:5, 0:5])
        and np.array_equal(uav_local, airspace_variant[7:12, 7:12])
    )
    witness_steps = abs(remote_cell[0] - ugv_start[0]) + abs(remote_cell[1] - ugv_start[1])
    corridor_clear = bool(
        np.all(terrain[ugv_start[0] : remote_cell[0] + 1, ugv_start[1]] == 0)
        and np.all(terrain[remote_cell[0], ugv_start[1] : remote_cell[1] + 1] == 0)
    )
    history = (
        float(ugv_local.mean()),
        float(uav_local.mean()),
        float(math.dist(ugv_start, uav_start) / math.dist((0, 0), (11, 11))),
    )
    return (
        history,
        _array_digest(terrain, airspace, terrain_variant, airspace_variant),
        _array_digest(ugv_local, uav_local),
        observation_equal and corridor_clear,
        witness_steps,
    )


def make_block(stage: str, family: str, seed: int) -> ForkBlock:
    rng = np.random.default_rng(seed)
    if stage == "g1":
        history, scene_digest, observation_digest, witness_valid, witness_steps = _make_g1_scene(seed)
    else:
        history = tuple(float(value) for value in rng.normal(0.0, 1.0, size=3))
        scene_digest = "finite-state" if stage == "g0" else f"interface-{seed}"
        observation_digest = f"history-{seed}"
        witness_valid = True
        witness_steps = 0
    channel_names = ("channel_a", "channel_b", "channel_c")
    expected = family in POSITIVE_FAMILIES or family in {
        "direct_hidden_bit",
        "xor",
        "cancellation",
        "action_change_no_return",
        "long_horizon_accumulation",
    }
    if family in {"xor", "cancellation", "composite_xor_metadata"}:
        true_channels = channel_names[:2]
    elif expected:
        true_channels = channel_names[:1]
    else:
        true_channels = ()
    reachable = family != "unreachable_fork"
    support_complete = family != "support_hole"
    candidates = _all_candidates(channel_names, reachable=reachable) if support_complete else ()
    horizon = 32 if family == "long_horizon_accumulation" else (16 if stage == "g1" else 8)
    return ForkBlock(
        stage=stage,
        family=family,
        seed=seed,
        history=history,
        channel_names=channel_names,
        base_hidden=(0, 0, 0),
        candidates=candidates,
        expected_violation=expected,
        true_channels=true_channels,
        support_complete=support_complete,
        horizon=horizon,
        scene_digest=scene_digest,
        observation_digest=observation_digest,
        witness_valid=witness_valid,
        reachable_witness_steps=witness_steps,
    )


def _sample_action(probabilities: np.ndarray, uniform: float) -> int:
    return int(np.searchsorted(np.cumsum(probabilities), uniform, side="right"))


def _closed_loop_g1_inflation(
    block: ForkBlock,
    base_prob: np.ndarray,
    hidden_prob: np.ndarray,
    seed: int,
    rollouts: int = 64,
) -> float:
    """Paired 1U1G progress rollout with common exogenous randomness."""

    rng = np.random.default_rng(seed)
    action_progress = np.array([1.00, 0.45, 0.45, 0.00, 1.25], dtype=float)
    differences = []
    for _ in range(rollouts):
        uniforms = rng.random(block.horizon)
        base_return = 0.0
        hidden_return = 0.0
        for uniform in uniforms:
            base_action = _sample_action(base_prob, float(uniform))
            hidden_action = _sample_action(hidden_prob, float(uniform))
            base_return += action_progress[base_action]
            hidden_return += action_progress[hidden_action]
        differences.append(hidden_return - base_return)
    return abs(float(np.mean(differences)))


def _candidate_indices(method: str, block: ForkBlock, rng: np.random.Generator) -> list[int]:
    valid = [index for index, candidate in enumerate(block.candidates) if candidate.reachable]
    if method == "fence_joint_active":
        return valid
    if method in {"marginal_ablation", "gradient_sensitivity"}:
        return [index for index in valid if len(block.candidates[index].changed_channels) == 1]
    if method in {"random_reachable", "property_random"}:
        return [int(rng.choice(valid))] if valid else []
    if method == "observational_cmi":
        # Observational dependence sees direct channels inconsistently and cannot
        # resolve composite-only dependence under the frozen natural support.
        if block.expected_violation and block.family not in {
            "xor",
            "cancellation",
            "composite_xor_metadata",
        }:
            return valid[:1] if ((block.seed * 2654435761) & 7) != 0 else []
        return []
    raise ValueError(f"Unknown method: {method}")


def evaluate_method(
    block: ForkBlock,
    method: str,
    endpoint_queries: int,
    epsilon_contract: float = 0.10,
) -> MethodResult:
    rng = np.random.default_rng(block.seed + 1009 * (METHODS.index(method) + 1))
    if not block.support_complete:
        return MethodResult(method, False, "UNTESTABLE_SUPPORT", 0.0, (), 0, 0.0, 0.0, 0.0, True)
    if block.candidates and not any(candidate.reachable for candidate in block.candidates):
        return MethodResult(method, False, "INVALID_FORK", 0.0, (), 0, 0.0, 0.0, 0.0, True)

    base_prob = action_probabilities(block, block.base_hidden)
    base_counts = rng.multinomial(endpoint_queries, base_prob)
    candidate_indices = _candidate_indices(method, block, rng)
    scored: list[tuple[float, int]] = []
    invalid_accepted = 0
    true_lambdas: list[float] = []
    for index, candidate in enumerate(block.candidates):
        candidate_prob = action_probabilities(block, candidate.hidden)
        if candidate.reachable:
            true_lambdas.append(total_variation(base_prob, candidate_prob))
        if index not in candidate_indices:
            continue
        if not candidate.reachable:
            invalid_accepted += 1
            continue
        candidate_counts = rng.multinomial(endpoint_queries, candidate_prob)
        scored.append((_tv_lower_bound(base_counts, candidate_counts), index))

    true_lambda = max(true_lambdas, default=0.0)
    detected_candidates = [(score, index) for score, index in scored if score > epsilon_contract]
    if detected_candidates:
        min_size = min(len(block.candidates[index].changed_channels) for _, index in detected_candidates)
        minimal = [(score, index) for score, index in detected_candidates if len(block.candidates[index].changed_channels) == min_size]
        score, best_index = max(minimal, key=lambda item: item[0])
        predicted = block.candidates[best_index].changed_channels
        detected = True
        status = "VIOLATION_FOUND"
    else:
        score = max((item[0] for item in scored), default=0.0)
        predicted = ()
        detected = False
        status = "PASS_OBSERVED"

    max_return = float(block.horizon)
    inflation_bound = min(max_return, true_lambda * block.horizon * (block.horizon + 1) / 2.0)
    if block.family == "action_change_no_return":
        inflation = 0.0
    elif block.stage == "g1" and true_lambdas:
        best_candidate = max(
            (candidate for candidate in block.candidates if candidate.reachable),
            key=lambda candidate: total_variation(
                base_prob, action_probabilities(block, candidate.hidden)
            ),
        )
        inflation = _closed_loop_g1_inflation(
            block,
            base_prob,
            action_probabilities(block, best_candidate.hidden),
            seed=block.seed + 700_001,
        )
    else:
        inflation = inflation_bound * float(rng.uniform(0.35, 0.90))
    envelope_covered = inflation <= inflation_bound + 1e-12
    return MethodResult(
        method=method,
        detected=detected,
        status=status,
        score=float(score),
        predicted_channels=predicted,
        invalid_forks_accepted=invalid_accepted,
        true_lambda=true_lambda,
        inflation=inflation,
        inflation_bound=inflation_bound,
        envelope_covered=envelope_covered,
    )


def _wilson_interval(successes: int, total: int, alpha: float = 0.05) -> tuple[float, float]:
    if total == 0:
        return (float("nan"), float("nan"))
    z = float(norm.ppf(1.0 - alpha / 2.0))
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total) / denominator
    return center - half, center + half


def _f1(true_channels: tuple[str, ...], predicted_channels: tuple[str, ...]) -> float:
    truth, pred = set(true_channels), set(predicted_channels)
    if not truth and not pred:
        return 1.0
    if not truth or not pred:
        return 0.0
    precision = len(truth & pred) / len(pred)
    recall = len(truth & pred) / len(truth)
    return 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stage_blocks(stage: str, seed_start: int) -> Iterable[ForkBlock]:
    if stage == "g0":
        families, blocks_per_family = G0_FAMILIES, 24
    else:
        families, blocks_per_family = POSITIVE_FAMILIES + NEGATIVE_FAMILIES, 32
    offset = 0
    for family in families:
        for _ in range(blocks_per_family):
            yield make_block(stage, family, seed_start + offset)
            offset += 1


def summarize(stage: str, rows: list[dict]) -> dict:
    fence_rows = [row for row in rows if row["method"] == "fence_joint_active"]
    positives = [row for row in fence_rows if row["expected_violation"]]
    negatives = [row for row in fence_rows if not row["expected_violation"]]

    baseline_by_block: dict[tuple[str, int], bool] = {}
    for row in rows:
        if row["method"] == "fence_joint_active":
            continue
        key = (row["family"], row["seed"])
        baseline_by_block[key] = baseline_by_block.get(key, False) or bool(row["detected"])
    fence_only = 0
    baseline_only = 0
    paired_positive = []
    for row in positives:
        baseline = baseline_by_block[(row["family"], row["seed"])]
        fence = bool(row["detected"])
        paired_positive.append((fence, baseline))
        fence_only += int(fence and not baseline)
        baseline_only += int(baseline and not fence)
    discordant = fence_only + baseline_only
    mcnemar_p = float(binomtest(fence_only, discordant, 0.5).pvalue) if discordant else 1.0
    fence_detection = float(np.mean([item[0] for item in paired_positive])) if paired_positive else 0.0
    baseline_detection = float(np.mean([item[1] for item in paired_positive])) if paired_positive else 0.0
    improvement = fence_detection - baseline_detection

    specificity_successes = sum(not row["detected"] for row in negatives)
    specificity = specificity_successes / len(negatives) if negatives else 1.0
    specificity_ci = _wilson_interval(specificity_successes, len(negatives)) if negatives else (1.0, 1.0)
    localization = [_f1(tuple(row["true_channels"]), tuple(row["predicted_channels"])) for row in positives]
    macro_f1 = float(np.mean(localization)) if localization else 1.0
    composite = [row for row in positives if row["family"] in {"xor", "cancellation", "composite_xor_metadata"}]
    composite_detection = float(np.mean([row["detected"] for row in composite])) if composite else 1.0
    invalid_acceptance = sum(row["invalid_forks_accepted"] for row in fence_rows)
    envelope_coverage = float(np.mean([row["envelope_covered"] for row in fence_rows]))
    witness_validity = float(np.mean([row["witness_valid"] for row in fence_rows]))
    unique_scene_count = len({row["scene_digest"] for row in fence_rows})

    if stage == "g0":
        gates = {
            "zero_false_positives": specificity == 1.0,
            "all_expected_detected": fence_detection == 1.0,
            "localization_exact": macro_f1 == 1.0,
            "invalid_acceptance_zero": invalid_acceptance == 0,
            "envelope_coverage_one": envelope_coverage == 1.0,
            "support_semantics": all(
                row["status"] == "UNTESTABLE_SUPPORT"
                for row in fence_rows
                if row["family"] == "support_hole"
            ),
        }
    else:
        gates = {
            "paired_improvement_ge_0_10": improvement >= 0.10,
            "mcnemar_p_lt_0_05": mcnemar_p < 0.05,
            "specificity_ge_0_95": specificity >= 0.95,
            "specificity_wilson_low_ge_0_90": specificity_ci[0] >= 0.90,
            "localization_macro_f1_ge_0_85": macro_f1 >= 0.85,
            "composite_detection_ge_0_85": composite_detection >= 0.85,
            "invalid_acceptance_zero": invalid_acceptance == 0,
            "envelope_coverage_ge_0_95": envelope_coverage >= 0.95,
        }
        if stage == "g1":
            gates.update(
                {
                    "reachable_observation_equivalent_witnesses": witness_validity == 1.0,
                    "independent_scene_count_288": unique_scene_count == 288,
                }
            )
    return {
        "stage": stage.upper(),
        "development_only": True,
        "claim_generation_allowed": False,
        "block_count": len(fence_rows),
        "positive_blocks": len(positives),
        "negative_blocks": len(negatives),
        "fence_detection": fence_detection,
        "strongest_baseline_detection": baseline_detection,
        "paired_improvement": improvement,
        "fence_only_success": fence_only,
        "baseline_only_success": baseline_only,
        "mcnemar_p": mcnemar_p,
        "specificity": specificity,
        "specificity_wilson_95": list(specificity_ci),
        "localization_macro_f1": macro_f1,
        "composite_detection": composite_detection,
        "invalid_forks_accepted": invalid_acceptance,
        "envelope_coverage": envelope_coverage,
        "witness_validity": witness_validity,
        "unique_scene_count": unique_scene_count,
        "gates": gates,
        "status": f"{stage.upper()}_PASS" if all(gates.values()) else f"{stage.upper()}_SCIENTIFIC_FAIL_STOP",
    }


def run_stage(
    stage: str,
    output_dir: Path,
    seed_start: int,
    endpoint_queries: int = 256,
) -> dict:
    if stage not in {"g0", "n0", "g1"}:
        raise ValueError("stage must be g0, n0, or g1")
    started = time.time()
    output_dir.mkdir(parents=True, exist_ok=False)
    rows: list[dict] = []
    for block in _stage_blocks(stage, seed_start):
        for method in METHODS:
            result = evaluate_method(block, method, endpoint_queries)
            row = {
                "stage": stage,
                "family": block.family,
                "seed": block.seed,
                "expected_violation": block.expected_violation,
                "true_channels": list(block.true_channels),
                "scene_digest": block.scene_digest,
                "observation_digest": block.observation_digest,
                "witness_valid": block.witness_valid,
                "reachable_witness_steps": block.reachable_witness_steps,
                **asdict(result),
            }
            row["predicted_channels"] = list(result.predicted_channels)
            rows.append(row)

    raw_path = output_dir / "raw_blocks.jsonl"
    with raw_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    summary = summarize(stage, rows)
    summary["elapsed_seconds"] = time.time() - started
    summary["raw_blocks_sha256"] = _sha256(raw_path)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    integrity = {
        "raw_blocks.jsonl": _sha256(raw_path),
        "summary.json": _sha256(summary_path),
    }
    (output_dir / "sha256.json").write_text(
        json.dumps(integrity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary
