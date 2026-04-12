"""
Exploratory tests to confirm the cross-color bug in change_die_face.
These tests MUST FAIL on unfixed code (bug confirmed when they fail).
After the fix is applied (Task 2), all four tests MUST PASS (Task 3).
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
from drc_stat_engine.stats.dice_maths_combinatories import change_die_face, combine_dice


def dataframes_equal(df1, df2):
    """Check that two roll DataFrames have identical value/proba rows (order-independent)."""
    if set(df1.columns) != set(df2.columns):
        return False
    df1_sorted = df1.sort_values("value").reset_index(drop=True)
    df2_sorted = df2.sort_values("value").reset_index(drop=True)
    return df1_sorted.equals(df2_sorted)


def test_black_pool_red_target():
    """Black pool + R_hit+hit target: result must equal original roll_df (no-op)."""
    roll_df = combine_dice(0, 0, 1, 'ship')
    source_faces = ["B_blank", "B_hit", "B_hit+crit"]
    result = change_die_face(roll_df, source_faces, "R_hit+hit", "ship")
    assert dataframes_equal(result, roll_df), (
        f"FAIL: black pool + R_hit+hit target modified roll_df\n"
        f"Original:\n{roll_df.to_string()}\n"
        f"Result:\n{result.to_string()}"
    )
    print("PASS: test_black_pool_red_target")


def test_blue_pool_black_target():
    """Blue pool + B_hit target: result must equal original roll_df (no-op)."""
    roll_df = combine_dice(0, 1, 0, 'ship')
    source_faces = ["U_acc", "U_hit", "U_crit"]
    result = change_die_face(roll_df, source_faces, "B_hit", "ship")
    assert dataframes_equal(result, roll_df), (
        f"FAIL: blue pool + B_hit target modified roll_df\n"
        f"Original:\n{roll_df.to_string()}\n"
        f"Result:\n{result.to_string()}"
    )
    print("PASS: test_blue_pool_black_target")


def test_red_pool_blue_target():
    """Red pool + U_acc target: result must equal original roll_df (no-op)."""
    roll_df = combine_dice(1, 0, 0, 'ship')
    source_faces = ["R_blank", "R_acc", "R_hit", "R_crit", "R_hit+hit"]
    result = change_die_face(roll_df, source_faces, "U_acc", "ship")
    assert dataframes_equal(result, roll_df), (
        f"FAIL: red pool + U_acc target modified roll_df\n"
        f"Original:\n{roll_df.to_string()}\n"
        f"Result:\n{result.to_string()}"
    )
    print("PASS: test_red_pool_blue_target")


def test_two_black_pool_red_blank_target():
    """2-black pool + R_blank target: result must equal original roll_df (no-op)."""
    roll_df = combine_dice(0, 0, 2, 'ship')
    source_faces = ["B_blank", "B_hit", "B_hit+crit"]
    result = change_die_face(roll_df, source_faces, "R_blank", "ship")
    assert dataframes_equal(result, roll_df), (
        f"FAIL: 2-black pool + R_blank target modified roll_df\n"
        f"Original:\n{roll_df.to_string()}\n"
        f"Result:\n{result.to_string()}"
    )
    print("PASS: test_two_black_pool_red_blank_target")


if __name__ == "__main__":
    passed = 0
    failed = 0
    tests = [
        test_black_pool_red_target,
        test_blue_pool_black_target,
        test_red_pool_blue_target,
        test_two_black_pool_red_blank_target,
    ]
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {test.__name__}\n  {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {test.__name__}\n  {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
