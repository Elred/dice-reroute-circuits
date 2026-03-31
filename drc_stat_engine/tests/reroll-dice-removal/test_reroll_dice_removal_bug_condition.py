"""
Bug condition exploration test for reroll-dice-removal.

This test encodes the EXPECTED (fixed) behavior: remove_dice_from_roll should
remove exactly len(removed_dice) face tokens from the value string, one at a
time, preserving remaining duplicates.

On UNFIXED code, this test is EXPECTED TO FAIL — the current filter
`v not in x["removed_dice"]` removes ALL occurrences of a face type instead
of one-at-a-time when duplicates exist.

Failure on unfixed code confirms the bug exists.
"""

import sys
sys.path.insert(0, '.')

from collections import Counter

import numpy as np
import pandas as pd
from hypothesis import given, assume, settings, HealthCheck
from hypothesis import strategies as st

from drc_stat_engine.stats.dice_maths_combinatories import (
    remove_dice_from_roll,
    value_str_to_list,
    value_to_dice_attr_dict,
)

# Valid red die ship faces (we use red-only for simplicity — bug is color-agnostic)
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
    beyond what should be removed.
    """
    faces = value_str_to_list(value_str)
    face_counts = Counter(faces)
    remove_counts = Counter(removed_dice)
    for face_type, count_to_remove in remove_counts.items():
        if face_counts.get(face_type, 0) > count_to_remove:
            return True
    return False


# ---------------------------------------------------------------------------
# Property-based test
# Feature: reroll-dice-removal, Property 1: Bug Condition
# ---------------------------------------------------------------------------

@given(
    faces=st.lists(
        st.sampled_from(RED_FACES),
        min_size=2,
        max_size=6,
    ),
    removed_indices=st.data(),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.filter_too_much])
def test_bug_condition_exact_removal_count(faces, removed_indices):
    """
    **Validates: Requirements 2.1, 2.2, 2.3**

    For any roll value string and removed_dice list where the bug condition
    holds (duplicate faces exist beyond the removal count), the function
    remove_dice_from_roll SHALL produce a value string with exactly
    len(original_faces) - len(removed_dice) face tokens.

    On unfixed code this FAILS because the filter removes ALL occurrences
    of each face type in removed_dice.
    """
    # Feature: reroll-dice-removal, Property 1: Bug Condition

    # Build a sorted value string from the generated faces
    value_str = " ".join(sorted(faces))
    original_count = len(faces)

    # Pick 1..min(3, len(faces)-1) faces to remove (by index into the face list)
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

    # Only test the bug condition: duplicates exist beyond removal count
    assume(is_bug_condition(value_str, removed_dice))

    # All removed faces must actually exist in the value string
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
        f"Bug confirmed: expected {expected_count} faces after removing "
        f"{removed_dice} from {value_str}, but got {len(result_faces)} faces. "
        f"Result value: '{result_value}'"
    )


# ---------------------------------------------------------------------------
# Concrete test cases
# Feature: reroll-dice-removal, Property 1: Bug Condition
# ---------------------------------------------------------------------------

def test_concrete_remove_1_blank_from_2_blanks():
    """
    Remove 1 R_blank from "R_acc R_blank R_blank R_crit R_hit R_hit"
    → expect 5 faces, observe 4 on buggy code.
    """
    # Feature: reroll-dice-removal, Property 1: Bug Condition
    value_str = "R_acc R_blank R_blank R_crit R_hit R_hit"
    removed_dice = ["R_blank"]

    roll_df = make_roll_df(value_str)
    to_remove = pd.Series([removed_dice], index=roll_df.index)
    removed_df, _ = remove_dice_from_roll(roll_df, to_remove, "ship")

    result_value = removed_df.iloc[0]["value"]
    result_faces = value_str_to_list(result_value)

    assert len(result_faces) == 5, (
        f"Bug confirmed: expected 5 faces after removing 1 R_blank from "
        f"'{value_str}', but got {len(result_faces)} faces. "
        f"Result: '{result_value}'"
    )


def test_concrete_remove_blank_and_acc_from_2_blanks():
    """
    Remove ["R_blank", "R_acc"] from "R_acc R_blank R_blank R_crit R_hit R_hit"
    → expect 4 faces, observe 3 on buggy code.
    """
    # Feature: reroll-dice-removal, Property 1: Bug Condition
    value_str = "R_acc R_blank R_blank R_crit R_hit R_hit"
    removed_dice = ["R_blank", "R_acc"]

    roll_df = make_roll_df(value_str)
    to_remove = pd.Series([removed_dice], index=roll_df.index)
    removed_df, _ = remove_dice_from_roll(roll_df, to_remove, "ship")

    result_value = removed_df.iloc[0]["value"]
    result_faces = value_str_to_list(result_value)

    assert len(result_faces) == 4, (
        f"Bug confirmed: expected 4 faces after removing ['R_blank', 'R_acc'] "
        f"from '{value_str}', but got {len(result_faces)} faces. "
        f"Result: '{result_value}'"
    )


def test_concrete_remove_2_hits_from_3_hits():
    """
    Remove ["R_hit", "R_hit"] from "R_acc R_blank R_crit R_hit R_hit R_hit"
    → expect 4 faces, observe 3 on buggy code.
    """
    # Feature: reroll-dice-removal, Property 1: Bug Condition
    value_str = "R_acc R_blank R_crit R_hit R_hit R_hit"
    removed_dice = ["R_hit", "R_hit"]

    roll_df = make_roll_df(value_str)
    to_remove = pd.Series([removed_dice], index=roll_df.index)
    removed_df, _ = remove_dice_from_roll(roll_df, to_remove, "ship")

    result_value = removed_df.iloc[0]["value"]
    result_faces = value_str_to_list(result_value)

    assert len(result_faces) == 4, (
        f"Bug confirmed: expected 4 faces after removing ['R_hit', 'R_hit'] "
        f"from '{value_str}', but got {len(result_faces)} faces. "
        f"Result: '{result_value}'"
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    passed = 0
    failed = 0
    errors = []

    # Concrete tests
    for name, fn in [
        ("Remove 1 R_blank from 2 R_blanks (expect 5, buggy gives 4)",
         test_concrete_remove_1_blank_from_2_blanks),
        ("Remove [R_blank, R_acc] from 2 R_blanks (expect 4, buggy gives 3)",
         test_concrete_remove_blank_and_acc_from_2_blanks),
        ("Remove [R_hit, R_hit] from 3 R_hits (expect 4, buggy gives 3)",
         test_concrete_remove_2_hits_from_3_hits),
    ]:
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

    # Property-based test
    try:
        test_bug_condition_exact_removal_count()
        print("PASS: Property test — exact removal count")
        passed += 1
    except AssertionError as e:
        print(f"FAIL: Property test — {e}")
        failed += 1
        errors.append(str(e))
    except Exception as e:
        print(f"FAIL: Property test — {type(e).__name__}: {e}")
        failed += 1
        errors.append(f"{type(e).__name__}: {e}")

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    if errors:
        print(f"\nCounterexamples / failures:")
        for err in errors:
            print(f"  - {err}")
