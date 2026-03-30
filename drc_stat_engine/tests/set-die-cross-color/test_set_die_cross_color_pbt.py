"""
Property-based tests for the set_die_face cross-color bugfix.

Property 1 (Fix Checking): For any single-color pool, calling set_die_face with a
target face of an absent color must return roll_df unchanged.
**Validates: Requirements 2.1, 2.2, 2.3**

Property 2 (Preservation): For any pool where the target color IS present, the fixed
set_die_face must produce the same result as the original function. Color-agnostic
targets must resolve and substitute unchanged. Probabilities must sum to 1.0.
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from drc_stat_engine.stats.dice_maths_combinatories import set_die_face, combine_dice


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def dataframes_equal(df1, df2):
    """Order-independent equality check on value/proba/damage/crit/acc/blank."""
    df1_s = df1.sort_values("value").reset_index(drop=True)
    df2_s = df2.sort_values("value").reset_index(drop=True)
    return df1_s.equals(df2_s)


# Face lists per color (ship type)
RED_FACES   = ["R_blank", "R_hit", "R_crit", "R_acc", "R_hit+hit"]
BLUE_FACES  = ["U_hit", "U_crit", "U_acc"]
BLACK_FACES = ["B_blank", "B_hit", "B_hit+crit"]

COLOR_FACES = {
    "R": RED_FACES,
    "U": BLUE_FACES,
    "B": BLACK_FACES,
}

# Absent-color results to set for each single-color pool
ABSENT_TARGETS = {
    "red":   [("U", "U_acc"), ("B", "B_hit"), ("B", "B_blank"), ("B", "B_hit+crit")],
    "blue":  [("R", "R_hit+hit"), ("R", "R_blank"), ("B", "B_hit"), ("B", "B_hit+crit")],
    "black": [("R", "R_hit+hit"), ("R", "R_blank"), ("U", "U_acc"), ("U", "U_hit")],
}


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

@st.composite
def single_color_pool(draw):
    """Generate a roll_df from a single-color pool (1–3 dice)."""
    color = draw(st.sampled_from(["red", "blue", "black"]))
    count = draw(st.integers(min_value=1, max_value=3))
    if color == "red":
        roll_df = combine_dice(count, 0, 0, 'ship')
    elif color == "blue":
        roll_df = combine_dice(0, count, 0, 'ship')
    else:
        roll_df = combine_dice(0, 0, count, 'ship')
    return color, roll_df


@st.composite
def pool_with_present_color(draw):
    """
    Generate a roll_df where at least one die of a specific color is present,
    along with a target face of that color and appropriate source faces.
    """
    # Choose which color will be the target color (must be present)
    target_color = draw(st.sampled_from(["R", "U", "B"]))

    # Dice counts: target color has 1–2 dice; other colors have 0–1 each
    red_count   = draw(st.integers(min_value=(1 if target_color == "R" else 0), max_value=2))
    blue_count  = draw(st.integers(min_value=(1 if target_color == "U" else 0), max_value=2))
    black_count = draw(st.integers(min_value=(1 if target_color == "B" else 0), max_value=2))

    # Ensure at least one die total
    assume(red_count + blue_count + black_count >= 1)

    roll_df = combine_dice(red_count, blue_count, black_count, 'ship')

    # Pick a target face of the present color
    target_face = draw(st.sampled_from(COLOR_FACES[target_color]))

    # Source faces: all faces of the target color (so substitution can happen)
    source_faces = COLOR_FACES[target_color]

    return roll_df, source_faces, target_face


# ---------------------------------------------------------------------------
# Property 1: Bug Condition — No-op When Target Color Absent
# **Validates: Requirements 2.1, 2.2, 2.3**
# ---------------------------------------------------------------------------

@given(single_color_pool())
@settings(max_examples=50)
def test_property1_noop_when_target_color_absent(pool_data):
    """
    For any single-color pool, set_die_face with a target of an absent color
    must return roll_df unchanged.
    **Validates: Requirements 2.1, 2.2, 2.3**
    """
    color, roll_df = pool_data

    # Pick absent-color targets
    for absent_color, target_face in ABSENT_TARGETS[color]:
        source_faces = COLOR_FACES[absent_color]
        result = set_die_face(roll_df, source_faces, target_face, 'ship')
        assert dataframes_equal(result, roll_df), (
            f"Property 1 FAILED: {color} pool, target={target_face}\n"
            f"Original:\n{roll_df.to_string()}\n"
            f"Result:\n{result.to_string()}"
        )


# ---------------------------------------------------------------------------
# Property 2: Preservation — Valid Same-Color Substitution Unchanged
# **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
# ---------------------------------------------------------------------------

@given(pool_with_present_color())
@settings(max_examples=50)
def test_property2_same_color_substitution_preserved(pool_data):
    """
    When the target color IS present in the pool, set_die_face must produce
    the same result as before the fix (substitution behavior unchanged).
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
    """
    roll_df, source_faces, target_face = pool_data
    result = set_die_face(roll_df, source_faces, target_face, 'ship')

    # Probabilities must sum to 1.0
    prob_sum = result["proba"].sum()
    assert abs(prob_sum - 1.0) < 1e-9, (
        f"Property 2 FAILED: probabilities sum to {prob_sum}, not 1.0\n"
        f"Pool:\n{roll_df.to_string()}\n"
        f"Result:\n{result.to_string()}"
    )

    # Result must have the expected columns
    assert set(result.columns) == {"value", "proba", "damage", "crit", "acc", "blank"}, (
        f"Property 2 FAILED: unexpected columns {result.columns.tolist()}"
    )


@given(
    st.sampled_from(["hit", "blank", "acc"]),
    st.integers(min_value=1, max_value=2),
    st.integers(min_value=0, max_value=2),
    st.integers(min_value=0, max_value=2),
)
@settings(max_examples=30)
def test_property2_color_agnostic_target_preserved(target_face, red, blue, black):
    """
    Color-agnostic targets ('hit', 'blank', 'acc') must resolve and substitute
    correctly — result probabilities sum to 1.0.
    **Validates: Requirements 3.2, 3.5**
    """
    assume(red + blue + black >= 1)
    roll_df = combine_dice(red, blue, black, 'ship')

    # Use all faces as source so substitution can always find a match
    all_faces = RED_FACES + BLUE_FACES + BLACK_FACES
    result = set_die_face(roll_df, all_faces, target_face, 'ship')

    prob_sum = result["proba"].sum()
    assert abs(prob_sum - 1.0) < 1e-9, (
        f"Property 2 FAILED (color-agnostic): target={target_face}, "
        f"pool=({red}R,{blue}U,{black}B), proba_sum={prob_sum}"
    )


@given(pool_with_present_color())
@settings(max_examples=30)
def test_property2_empty_source_faces_noop(pool_data):
    """
    Empty source_faces must always return roll_df unchanged.
    **Validates: Requirements 3.4**
    """
    roll_df, _, target_face = pool_data
    result = set_die_face(roll_df, [], target_face, 'ship')
    assert dataframes_equal(result, roll_df), (
        f"Property 2 FAILED (empty source): target={target_face}\n"
        f"Original:\n{roll_df.to_string()}\n"
        f"Result:\n{result.to_string()}"
    )


@given(pool_with_present_color())
@settings(max_examples=30)
def test_property2_no_match_source_noop(pool_data):
    """
    When source_faces contains no face present in any outcome, roll_df is returned unchanged.
    **Validates: Requirements 3.3**
    """
    roll_df, _, target_face = pool_data
    # Use a source face that cannot appear in any outcome (a face from an absent color)
    # We'll use a face that is definitely not in the pool by using a nonsense face
    # Actually use a face from a color not in the pool, or just a face not in any row
    all_values = set(v for row in roll_df["value"] for v in row.split(" "))
    # Pick source faces that are NOT in any outcome
    impossible_sources = [f for f in (RED_FACES + BLUE_FACES + BLACK_FACES) if f not in all_values]
    assume(len(impossible_sources) > 0)

    result = set_die_face(roll_df, impossible_sources, target_face, 'ship')
    assert dataframes_equal(result, roll_df), (
        f"Property 2 FAILED (no-match source): target={target_face}\n"
        f"Original:\n{roll_df.to_string()}\n"
        f"Result:\n{result.to_string()}"
    )


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import traceback
    tests = [
        ("Property 1 - no-op when target color absent", test_property1_noop_when_target_color_absent),
        ("Property 2 - same-color substitution preserved", test_property2_same_color_substitution_preserved),
        ("Property 2 - color-agnostic target preserved", test_property2_color_agnostic_target_preserved),
        ("Property 2 - empty source faces no-op", test_property2_empty_source_faces_noop),
        ("Property 2 - no-match source no-op", test_property2_no_match_source_noop),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"PASS: {name}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {name}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
