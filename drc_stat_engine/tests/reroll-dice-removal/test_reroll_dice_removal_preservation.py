"""
Preservation property tests for reroll-dice-removal.

These tests verify behaviors that are CORRECT on the UNFIXED code and must
remain correct after the fix is applied. All tests here MUST PASS on both
unfixed and fixed code.

Property 2: Preservation — Non-Duplicate Removal Behavior

Three sub-properties:
  1. For (value_str, removed_dice) pairs where each removed face type appears
     at most once in the value string, remove_dice_from_roll produces correct
     face counts (original - removed).
  2. For valid small pools, probability column sums to 1.0 after reroll_dice.
  3. NaN rows are always passed through to kept_df unchanged.
"""

import sys
sys.path.insert(0, '.')

from collections import Counter

import numpy as np
import pandas as pd
from hypothesis import given, assume, settings, HealthCheck
from hypothesis import strategies as st

from drc_stat_engine.stats.dice_maths_combinatories import (
    combine_dice,
    remove_dice_from_roll,
    reroll_dice,
    value_str_to_list,
    value_to_dice_attr_dict,
)

# Valid red die ship faces
RED_FACES = ["R_blank", "R_hit", "R_crit", "R_acc", "R_hit+hit"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_roll_df(value_str, type_str="ship"):
    """Build a single-row roll DataFrame from a value string."""
    faces = value_str_to_list(value_str)
    damage = sum(value_to_dice_attr_dict(f, type_str)["damage"] for f in faces)
    crit = sum(value_to_dice_attr_dict(f, type_str)["crit"] for f in faces)
    acc = sum(value_to_dice_attr_dict(f, type_str)["acc"] for f in faces)
    blank = sum(value_to_dice_attr_dict(f, type_str)["blank"] for f in faces)
    return pd.DataFrame([{
        "value": value_str,
        "proba": 1.0,
        "damage": damage,
        "crit": crit,
        "acc": acc,
        "blank": blank,
    }])


def is_bug_condition(value_str, removed_dice):
    """
    Return True when removed_dice contains a face token that appears more
    times in the value string than in removed_dice — i.e. duplicates exist
    beyond what should be removed. This is the condition that triggers the bug.
    """
    faces = value_str_to_list(value_str)
    face_counts = Counter(faces)
    remove_counts = Counter(removed_dice)
    for face_type, count_to_remove in remove_counts.items():
        if face_counts.get(face_type, 0) > count_to_remove:
            return True
    return False


# ---------------------------------------------------------------------------
# Property-based test 1: Non-duplicate removal produces correct face count
# Feature: reroll-dice-removal, Property 2: Preservation
# ---------------------------------------------------------------------------

@given(
    faces=st.lists(
        st.sampled_from(RED_FACES),
        min_size=2,
        max_size=6,
        unique=True,  # all faces unique — guarantees no duplicates
    ),
    removed_indices=st.data(),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.filter_too_much])
def test_unique_face_removal_correct_count(faces, removed_indices):
    """
    **Validates: Requirements 3.1, 3.4**

    For any roll value string and removed_dice list where each removed face
    type appears at most once in the value string (no excess duplicates / bug
    condition does NOT hold), remove_dice_from_roll produces a value string
    with exactly len(original_faces) - len(removed_dice) face tokens.

    This works correctly on UNFIXED code because the filter-based approach
    happens to be correct when there are no duplicate faces to over-remove.
    """
    # Feature: reroll-dice-removal, Property 2: Preservation

    value_str = " ".join(sorted(faces))
    original_count = len(faces)

    # Pick 1..min(3, len(faces)-1) faces to remove by index
    max_remove = min(3, original_count - 1)
    assume(max_remove >= 1)
    indices = removed_indices.draw(
        st.lists(
            st.integers(min_value=0, max_value=original_count - 1),
            min_size=1,
            max_size=max_remove,
            unique=True,
        )
    )
    removed_dice = [faces[i] for i in indices]

    # Ensure we are NOT in the bug condition
    assume(not is_bug_condition(value_str, removed_dice))

    # All removed faces must exist in the value string
    remaining = list(faces)
    for f in removed_dice:
        assume(f in remaining)
        remaining.remove(f)

    # Call the function under test
    roll_df = make_roll_df(value_str)
    to_remove = pd.Series([removed_dice], index=roll_df.index)
    removed_df, kept_df = remove_dice_from_roll(roll_df, to_remove, "ship")

    assert not removed_df.empty, "removed_df should not be empty"

    result_value = removed_df.iloc[0]["value"]
    result_faces = value_str_to_list(result_value)
    expected_count = original_count - len(removed_dice)

    assert len(result_faces) == expected_count, (
        f"Expected {expected_count} faces after removing {removed_dice} "
        f"from '{value_str}', but got {len(result_faces)} faces. "
        f"Result value: '{result_value}'"
    )


