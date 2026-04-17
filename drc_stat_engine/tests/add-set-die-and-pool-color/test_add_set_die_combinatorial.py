"""Property-based tests for combinatorial add_set_die (Properties 2, 3).

Uses Hypothesis for property-based testing. Each property test is tagged with
a comment referencing the design property it validates.
"""
import sys
sys.path.insert(0, '.')

from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from drc_stat_engine.stats.dice_maths_combinatories import (
    add_set_die_to_roll,
    combine_dice,
    value_to_dice_attr_dict,
    value_str_to_list,
)
from drc_stat_engine.stats.dice_models import VALID_FACES_BY_TYPE

# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

pool_types = st.sampled_from(["ship", "squad"])

all_faces = {
    "ship": sorted(VALID_FACES_BY_TYPE["ship"]),
    "squad": sorted(VALID_FACES_BY_TYPE["squad"]),
}


@st.composite
def small_pool_and_face(draw):
    """Generate a small dice pool (0-2 of each color, at least 1 die total)
    and a valid face string for that pool type."""
    type_str = draw(pool_types)
    red = draw(st.integers(min_value=0, max_value=2))
    blue = draw(st.integers(min_value=0, max_value=2))
    black = draw(st.integers(min_value=0, max_value=2))
    assume(red + blue + black >= 1)
    face = draw(st.sampled_from(all_faces[type_str]))
    return type_str, red, blue, black, face


passed = 0
failed = 0
errors = []

# ---------------------------------------------------------------------------
# Property 2: add_set_die appends face and updates stats correctly
# Feature: add-set-die-and-pool-color, Property 2: add_set_die appends face and updates stats correctly
# **Validates: Requirements 2.1, 2.2**
# ---------------------------------------------------------------------------

prop2_pass = True
prop2_error = None

try:
    @given(data=small_pool_and_face())
    @settings(max_examples=100, deadline=None)
    def test_prop2_add_set_die_appends_face_and_updates_stats(data):
        """For any small dice pool and any valid face string, after add_set_die_to_roll:
        - Every outcome's value string contains the target face token
        - The damage/crit/acc/blank columns increase by exactly the face's attribute values
        """
        type_str, red, blue, black, face = data

        roll_df = combine_dice(red, blue, black, type_str)
        attrs = value_to_dice_attr_dict(face, type_str)
        result = add_set_die_to_roll(roll_df, face, type_str)

        # Build a lookup from original value -> original stats
        orig_lookup = {}
        for _, row in roll_df.iterrows():
            orig_lookup[row["value"]] = {
                "damage": row["damage"],
                "crit": row["crit"],
                "acc": row["acc"],
                "blank": row["blank"],
            }

        # Check every outcome in the result
        for _, row in result.iterrows():
            tokens = value_str_to_list(row["value"])

            # Every outcome must contain the target face token
            assert face in tokens, (
                f"Target face '{face}' not found in outcome '{row['value']}'"
            )

            # Reconstruct the original value by removing one occurrence of the face
            orig_tokens = list(tokens)
            orig_tokens.remove(face)
            orig_value = " ".join(sorted(orig_tokens))

            # The original value must exist in the original roll
            assert orig_value in orig_lookup, (
                f"Original value '{orig_value}' not found in original roll"
            )

            orig_stats = orig_lookup[orig_value]
            for stat in ("damage", "crit", "acc", "blank"):
                expected = orig_stats[stat] + attrs[stat]
                actual = row[stat]
                assert actual == expected, (
                    f"Stat '{stat}' mismatch for '{row['value']}': "
                    f"expected {expected} (orig {orig_stats[stat]} + face {attrs[stat]}), "
                    f"got {actual}"
                )

    test_prop2_add_set_die_appends_face_and_updates_stats()
except Exception as e:
    prop2_pass = False
    prop2_error = str(e)

if prop2_pass:
    print("PASS: Property 2 — add_set_die appends face and updates stats correctly")
    passed += 1
else:
    print(f"FAIL: Property 2 — {prop2_error}")
    failed += 1
    errors.append(("Property 2", prop2_error))


# ---------------------------------------------------------------------------
# Property 3: Probability integrity after add operations
# Feature: add-set-die-and-pool-color, Property 3: Probability integrity after add operations
# **Validates: Requirements 2.3, 5.6, 10.4**
# ---------------------------------------------------------------------------

prop3_pass = True
prop3_error = None

try:
    @given(data=small_pool_and_face())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow], database=None)
    def test_prop3_probability_integrity_after_add_set_die(data):
        """For any small dice pool and any valid add_set_die operation,
        the resulting Roll_DataFrame's probabilities sum to 1.0 within tolerance (1e-9)."""
        type_str, red, blue, black, face = data

        roll_df = combine_dice(red, blue, black, type_str)
        result = add_set_die_to_roll(roll_df, face, type_str)

        total_proba = result["proba"].sum()
        assert abs(total_proba - 1.0) < 1e-9, (
            f"Probability sum = {total_proba}, expected 1.0 "
            f"(pool: {red}R {blue}U {black}B {type_str}, face: {face})"
        )

    test_prop3_probability_integrity_after_add_set_die()
