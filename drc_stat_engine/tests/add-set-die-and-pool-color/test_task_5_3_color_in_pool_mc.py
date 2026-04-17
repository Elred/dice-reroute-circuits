"""
Test color_in_pool_add_mc — MC backend per-trial color selection.

Validates Requirements 11.1, 11.2, 11.3:
- Determines selected color per trial from Roll_State_Tokens
- Samples a new die of the selected color per trial
- Appends new die column(s) to sample matrix
"""
import sys
sys.path.insert(0, ".")

import numpy as np

from drc_stat_engine.stats.dice_monte_carlo import (
    combine_dice as mc_combine,
    color_in_pool_add_mc,
    SENTINEL,
)


def test_basic_color_in_pool_mc():
    """color_in_pool_add_mc adds 3 new columns and probabilities sum to ~1."""
    roll_df = mc_combine(1, 1, 0, "ship", sample_count=5000, seed=42)
    state_before = roll_df.attrs["_mc_state"]
    D_before = state_before["matrix"].shape[1]

    result = color_in_pool_add_mc(roll_df, ["red", "blue", "black"], type_str="ship")

    state_after = result.attrs["_mc_state"]
    D_after = state_after["matrix"].shape[1]

    # Should have 3 new columns (one per color)
    assert D_after == D_before + 3, f"FAIL: expected {D_before + 3} columns, got {D_after}"
    print(f"PASS: matrix grew from {D_before} to {D_after} columns (+3)")

    # Probabilities should sum to ~1
    proba_sum = result["proba"].sum()
    assert abs(proba_sum - 1.0) < 1e-6, f"FAIL: proba sum = {proba_sum}"
    print(f"PASS: proba sum = {proba_sum:.6f}")

    # _mc_state should be preserved
    assert "_mc_state" in result.attrs, "FAIL: _mc_state missing"
    assert result.attrs["_mc_state"]["N"] == 5000
    print("PASS: _mc_state preserved")


def test_sentinel_usage():
    """For each trial, exactly 1 of the 3 new columns should be non-sentinel."""
    roll_df = mc_combine(1, 1, 1, "ship", sample_count=2000, seed=123)
    result = color_in_pool_add_mc(roll_df, ["black", "red", "blue"], type_str="ship")

    state = result.attrs["_mc_state"]
    matrix = state["matrix"]
    N = state["N"]
    D_orig = 3  # 1R + 1U + 1B

    # Last 3 columns are the new color columns
    new_cols = matrix[:, D_orig:]
    assert new_cols.shape == (N, 3), f"FAIL: new cols shape = {new_cols.shape}"

    # Each trial should have exactly 1 non-sentinel in the new columns
    active_per_trial = np.sum(new_cols != SENTINEL, axis=1)
    assert np.all(active_per_trial == 1), (
        f"FAIL: some trials have != 1 active new column. "
        f"min={active_per_trial.min()}, max={active_per_trial.max()}"
    )
    print("PASS: exactly 1 active new column per trial")


def test_color_priority_respected():
    """With only red dice in pool, color_in_pool should always select red (first match)."""
    roll_df = mc_combine(2, 0, 0, "ship", sample_count=1000, seed=99)
    # Priority: red first — all trials have red tokens, so red should always be selected
    result = color_in_pool_add_mc(roll_df, ["red", "blue", "black"], type_str="ship")

    state = result.attrs["_mc_state"]
    matrix = state["matrix"]
    D_orig = 2  # 2 red dice

    new_cols = matrix[:, D_orig:]  # 3 new columns: red(0), blue(1), black(2)
    # Red column (index 0) should be active for all trials
    red_active = new_cols[:, 0] != SENTINEL
    blue_active = new_cols[:, 1] != SENTINEL
    black_active = new_cols[:, 2] != SENTINEL

    assert np.all(red_active), "FAIL: not all trials selected red"
    assert not np.any(blue_active), "FAIL: some trials selected blue"
    assert not np.any(black_active), "FAIL: some trials selected black"
    print("PASS: all trials selected red when only red dice in pool")


def test_mixed_pool_priority():
    """With red+blue pool and priority [blue, red, black], blue should be selected."""
    roll_df = mc_combine(1, 1, 0, "ship", sample_count=1000, seed=77)
    result = color_in_pool_add_mc(roll_df, ["blue", "red", "black"], type_str="ship")

    state = result.attrs["_mc_state"]
    matrix = state["matrix"]
    D_orig = 2

    new_cols = matrix[:, D_orig:]
    # Blue is first priority and present in all trials → blue column (index 1) active
    blue_active = new_cols[:, 1] != SENTINEL
    assert np.all(blue_active), "FAIL: not all trials selected blue"
    print("PASS: all trials selected blue with [blue, red, black] priority on R+U pool")


def test_value_strings_extended():
    """After color_in_pool_add_mc, value strings should have more tokens than before."""
    roll_df = mc_combine(1, 0, 1, "ship", sample_count=500, seed=55)
    before_tokens = roll_df["value"].apply(lambda v: len(v.split(" ")))

    result = color_in_pool_add_mc(roll_df, ["red", "blue", "black"], type_str="ship")
    after_tokens = result["value"].apply(lambda v: len(v.split(" ")))

    # Every outcome should have at least 1 more token than the minimum before
    assert after_tokens.min() >= before_tokens.min() + 1, (
        f"FAIL: min tokens before={before_tokens.min()}, after={after_tokens.min()}"
    )
    print(f"PASS: value strings extended (min tokens: {before_tokens.min()} -> {after_tokens.min()})")


def test_squad_type():
    """color_in_pool_add_mc works with squad type."""
    roll_df = mc_combine(1, 1, 0, "squad", sample_count=500, seed=33)
    result = color_in_pool_add_mc(roll_df, ["red", "blue", "black"], type_str="squad")

    proba_sum = result["proba"].sum()
    assert abs(proba_sum - 1.0) < 1e-6, f"FAIL: proba sum = {proba_sum}"
    print(f"PASS: squad type works, proba sum = {proba_sum:.6f}")


if __name__ == "__main__":
    tests = [
        test_basic_color_in_pool_mc,
        test_sentinel_usage,
        test_color_priority_respected,
        test_mixed_pool_priority,
        test_value_strings_extended,
        test_squad_type,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"FAIL [{t.__name__}]: {e}")
    print("\nAll tests completed.")