# ---------------------------------------------------------------------------
# Property-based test 2: Probability sums to 1.0 after reroll_dice
# Feature: reroll-dice-removal, Property 2: Preservation
# ---------------------------------------------------------------------------

@given(
    pool_size=st.integers(min_value=1, max_value=3),
    reroll_count=st.integers(min_value=1, max_value=2),
)
@settings(max_examples=100)
def test_reroll_dice_probability_sum(pool_size, reroll_count):
    """
    **Validates: Requirements 3.3**

    For any valid small red-only pool, after reroll_dice with blanks,
    the probability column sums to 1.0.

    This works correctly on UNFIXED code — the probability math is not
    affected by the value string bug.
    """
    # Feature: reroll-dice-removal, Property 2: Preservation

    assume(reroll_count <= pool_size)

    roll_df = combine_dice(pool_size, 0, 0, "ship")
    rerolled_df, _ = reroll_dice(
        roll_df,
        results_to_reroll=["R_blank"],
        reroll_count=reroll_count,
        type_str="ship",
    )

    proba_sum = rerolled_df["proba"].sum()
    assert abs(proba_sum - 1.0) < 1e-10, (
        f"Probability sum after reroll should be 1.0, got {proba_sum}. "
        f"Pool: {pool_size}R, reroll_count: {reroll_count}"
    )


# ---------------------------------------------------------------------------
# Property-based test 3: NaN rows pass through to kept_df unchanged
# Feature: reroll-dice-removal, Property 2: Preservation
# ---------------------------------------------------------------------------

@given(
    faces=st.lists(
        st.sampled_from(RED_FACES),
        min_size=1,
        max_size=6,
    ),
)
@settings(max_examples=100)
def test_nan_rows_pass_through_unchanged(faces):
    """
    **Validates: Requirements 3.5**

    For any roll value string, when removed_dice is NaN for a row, that row
    passes through to kept_df unchanged — value, proba, and all stats match
    the original.

    This works correctly on UNFIXED code — NaN handling is not affected by
    the value string bug.
    """
    # Feature: reroll-dice-removal, Property 2: Preservation

    value_str = " ".join(sorted(faces))
    roll_df = make_roll_df(value_str)

    # NaN removal — row should be kept unchanged
    to_remove = pd.Series([np.nan], index=roll_df.index)
    removed_df, kept_df = remove_dice_from_roll(roll_df, to_remove, "ship")

    assert removed_df.empty, (
        f"removed_df should be empty when removed_dice is NaN, "
        f"but has {len(removed_df)} rows"
    )
    assert len(kept_df) == 1, (
        f"kept_df should have exactly 1 row, got {len(kept_df)}"
    )
    assert kept_df.iloc[0]["value"] == value_str, (
        f"kept_df value should match original '{value_str}', "
        f"got '{kept_df.iloc[0]['value']}'"
    )
    assert kept_df.iloc[0]["proba"] == roll_df.iloc[0]["proba"], (
        f"kept_df proba should match original"
    )
    for stat in ("damage", "crit", "acc", "blank"):
        assert kept_df.iloc[0][stat] == roll_df.iloc[0][stat], (
            f"kept_df {stat} should match original"
        )


