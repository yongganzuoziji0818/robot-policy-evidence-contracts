from __future__ import annotations

from agc_fence.experiment import evaluate_method, make_block


def test_conformant_block_is_not_flagged() -> None:
    block = make_block("g0", "local_conformant", 1)
    result = evaluate_method(block, "fence_joint_active", endpoint_queries=2048)
    assert not result.detected
    assert result.status == "PASS_OBSERVED"


def test_direct_channel_is_found_and_localized() -> None:
    block = make_block("g0", "direct_hidden_bit", 2)
    result = evaluate_method(block, "fence_joint_active", endpoint_queries=2048)
    assert result.detected
    assert result.predicted_channels == ("channel_a",)


def test_joint_search_is_needed_for_composite_channel() -> None:
    block = make_block("g0", "xor", 3)
    full = evaluate_method(block, "fence_joint_active", endpoint_queries=2048)
    marginal = evaluate_method(block, "marginal_ablation", endpoint_queries=2048)
    assert full.detected
    assert full.predicted_channels == ("channel_a", "channel_b")
    assert not marginal.detected


def test_support_gap_is_fail_closed() -> None:
    block = make_block("g0", "support_hole", 4)
    result = evaluate_method(block, "fence_joint_active", endpoint_queries=256)
    assert result.status == "UNTESTABLE_SUPPORT"


def test_unreachable_fork_is_rejected() -> None:
    block = make_block("g0", "unreachable_fork", 5)
    result = evaluate_method(block, "fence_joint_active", endpoint_queries=256)
    assert result.status == "INVALID_FORK"
    assert result.invalid_forks_accepted == 0


def test_g1_has_reachable_observation_equivalent_scene_witness() -> None:
    first = make_block("g1", "ugv_hidden_terrain_mask", 930000)
    second = make_block("g1", "ugv_hidden_terrain_mask", 930001)
    assert first.witness_valid
    assert first.reachable_witness_steps > 0
    assert first.scene_digest != second.scene_digest
    assert first.observation_digest != "finite-state"
