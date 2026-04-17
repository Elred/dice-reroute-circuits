"""
Test task 5.2: MC conditional per-trial logic for add_dice and add_set_die.

Validates Requirements 7.1, 7.2, 7.3, 7.4.
"""
import sys
sys.path.insert(0, '.')

import numpy as np

from drc_stat_engine.stats.dice_monte_carlo import (
    combine_dice as mc_combine_dice,
    add_dice_to_roll as mc_add_dice_to_roll,
    add_set_die_to_roll as mc_add_set_die_to_roll,
    conditional_add_dice_mc,
    conditional_add_set_die_mc,
    _evaluate_face_condition_per_trial,
    _build_profile_arrays,
    SENTINEL,
)
from drc_stat_engine.stats.dice_maths_combinatories import (
    combine_dice as comb_combine_dice,
    add_set_die_to_roll as comb_add_set_die_to_roll,
    add_dice_to_roll as comb_add_dice_to_roll,
    conditional_add_partition,
)

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"PASS: {name}")
        passed += 1
    else:
        print(f"FAIL: {name} — {detail}")
        failed += 1


# ============================================================================
# Test 1: _evaluate_face_condition_per_trial correctly identifies matching trials
# ============================================================================
try:
    # Roll 1 red + 1 blue die. R_acc appears on ~12.5% of red die trials.
    roll_df = mc_combine_dice(1, 1, 0, "ship", sample_count=10000, seed=42)
    state = roll_df.attrs["_mc_state"]
    matrix = state["matrix"]
    profiles = state["profiles"]

    mask = _evaluate_face_condition_per_trial(matrix, profiles, "R_acc")
    # R_acc has proba 0.125, so ~12.5% of trials should match
    match_frac = mask.sum() / len(mask)
    check("7.1 — face condition evaluation identifies matching trials",
          0.08 < match_frac < 0.18,
          f"expected ~12.5%, got {match_frac*100:.1f}%")
except Exception as e:
    check("7.1 — face condition evaluation", False, str(e))

# ============================================================================
# Test 2: _evaluate_face_condition_per_trial returns False for absent face
# ============================================================================
try:
    # Roll only blue dice — no R_acc possible
    roll_df_blue = mc_combine_dice(0, 2, 0, "ship", sample_count=5000, seed=7)
    state_b = roll_df_blue.attrs["_mc_state"]
    mask_b = _evaluate_face_condition_per_trial(state_b["matrix"], state_b["profiles"], "R_acc")
    check("7.1 — no matches when face not in pool",
          mask_b.sum() == 0,
          f"expected 0 matches, got {mask_b.sum()}")
except Exception as e:
    check("7.1 — no matches for absent face", False, str(e))

# ============================================================================
# Test 3: conditional_add_set_die_mc — matching trials get the die
# ============================================================================
try:
    roll_df = mc_combine_dice(1, 1, 0, "ship", sample_count=10000, seed=42)
    result_df = conditional_add_set_die_mc(roll_df, "R_acc", "B_hit+crit", "ship")

    # Check that _mc_state is preserved
    state = result_df.attrs["_mc_state"]
    check("7.2/7.4 — _mc_state preserved after conditional add_set_die",
          all(k in state for k in ("matrix", "profiles", "N", "rng")))

    # Matrix should have one more column
    orig_D = roll_df.attrs["_mc_state"]["matrix"].shape[1]
    new_D = state["matrix"].shape[1]
    check("7.4 — matrix has extra column",
          new_D == orig_D + 1,
          f"expected {orig_D + 1}, got {new_D}")

    # Non-matching trials should have SENTINEL in the new column
    new_col = state["matrix"][:, -1]
    orig_mask = _evaluate_face_condition_per_trial(
        roll_df.attrs["_mc_state"]["matrix"],
        roll_df.attrs["_mc_state"]["profiles"],
        "R_acc"
    )
    sentinel_count = (new_col == SENTINEL).sum()
    non_match_count = (~orig_mask).sum()
    check("7.3 — non-matching trials have sentinel",
          sentinel_count == non_match_count,
          f"sentinel_count={sentinel_count}, non_match_count={non_match_count}")

    # Matching trials should have the correct face index (not sentinel)
    match_vals = new_col[orig_mask]
    check("7.2 — matching trials have valid face index (not sentinel)",
          np.all(match_vals != SENTINEL),
          f"found {(match_vals == SENTINEL).sum()} sentinels in matching trials")
