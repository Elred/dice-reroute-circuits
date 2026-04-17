"""
Test task 5.1: MC add_set_die_to_roll implementation.

Validates Requirements 3.1, 3.2, 3.3, 3.4.
"""
import sys
sys.path.insert(0, '.')

import numpy as np

from drc_stat_engine.stats.dice_monte_carlo import (
    combine_dice as mc_combine_dice,
    add_set_die_to_roll as mc_add_set_die_to_roll,
)
from drc_stat_engine.stats.dice_maths_combinatories import (
    combine_dice as comb_combine_dice,
    add_set_die_to_roll as comb_add_set_die_to_roll,
    value_to_dice_attr_dict,
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


# --- Test 1: Basic add_set_die appends column to matrix (Req 3.1) ---
try:
    roll_df = mc_combine_dice(1, 0, 0, "ship", sample_count=5000, seed=42)
    state_before = roll_df.attrs["_mc_state"]
    D_before = state_before["matrix"].shape[1]

    result_df = mc_add_set_die_to_roll(roll_df, "R_hit", "ship")
    state_after = result_df.attrs["_mc_state"]
    D_after = state_after["matrix"].shape[1]

    check("3.1 — new column appended to matrix",
          D_after == D_before + 1,
          f"expected {D_before + 1} columns, got {D_after}")
except Exception as e:
    check("3.1 — new column appended to matrix", False, str(e))

# --- Test 2: Every trial has the same face index in the new column (Req 3.1) ---
try:
    new_col = state_after["matrix"][:, -1]
    unique_vals = np.unique(new_col)
    check("3.1 — all trials have same face index (deterministic)",
          len(unique_vals) == 1,
          f"expected 1 unique value, got {len(unique_vals)}: {unique_vals}")
except Exception as e:
    check("3.1 — all trials have same face index", False, str(e))

# --- Test 3: Profile list extended (Req 3.2) ---
try:
    check("3.2 — profiles list extended by 1",
          len(state_after["profiles"]) == len(state_before["profiles"]) + 1,
          f"expected {len(state_before['profiles']) + 1}, got {len(state_after['profiles'])}")
except Exception as e:
    check("3.2 — profiles list extended", False, str(e))

# --- Test 4: New profile is for the correct color (Req 3.2) ---
try:
    new_profile = state_after["profiles"][-1]
    # R_hit should be in a red die profile
    check("3.2 — new profile contains target face",
          "R_hit" in new_profile["values"],
          f"R_hit not found in new profile values: {new_profile['values']}")
except Exception as e:
    check("3.2 — new profile contains target face", False, str(e))

# --- Test 5: Roll_DataFrame is rebuilt correctly (Req 3.3) ---
try:
    expected_cols = {"value", "proba", "damage", "crit", "acc", "blank"}
    check("3.3 — Roll_DataFrame has correct columns",
          set(result_df.columns) == expected_cols,
          f"got columns: {set(result_df.columns)}")
except Exception as e:
    check("3.3 — Roll_DataFrame columns", False, str(e))

# --- Test 6: Probabilities sum to ~1.0 (Req 3.3) ---
try:
    proba_sum = result_df["proba"].sum()
    check("3.3 — probabilities sum to ~1.0",
          abs(proba_sum - 1.0) < 1e-9,
          f"sum = {proba_sum}")
except Exception as e:
    check("3.3 — probability sum", False, str(e))

# --- Test 7: _mc_state preserved (Req 3.4) ---
try:
    check("3.4 — _mc_state has matrix key", "matrix" in state_after)
    check("3.4 — _mc_state has profiles key", "profiles" in state_after)
    check("3.4 — _mc_state has N key", "N" in state_after)
    check("3.4 — _mc_state has rng key", "rng" in state_after)
    check("3.4 — N is preserved", state_after["N"] == state_before["N"],
          f"expected {state_before['N']}, got {state_after['N']}")
except Exception as e:
    check("3.4 — _mc_state preserved", False, str(e))

# --- Test 8: Every value string contains the target face (Req 3.1) ---
try:
    all_contain = all("R_hit" in v for v in result_df["value"])
    check("3.1 — every value string contains R_hit", all_contain)
except Exception as e:
    check("3.1 — value strings contain target", False, str(e))

# --- Test 9: Stats updated correctly — damage increased by face attrs ---
try:
    # R_hit has damage=1, crit=0, acc=0, blank=0
    attrs = value_to_dice_attr_dict("R_hit", "ship")
    # Compare MC avg damage with combinatorial
    comb_df = comb_combine_dice(1, 0, 0, "ship")
    comb_result = comb_add_set_die_to_roll(comb_df, "R_hit", "ship")
    comb_avg_dmg = (comb_result["damage"] * comb_result["proba"]).sum()
    mc_avg_dmg = (result_df["damage"] * result_df["proba"]).sum()
    check("3.1 — MC avg damage close to combinatorial",
          abs(mc_avg_dmg - comb_avg_dmg) < 0.15,
          f"MC={mc_avg_dmg:.4f}, comb={comb_avg_dmg:.4f}")
except Exception as e:
    check("3.1 — MC/comb damage agreement", False, str(e))

# --- Test 10: Works with different colors (blue, black) ---
try:
    roll_df2 = mc_combine_dice(0, 1, 0, "ship", sample_count=5000, seed=99)
    result_blue = mc_add_set_die_to_roll(roll_df2, "B_hit+crit", "ship")
    all_contain_b = all("B_hit+crit" in v for v in result_blue["value"])
    check("3.1 — add B_hit+crit: every value contains target", all_contain_b)
    check("3.2 — add B_hit+crit: profile is black die",
          "B_hit+crit" in result_blue.attrs["_mc_state"]["profiles"][-1]["values"])
except Exception as e:
    check("cross-color add_set_die", False, str(e))

# --- Test 11: Works with squad type ---
try:
    roll_df3 = mc_combine_dice(1, 0, 0, "squad", sample_count=3000, seed=7)
    result_squad = mc_add_set_die_to_roll(roll_df3, "U_hit", "squad")
    all_contain_u = all("U_hit" in v for v in result_squad["value"])
    check("3.1 — squad type: every value contains U_hit", all_contain_u)
    proba_sum_sq = result_squad["proba"].sum()
    check("3.3 — squad type: probabilities sum to ~1.0",
          abs(proba_sum_sq - 1.0) < 1e-9,
          f"sum = {proba_sum_sq}")
except Exception as e:
    check("squad type add_set_die", False, str(e))

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed")
if failed > 0:
    print("SOME TESTS FAILED")
else:
    print("ALL TESTS PASSED")
