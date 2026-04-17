"""Smoke tests for conditional_add_partition (Task 3.3).

Verifies:
- Partitioning by face condition works for add_dice and add_set_die
- Non-matching rows are unchanged
- Matching rows get the die added
- Empty matching partition returns unchanged
- Probability integrity is preserved
"""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.dice_maths_combinatories import (
    add_dice_to_roll,
    add_set_die_to_roll,
    combine_dice,
    conditional_add_partition,
    value_str_to_list,
)

passed = 0
failed = 0
errors = []


def check(name, condition, msg=""):
    global passed, failed
    if condition:
        print(f"PASS: {name}")
        passed += 1
    else:
        print(f"FAIL: {name} — {msg}")
        failed += 1
        errors.append((name, msg))


# ---------------------------------------------------------------------------
# Setup: 1 red die pool (5 outcomes: R_blank, R_hit, R_crit, R_acc, R_hit+hit)
# ---------------------------------------------------------------------------
type_str = "ship"
roll_df = combine_dice(1, 0, 0, type_str)

# ---------------------------------------------------------------------------
# Test 1: conditional add_set_die with face_condition="R_hit"
# Only outcomes containing "R_hit" should get the set die added.
# ---------------------------------------------------------------------------
try:
    result = conditional_add_partition(
        roll_df, "R_hit", add_set_die_to_roll,
        target_result="B_hit", type_str=type_str,
    )
    # R_hit is present in exactly one outcome of a 1-red-die pool
    # Matching rows should have 2 tokens, non-matching should have 1
    matching_rows = result[result["value"].apply(lambda v: len(v.split(" ")) == 2)]
    non_matching_rows = result[result["value"].apply(lambda v: len(v.split(" ")) == 1)]

    check("conditional add_set_die: matching rows exist",
          len(matching_rows) > 0, f"got {len(matching_rows)} matching rows")

    check("conditional add_set_die: non-matching rows exist",
          len(non_matching_rows) > 0, f"got {len(non_matching_rows)} non-matching rows")

    # Non-matching rows should be the original outcomes minus R_hit
    orig_non_matching = roll_df[roll_df["value"] != "R_hit"]
    for _, row in non_matching_rows.iterrows():
        orig_row = orig_non_matching[orig_non_matching["value"] == row["value"]]
        check(f"conditional add_set_die: non-matching '{row['value']}' unchanged",
              len(orig_row) == 1 and abs(orig_row.iloc[0]["proba"] - row["proba"]) < 1e-12,
              f"row not found or proba mismatch")

    # Matching row should contain B_hit
    for _, row in matching_rows.iterrows():
        tokens = value_str_to_list(row["value"])
        check(f"conditional add_set_die: matching '{row['value']}' contains B_hit",
              "B_hit" in tokens, f"tokens: {tokens}")

    # Probability integrity
    total_proba = result["proba"].sum()
    check("conditional add_set_die: probability sums to 1.0",
          abs(total_proba - 1.0) < 1e-9, f"got {total_proba}")

except Exception as e:
    check("conditional add_set_die", False, str(e))


# ---------------------------------------------------------------------------
# Test 2: conditional add_dice with face_condition="R_acc"
# Only outcomes containing "R_acc" should get the extra die.
# ---------------------------------------------------------------------------
try:
    result = conditional_add_partition(
        roll_df, "R_acc", add_dice_to_roll,
        black=1, type_str=type_str,
    )
    # R_acc has proba 0.125 in a 1-red-die pool
    # Matching rows should have 2 tokens, non-matching should have 1
    matching_rows = result[result["value"].apply(lambda v: len(v.split(" ")) == 2)]
    non_matching_rows = result[result["value"].apply(lambda v: len(v.split(" ")) == 1)]

    check("conditional add_dice: matching rows exist",
          len(matching_rows) > 0, f"got {len(matching_rows)} matching rows")

    check("conditional add_dice: non-matching rows exist",
          len(non_matching_rows) > 0, f"got {len(non_matching_rows)} non-matching rows")

    # Probability integrity
    total_proba = result["proba"].sum()
    check("conditional add_dice: probability sums to 1.0",
          abs(total_proba - 1.0) < 1e-9, f"got {total_proba}")

except Exception as e:
    check("conditional add_dice", False, str(e))


# ---------------------------------------------------------------------------
# Test 3: empty matching partition (face not present in any outcome)
# face_condition="U_hit" on a pool with no blue dice → no matches
# ---------------------------------------------------------------------------
try:
    result = conditional_add_partition(
        roll_df, "U_hit", add_set_die_to_roll,
        target_result="B_hit", type_str=type_str,
    )
    # Should return unchanged
    check("empty matching: same number of rows",
          len(result) == len(roll_df),
          f"expected {len(roll_df)} rows, got {len(result)}")

    # Values should be identical
    orig_values = set(roll_df["value"].tolist())
    result_values = set(result["value"].tolist())
    check("empty matching: same value strings",
          orig_values == result_values,
          f"values differ: {orig_values.symmetric_difference(result_values)}")

    total_proba = result["proba"].sum()
    check("empty matching: probability sums to 1.0",
          abs(total_proba - 1.0) < 1e-9, f"got {total_proba}")

except Exception as e:
    check("empty matching partition", False, str(e))


# ---------------------------------------------------------------------------
# Test 4: all rows match (face_condition on a face present in every outcome)
# Use a 1-red pool and condition on a face that appears in all outcomes?
# Actually no single face appears in all outcomes of a 1-red pool.
# Use a pool where we've already added a set die, so all outcomes have it.
# ---------------------------------------------------------------------------
try:
    # Start with 1 red die, add a set B_hit to all outcomes
    pool_with_set = add_set_die_to_roll(roll_df, "B_hit", type_str)
    # Now every outcome contains B_hit
    result = conditional_add_partition(
        pool_with_set, "B_hit", add_set_die_to_roll,
        target_result="R_acc", type_str=type_str,
    )
    # All rows should have 3 tokens (original + B_hit + R_acc)
    for _, row in result.iterrows():
        tokens = value_str_to_list(row["value"])
        check(f"all match: '{row['value']}' has 3 tokens",
              len(tokens) == 3, f"got {len(tokens)} tokens: {tokens}")

    total_proba = result["proba"].sum()
    check("all match: probability sums to 1.0",
          abs(total_proba - 1.0) < 1e-9, f"got {total_proba}")

except Exception as e:
    check("all rows match", False, str(e))


# ---------------------------------------------------------------------------
# Test 5: Larger pool — 1R 1B, condition on R_blank
# ---------------------------------------------------------------------------
try:
    roll_df_2 = combine_dice(1, 0, 1, type_str)
    orig_count = len(roll_df_2)

    result = conditional_add_partition(
        roll_df_2, "R_blank", add_set_die_to_roll,
        target_result="U_hit", type_str=type_str,
    )

    # Outcomes with R_blank should now also have U_hit
    for _, row in result.iterrows():
        tokens = value_str_to_list(row["value"])
        if "R_blank" in tokens:
            check(f"larger pool: '{row['value']}' with R_blank has U_hit",
                  "U_hit" in tokens, f"tokens: {tokens}")

    total_proba = result["proba"].sum()
    check("larger pool: probability sums to 1.0",
          abs(total_proba - 1.0) < 1e-9, f"got {total_proba}")

except Exception as e:
    check("larger pool conditional", False, str(e))


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    for name, err in errors:
        print(f"  {name}: {err}")