except Exception as e:
    check("7.2/7.3/7.4 — conditional_add_set_die_mc", False, str(e))

# ============================================================================
# Test 4: conditional_add_dice_mc — matching trials get the die
# ============================================================================
try:
    roll_df = mc_combine_dice(1, 1, 0, "ship", sample_count=10000, seed=42)
    result_df = conditional_add_dice_mc(roll_df, "R_acc", red=0, blue=0, black=1, type_str="ship")

    state = result_df.attrs["_mc_state"]
    new_col = state["matrix"][:, -1]
    orig_mask = _evaluate_face_condition_per_trial(
        roll_df.attrs["_mc_state"]["matrix"],
        roll_df.attrs["_mc_state"]["profiles"],
        "R_acc"
    )

    # Non-matching trials should have sentinel
    check("7.3 — conditional add_dice: non-matching have sentinel",
          np.all(new_col[~orig_mask] == SENTINEL),
          f"found {(new_col[~orig_mask] != SENTINEL).sum()} non-sentinel in non-matching")

    # Matching trials should have valid face indices (0..n_faces-1)
    match_vals = new_col[orig_mask]
    check("7.2 — conditional add_dice: matching have valid face index",
          np.all(match_vals >= 0),
          f"found {(match_vals < 0).sum()} invalid indices in matching trials")
except Exception as e:
    check("7.2/7.3 — conditional_add_dice_mc", False, str(e))

# ============================================================================
# Test 5: Probabilities sum to ~1.0 after conditional add
# ============================================================================
try:
    proba_sum = result_df["proba"].sum()
    check("7.4 — probabilities sum to ~1.0 after conditional add_dice",
          abs(proba_sum - 1.0) < 1e-9,
          f"sum = {proba_sum}")
except Exception as e:
    check("7.4 — probability sum", False, str(e))

try:
    roll_df2 = mc_combine_dice(1, 1, 0, "ship", sample_count=10000, seed=42)
    result_df2 = conditional_add_set_die_mc(roll_df2, "R_acc", "B_hit+crit", "ship")
    proba_sum2 = result_df2["proba"].sum()
    check("7.4 — probabilities sum to ~1.0 after conditional add_set_die",
          abs(proba_sum2 - 1.0) < 1e-9,
          f"sum = {proba_sum2}")
except Exception as e:
    check("7.4 — probability sum (set die)", False, str(e))

# ============================================================================
# Test 6: Value strings are correct — matching trials include the added face
# ============================================================================
try:
    # Use a face condition that's always true (e.g. U_hit on blue die, 50% chance)
    roll_df3 = mc_combine_dice(0, 1, 0, "ship", sample_count=5000, seed=99)
    result_df3 = conditional_add_set_die_mc(roll_df3, "U_hit", "R_hit", "ship")

    # Some value strings should contain R_hit (those where U_hit was present)
    has_r_hit = result_df3["value"].apply(lambda v: "R_hit" in v.split(" "))
    # Some should NOT contain R_hit (those where U_hit was absent)
    no_r_hit = ~has_r_hit
    check("7.2/7.3 — some outcomes have added face, some don't",
          has_r_hit.any() and no_r_hit.any(),
          f"has_r_hit={has_r_hit.sum()}, no_r_hit={no_r_hit.sum()}")
except Exception as e:
    check("7.2/7.3 — value string correctness", False, str(e))

# ============================================================================
# Test 7: When no trials match, result is unchanged
# ============================================================================
try:
    # Roll only blue dice, condition on R_acc (never present)
    roll_df4 = mc_combine_dice(0, 2, 0, "ship", sample_count=3000, seed=11)
    result_df4 = conditional_add_set_die_mc(roll_df4, "R_acc", "B_hit", "ship")

    # No value string should contain B_hit since no trial matched
    has_b_hit = any("B_hit" in v.split(" ") for v in result_df4["value"])
    check("7.3 — no trials match: no added face in any outcome",
          not has_b_hit,
          "found B_hit in outcomes despite no matching trials")

    proba_sum4 = result_df4["proba"].sum()
    check("7.3 — no trials match: probabilities still sum to ~1.0",
          abs(proba_sum4 - 1.0) < 1e-9,
          f"sum = {proba_sum4}")
