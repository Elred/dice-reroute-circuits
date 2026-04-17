"""Smoke tests for color_in_pool_add (Task 3.4).

Verifies:
- Rows are partitioned by selected color and correct die is added per group
- Probability integrity is preserved
- All outcomes gain exactly one extra die token
- Different priority orders produce different color selections
Requirements: 10.1, 10.2, 10.3, 10.4
"""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.dice_maths_combinatories import (
    color_in_pool_add,
    combine_dice,
    value_str_to_list,
    value_to_dice_count_dict,
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


type_str = "ship"

# ---------------------------------------------------------------------------
# Test 1: 1R 1B pool, priority ["red", "blue", "black"]
# All outcomes have both R and B tokens → red is first priority → add red die
# ---------------------------------------------------------------------------
try:
    roll_df = combine_dice(1, 0, 1, type_str)
    orig_total_dice = 2  # 1R + 1B

    result = color_in_pool_add(roll_df, ["red", "blue", "black"], type_str)

    # Probability integrity
    total_proba = result["proba"].sum()
    check("1R1B red-first: probability sums to 1.0",
          abs(total_proba - 1.0) < 1e-9, f"got {total_proba}")

    # Every outcome should have 3 tokens (original 2 + 1 added)
    for _, row in result.iterrows():
        tokens = value_str_to_list(row["value"])
        check(f"1R1B red-first: '{row['value']}' has 3 tokens",
              len(tokens) == 3, f"got {len(tokens)} tokens")

    # Since all outcomes have R tokens and red is first priority,
    # all added dice should be red
    for _, row in result.iterrows():
        counts = value_to_dice_count_dict(row["value"], type_str)
        check(f"1R1B red-first: '{row['value']}' has 2 red dice",
              counts["red"] == 2, f"red count = {counts['red']}")

except Exception as e:
    check("1R1B red-first", False, str(e))

# ---------------------------------------------------------------------------
# Test 2: Same pool, priority ["black", "red", "blue"]
# All outcomes have both R and B tokens → black is first priority → add black die
# ---------------------------------------------------------------------------
try:
    roll_df = combine_dice(1, 0, 1, type_str)

    result = color_in_pool_add(roll_df, ["black", "red", "blue"], type_str)

    total_proba = result["proba"].sum()
    check("1R1B black-first: probability sums to 1.0",
          abs(total_proba - 1.0) < 1e-9, f"got {total_proba}")

    for _, row in result.iterrows():
        counts = value_to_dice_count_dict(row["value"], type_str)
        check(f"1R1B black-first: '{row['value']}' has 2 black dice",
              counts["black"] == 2, f"black count = {counts['black']}")

except Exception as e:
    check("1R1B black-first", False, str(e))

# ---------------------------------------------------------------------------
# Test 3: 1R pool only, priority ["blue", "red", "black"]
# No blue tokens → skip blue → red is next → add red die
# ---------------------------------------------------------------------------
try:
    roll_df = combine_dice(1, 0, 0, type_str)

    result = color_in_pool_add(roll_df, ["blue", "red", "black"], type_str)

    total_proba = result["proba"].sum()
    check("1R blue-first: probability sums to 1.0",
          abs(total_proba - 1.0) < 1e-9, f"got {total_proba}")

    for _, row in result.iterrows():
        counts = value_to_dice_count_dict(row["value"], type_str)
        check(f"1R blue-first: '{row['value']}' has 2 red dice",
              counts["red"] == 2, f"red={counts['red']}, blue={counts['blue']}, black={counts['black']}")

except Exception as e:
    check("1R blue-first", False, str(e))

# ---------------------------------------------------------------------------
# Test 4: 1R 1U 1B pool — all colors present, priority determines which
# ---------------------------------------------------------------------------
try:
    roll_df = combine_dice(1, 1, 1, type_str)

    result = color_in_pool_add(roll_df, ["blue", "black", "red"], type_str)

    total_proba = result["proba"].sum()
    check("1R1U1B blue-first: probability sums to 1.0",
          abs(total_proba - 1.0) < 1e-9, f"got {total_proba}")

    # All outcomes have all 3 colors → blue is first → add blue die
    for _, row in result.iterrows():
        counts = value_to_dice_count_dict(row["value"], type_str)
        check(f"1R1U1B blue-first: '{row['value']}' has 2 blue dice",
              counts["blue"] == 2, f"blue={counts['blue']}")

except Exception as e:
    check("1R1U1B blue-first", False, str(e))

# ---------------------------------------------------------------------------
# Test 5: squad type works too
# ---------------------------------------------------------------------------
try:
    roll_df = combine_dice(1, 0, 1, "squad")

    result = color_in_pool_add(roll_df, ["red", "blue", "black"], "squad")

    total_proba = result["proba"].sum()
    check("squad 1R1B: probability sums to 1.0",
          abs(total_proba - 1.0) < 1e-9, f"got {total_proba}")

    for _, row in result.iterrows():
        tokens = value_str_to_list(row["value"])
        check(f"squad 1R1B: '{row['value']}' has 3 tokens",
              len(tokens) == 3, f"got {len(tokens)}")

except Exception as e:
    check("squad type", False, str(e))


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