except Exception as e:
    prop3_pass = False
    prop3_error = str(e)

if prop3_pass:
    print("PASS: Property 3 — Probability integrity after add operations")
    passed += 1
else:
    print(f"FAIL: Property 3 — {prop3_error}")
    failed += 1
    errors.append(("Property 3", prop3_error))


# ---------------------------------------------------------------------------
# Additional imports for Properties 5 and 7
# ---------------------------------------------------------------------------
from drc_stat_engine.stats.dice_maths_combinatories import (
    add_dice_to_roll,
    conditional_add_partition,
)
from drc_stat_engine.stats.dice_models import (
    evaluate_face_condition,
    select_color_from_pool,
    COLOR_PREFIXES,
)


# ---------------------------------------------------------------------------
# Generators for Properties 5 and 7
# ---------------------------------------------------------------------------

@st.composite
def small_pool_with_face_condition(draw):
    """Generate a small dice pool (1-2 of each color, at least 1 die),
    a valid face for that pool type to use as face_condition,
    and a valid face for add_set_die target_result."""
    type_str = draw(pool_types)
    red = draw(st.integers(min_value=0, max_value=2))
    blue = draw(st.integers(min_value=0, max_value=2))
    black = draw(st.integers(min_value=0, max_value=2))
    assume(red + blue + black >= 1)
    face_condition = draw(st.sampled_from(all_faces[type_str]))
    target_result = draw(st.sampled_from(all_faces[type_str]))
    return type_str, red, blue, black, face_condition, target_result


@st.composite
def small_pool_with_face_condition_add_dice(draw):
    """Generate a small dice pool and a face_condition for conditional add_dice.
    Also generates which color die to add (1 die of one color)."""
    type_str = draw(pool_types)
    red = draw(st.integers(min_value=0, max_value=2))
    blue = draw(st.integers(min_value=0, max_value=2))
    black = draw(st.integers(min_value=0, max_value=2))
    assume(red + blue + black >= 1)
    face_condition = draw(st.sampled_from(all_faces[type_str]))
    add_color = draw(st.sampled_from(["red", "blue", "black"]))
    return type_str, red, blue, black, face_condition, add_color


color_priority_perms = st.permutations(["red", "blue", "black"])


# ---------------------------------------------------------------------------
# Property 5: Conditional add applies only to matching outcomes
# Feature: add-set-die-and-pool-color, Property 5: Conditional add applies only to matching outcomes
# **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 6.2, 6.5**
# ---------------------------------------------------------------------------

prop5_pass = True
prop5_error = None

# --- Sub-property 5a: conditional add_set_die ---
try:
    @given(data=small_pool_with_face_condition())
    @settings(max_examples=100, deadline=None)
    def test_prop5a_conditional_add_set_die(data):
        """For any pool and face_condition, after conditional add_set_die:
        - Matching outcomes (containing face_condition) get the target face appended
        - Non-matching outcomes remain unchanged (same value string and stats)
        """
        type_str, red, blue, black, face_condition, target_result = data

        roll_df = combine_dice(red, blue, black, type_str)
        result = conditional_add_partition(
            roll_df, face_condition, add_set_die_to_roll,
            target_result=target_result, type_str=type_str,
        )

        # Build lookup of original rows
        orig_lookup = {}
        for _, row in roll_df.iterrows():
            orig_lookup[row["value"]] = {
                "proba": row["proba"],
                "damage": row["damage"],
                "crit": row["crit"],
                "acc": row["acc"],
                "blank": row["blank"],
            }

        target_attrs = value_to_dice_attr_dict(target_result, type_str)

        for _, row in result.iterrows():
            tokens = value_str_to_list(row["value"])

            if row["value"] in orig_lookup and not evaluate_face_condition(face_condition, row["value"]):
                # Non-matching outcome that wasn't modified — should be unchanged
                orig = orig_lookup[row["value"]]
                for stat in ("damage", "crit", "acc", "blank"):
                    assert row[stat] == orig[stat], (
                        f"Non-matching outcome '{row['value']}' stat '{stat}' changed: "
                        f"expected {orig[stat]}, got {row[stat]}"
                    )

        # Check that matching original outcomes produced results with the target face
        for orig_value, orig_stats in orig_lookup.items():
            if evaluate_face_condition(face_condition, orig_value):
                # This outcome should have been modified — the target face should appear
                # in some result row whose tokens are orig_tokens + [target_result]
                expected_tokens = sorted(value_str_to_list(orig_value) + [target_result])
                expected_value = " ".join(expected_tokens)
                matching_result = result[result["value"] == expected_value]
                assert len(matching_result) > 0, (
                    f"Matching outcome '{orig_value}' should produce '{expected_value}' "
                    f"but it was not found in result"
                )

    test_prop5a_conditional_add_set_die()