except Exception as e:
    check("7.3 — no matching trials", False, str(e))

# ============================================================================
# Test 8: MC conditional add agrees with combinatorial conditional add
# ============================================================================
try:
    # Small pool: 1 red + 1 blue, condition on R_acc, add B_hit+crit (set die)
    N_mc = 100_000
    mc_roll = mc_combine_dice(1, 1, 0, "ship", sample_count=N_mc, seed=123)
    mc_result = conditional_add_set_die_mc(mc_roll, "R_acc", "B_hit+crit", "ship")
    mc_avg_dmg = (mc_result["damage"] * mc_result["proba"]).sum()

    comb_roll = comb_combine_dice(1, 1, 0, "ship")
    comb_result = conditional_add_partition(
        comb_roll, "R_acc", comb_add_set_die_to_roll,
        target_result="B_hit+crit", type_str="ship"
    )
    comb_avg_dmg = (comb_result["damage"] * comb_result["proba"]).sum()

    check("7.1-7.4 — MC conditional add_set_die avg damage agrees with combinatorial",
          abs(mc_avg_dmg - comb_avg_dmg) < 0.1,
          f"MC={mc_avg_dmg:.4f}, comb={comb_avg_dmg:.4f}")
except Exception as e:
    check("7.1-7.4 — MC/comb agreement (set die)", False, str(e))

# ============================================================================
# Test 9: MC conditional add_dice agrees with combinatorial
# ============================================================================
try:
    mc_roll2 = mc_combine_dice(1, 1, 0, "ship", sample_count=N_mc, seed=456)
    mc_result2 = conditional_add_dice_mc(mc_roll2, "R_acc", red=0, blue=0, black=1, type_str="ship")
    mc_avg_dmg2 = (mc_result2["damage"] * mc_result2["proba"]).sum()

    comb_roll2 = comb_combine_dice(1, 1, 0, "ship")
    comb_result2 = conditional_add_partition(
        comb_roll2, "R_acc", comb_add_dice_to_roll,
        red=0, blue=0, black=1, type_str="ship"
    )
    comb_avg_dmg2 = (comb_result2["damage"] * comb_result2["proba"]).sum()

    check("7.1-7.4 — MC conditional add_dice avg damage agrees with combinatorial",
          abs(mc_avg_dmg2 - comb_avg_dmg2) < 0.1,
          f"MC={mc_avg_dmg2:.4f}, comb={comb_avg_dmg2:.4f}")
except Exception as e:
    check("7.1-7.4 — MC/comb agreement (add dice)", False, str(e))

# ============================================================================
# Test 10: Works with squad type
# ============================================================================
try:
    mc_roll_sq = mc_combine_dice(1, 0, 1, "squad", sample_count=10000, seed=77)
    result_sq = conditional_add_set_die_mc(mc_roll_sq, "R_hit", "U_hit", "squad")
    proba_sq = result_sq["proba"].sum()
    check("7.4 — squad type: probabilities sum to ~1.0",
          abs(proba_sq - 1.0) < 1e-9,
          f"sum = {proba_sq}")
except Exception as e:
    check("squad type conditional add", False, str(e))

# ============================================================================
# Test 11: conditional_add_dice_mc with zero dice returns unchanged
# ============================================================================
try:
    roll_df5 = mc_combine_dice(1, 0, 0, "ship", sample_count=3000, seed=55)
    result_df5 = conditional_add_dice_mc(roll_df5, "R_hit", red=0, blue=0, black=0, type_str="ship")
    check("7.2 — zero dice: returns unchanged",
          result_df5 is roll_df5,
          "expected same object returned")
except Exception as e:
    check("7.2 — zero dice", False, str(e))

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed")
if failed > 0:
    print("SOME TESTS FAILED")
else:
    print("ALL TESTS PASSED")