# ---------------------------------------------------------------------------
# Concrete observation tests
# Feature: reroll-dice-removal, Property 2: Preservation
# ---------------------------------------------------------------------------

def test_concrete_single_unique_removal():
    """
    Observation: remove 1 R_blank from "R_acc R_blank R_crit R_hit R_hit R_hit"
    where R_blank appears only once → value is "R_acc R_crit R_hit R_hit R_hit" (correct).
    """
    # Feature: reroll-dice-removal, Property 2: Preservation
    value_str = "R_acc R_blank R_crit R_hit R_hit R_hit"
    removed_dice = ["R_blank"]

    roll_df = make_roll_df(value_str)
    to_remove = pd.Series([removed_dice], index=roll_df.index)
    removed_df, _ = remove_dice_from_roll(roll_df, to_remove, "ship")

    result_value = removed_df.iloc[0]["value"]
    assert result_value == "R_acc R_crit R_hit R_hit R_hit", (
        f"Expected 'R_acc R_crit R_hit R_hit R_hit', got '{result_value}'"
    )


def test_concrete_nan_passthrough():
    """
    Observation: rows with NaN removed_dice pass through to kept_df unchanged.
    """
    # Feature: reroll-dice-removal, Property 2: Preservation
    value_str = "R_acc R_blank R_crit R_hit R_hit R_hit"
    roll_df = make_roll_df(value_str)
    to_remove = pd.Series([np.nan], index=roll_df.index)
    removed_df, kept_df = remove_dice_from_roll(roll_df, to_remove, "ship")

    assert removed_df.empty, "removed_df should be empty for NaN removal"
    assert kept_df.iloc[0]["value"] == value_str, (
        f"kept_df value should match original '{value_str}'"
    )


def test_concrete_reroll_proba_sum():
    """
    Observation: reroll_dice on 2R pool rerolling 1 blank preserves proba sum of 1.0.
    """
    # Feature: reroll-dice-removal, Property 2: Preservation
    roll_df = combine_dice(2, 0, 0, "ship")
    rerolled_df, _ = reroll_dice(
        roll_df,
        results_to_reroll=["R_blank"],
        reroll_count=1,
        type_str="ship",
    )
    proba_sum = rerolled_df["proba"].sum()
    assert abs(proba_sum - 1.0) < 1e-10, (
        f"Probability sum should be 1.0, got {proba_sum}"
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    passed = 0
    failed = 0
    errors = []

    # Concrete tests
    concrete_tests = [
        ("Concrete: single unique face removal", test_concrete_single_unique_removal),
        ("Concrete: NaN passthrough", test_concrete_nan_passthrough),
        ("Concrete: reroll proba sum", test_concrete_reroll_proba_sum),
    ]

    for name, fn in concrete_tests:
        try:
            fn()
            print(f"PASS: {name}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {name} — {e}")
            failed += 1
            errors.append(str(e))
        except Exception as e:
            print(f"FAIL: {name} — {type(e).__name__}: {e}")
            failed += 1
            errors.append(f"{type(e).__name__}: {e}")

    # Property-based tests
    property_tests = [
        ("Property: unique face removal correct count", test_unique_face_removal_correct_count),
        ("Property: reroll_dice probability sum", test_reroll_dice_probability_sum),
        ("Property: NaN rows pass through unchanged", test_nan_rows_pass_through_unchanged),
    ]

    for name, fn in property_tests:
        try:
            fn()
            print(f"PASS: {name}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {name} — {e}")
            failed += 1
            errors.append(str(e))
        except Exception as e:
            print(f"FAIL: {name} — {type(e).__name__}: {e}")
            failed += 1
            errors.append(f"{type(e).__name__}: {e}")

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    if errors:
        print(f"\nFailures:")
        for err in errors:
            print(f"  - {err}")