except Exception as e:
    prop5_pass = False
    prop5_error = str(e)

# --- Sub-property 5b: conditional add_dice ---
try:
    @given(data=small_pool_with_face_condition_add_dice())
    @settings(max_examples=100, deadline=None)
    def test_prop5b_conditional_add_dice(data):
        """For any pool and face_condition, after conditional add_dice:
        - Non-matching outcomes remain unchanged
        - Matching outcomes get extra dice (more tokens)
        - Probability sums to 1.0
        """
        type_str, red, blue, black, face_condition, add_color = data

        roll_df = combine_dice(red, blue, black, type_str)

        add_kwargs = {"red": 0, "blue": 0, "black": 0, "type_str": type_str}
        add_kwargs[add_color] = 1

        result = conditional_add_partition(
            roll_df, face_condition, add_dice_to_roll,
            **add_kwargs,
        )

        orig_token_count = len(value_str_to_list(roll_df.iloc[0]["value"]))

        # Non-matching original outcomes should appear unchanged in result
        for _, row in roll_df.iterrows():
            if not evaluate_face_condition(face_condition, row["value"]):
                match = result[result["value"] == row["value"]]
                assert len(match) > 0, (
                    f"Non-matching outcome '{row['value']}' missing from result"
                )
                for stat in ("damage", "crit", "acc", "blank"):
                    assert match.iloc[0][stat] == row[stat], (
                        f"Non-matching outcome '{row['value']}' stat '{stat}' changed"
                    )

        # Probability integrity
        total_proba = result["proba"].sum()
        assert abs(total_proba - 1.0) < 1e-9, (
            f"Probability sum = {total_proba}, expected 1.0"
        )

    test_prop5b_conditional_add_dice()
except Exception as e:
    prop5_pass = False
    prop5_error = str(e)

if prop5_pass:
    print("PASS: Property 5 — Conditional add applies only to matching outcomes")
    passed += 1
else:
    print(f"FAIL: Property 5 — {prop5_error}")
    failed += 1
    errors.append(("Property 5", prop5_error))


# ---------------------------------------------------------------------------
# Property 7: Color selection follows priority order
# Feature: add-set-die-and-pool-color, Property 7: Color selection follows priority order
# **Validates: Requirements 8.1, 8.2**
# ---------------------------------------------------------------------------

prop7_pass = True
prop7_error = None

try:
    @given(
        priority=color_priority_perms,
        pool_type=pool_types,
        red=st.integers(min_value=0, max_value=2),
        blue=st.integers(min_value=0, max_value=2),
        black=st.integers(min_value=0, max_value=2),
    )
    @settings(max_examples=200, deadline=None)
    def test_prop7_color_selection_follows_priority(priority, pool_type, red, blue, black):
        """For any value string containing at least one die token and any valid
        color priority list, select_color_from_pool returns the first color in
        the priority list whose prefix appears as a token prefix in the value string."""
        assume(red + blue + black >= 1)

        roll_df = combine_dice(red, blue, black, pool_type)

        for _, row in roll_df.iterrows():
            value_str = row["value"]
            tokens = value_str.split(" ")

            # Determine which colors are present in this outcome
            colors_present = set()
            for token in tokens:
                for color, prefix in COLOR_PREFIXES.items():
                    if token.startswith(prefix + "_"):
                        colors_present.add(color)

            # The expected result is the first color in priority that is present
            expected_color = None
            for color in priority:
                if color in colors_present:
                    expected_color = color
                    break

            # If no color is present (shouldn't happen with valid pool), fallback
            if expected_color is None:
                expected_color = priority[0]

            actual_color = select_color_from_pool(priority, value_str)
            assert actual_color == expected_color, (
                f"select_color_from_pool({priority}, {value_str!r}) = {actual_color!r}, "
                f"expected {expected_color!r} (colors present: {colors_present})"
            )

    test_prop7_color_selection_follows_priority()
except Exception as e:
    prop7_pass = False
    prop7_error = str(e)

if prop7_pass:
    print("PASS: Property 7 — Color selection follows priority order")
    passed += 1
else:
    print(f"FAIL: Property 7 — {prop7_error}")
    failed += 1
    errors.append(("Property 7", prop7_error))


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
if failed == 0:
    print("ALL PROPERTY TESTS PASSED")
else:
    print("SOME PROPERTY TESTS FAILED")
    for name, err in errors:
        print(f"  {name}: {err}")
