"""Property-based tests for MC/combinatorial agreement (Property 6).

Uses Hypothesis for property-based testing. Each property test is tagged with
a comment referencing the design property it validates.

**Validates: Requirements 3.1, 5.7, 8.5, 11.1**
"""
import sys
sys.path.insert(0, '.')

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from drc_stat_engine.stats.dice_maths_combinatories import (
    add_set_die_to_roll as comb_add_set_die,
    combine_dice as comb_combine_dice,
    conditional_add_partition as comb_conditional_add_partition,
    add_dice_to_roll as comb_add_dice,
    color_in_pool_add as comb_color_in_pool_add,
)
from drc_stat_engine.stats.dice_monte_carlo import (
    add_set_die_to_roll as mc_add_set_die,
    combine_dice as mc_combine_dice,
    conditional_add_set_die_mc,
    conditional_add_dice_mc,
    color_in_pool_add_mc,
)
from drc_stat_engine.stats.dice_models import VALID_FACES_BY_TYPE, COLOR_PREFIXES

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MC_SAMPLE_COUNT = 50_000
TOLERANCE = 0.15  # tolerance for average damage agreement

pool_types = st.sampled_from(["ship", "squad"])

all_faces = {
    "ship": sorted(VALID_FACES_BY_TYPE["ship"]),
    "squad": sorted(VALID_FACES_BY_TYPE["squad"]),
}

# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

@st.composite
def small_pool_and_face(draw):
    """Generate a small dice pool (0-2 of each color, at least 1 die total, ≤4 total)
    and a valid face string for that pool type."""
    type_str = draw(pool_types)
    red = draw(st.integers(min_value=0, max_value=2))
    blue = draw(st.integers(min_value=0, max_value=2))
    black = draw(st.integers(min_value=0, max_value=2))
    assume(1 <= red + blue + black <= 4)
    face = draw(st.sampled_from(all_faces[type_str]))
    return type_str, red, blue, black, face



@st.composite
def small_pool_and_face_condition_and_target(draw):
    """Generate a small dice pool, a face_condition, and a target_result for
    conditional add_set_die."""
    type_str = draw(pool_types)
    red = draw(st.integers(min_value=0, max_value=2))
    blue = draw(st.integers(min_value=0, max_value=2))
    black = draw(st.integers(min_value=0, max_value=2))
    assume(1 <= red + blue + black <= 4)
    face_condition = draw(st.sampled_from(all_faces[type_str]))
    target_result = draw(st.sampled_from(all_faces[type_str]))
    return type_str, red, blue, black, face_condition, target_result


@st.composite
def small_pool_and_face_condition_and_add_color(draw):
    """Generate a small dice pool, a face_condition, and a color to add for
    conditional add_dice."""
    type_str = draw(pool_types)
    red = draw(st.integers(min_value=0, max_value=2))
    blue = draw(st.integers(min_value=0, max_value=2))
    black = draw(st.integers(min_value=0, max_value=2))
    assume(1 <= red + blue + black <= 4)
    face_condition = draw(st.sampled_from(all_faces[type_str]))
    add_color = draw(st.sampled_from(["red", "blue", "black"]))
    return type_str, red, blue, black, face_condition, add_color


@st.composite
def small_pool_and_color_priority(draw):
    """Generate a small dice pool and a color priority permutation for
    color_in_pool testing."""
    type_str = draw(pool_types)
    red = draw(st.integers(min_value=0, max_value=2))
    blue = draw(st.integers(min_value=0, max_value=2))
    black = draw(st.integers(min_value=0, max_value=2))
    assume(1 <= red + blue + black <= 4)
    # Ensure at least 2 colors present so color_in_pool is meaningful
    colors_present = (1 if red > 0 else 0) + (1 if blue > 0 else 0) + (1 if black > 0 else 0)
    assume(colors_present >= 2)
    color_priority = draw(st.permutations(["red", "blue", "black"]))
    return type_str, red, blue, black, color_priority


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def avg_damage(roll_df):
    """Compute expected damage from a Roll_DataFrame."""
    return (roll_df["damage"] * roll_df["proba"]).sum()


passed = 0
failed = 0
errors = []


# ---------------------------------------------------------------------------
# Property 6a: MC and combinatorial agree on unconditional add_set_die
# Feature: add-set-die-and-pool-color, Property 6: MC and combinatorial backends agree on add_set_die and conditional operations
# **Validates: Requirements 3.1**
# ---------------------------------------------------------------------------

prop6a_pass = True
prop6a_error = None

try:
    @given(data=small_pool_and_face())
    @settings(max_examples=100, deadline=None)
    def test_prop6a_mc_comb_agree_unconditional_add_set_die(data):
        """For any small dice pool and valid face, the average damage from MC
        add_set_die should be within tolerance of the combinatorial result."""
        type_str, red, blue, black, face = data

        # Combinatorial path
        comb_roll = comb_combine_dice(red, blue, black, type_str)
        comb_result = comb_add_set_die(comb_roll, face, type_str)
        comb_avg = avg_damage(comb_result)

        # MC path
        mc_roll = mc_combine_dice(red, blue, black, type_str, sample_count=MC_SAMPLE_COUNT)
        mc_result = mc_add_set_die(mc_roll, face, type_str)
        mc_avg = avg_damage(mc_result)

        diff = abs(comb_avg - mc_avg)
        assert diff < TOLERANCE, (
            f"MC/comb avg damage disagree: comb={comb_avg:.4f}, mc={mc_avg:.4f}, "
            f"diff={diff:.4f} > tol={TOLERANCE} "
            f"(pool: {red}R {blue}U {black}B {type_str}, face: {face})"
        )

    test_prop6a_mc_comb_agree_unconditional_add_set_die()
except Exception as e:
    prop6a_pass = False
    prop6a_error = str(e)

if prop6a_pass:
    print("PASS: Property 6a — MC and combinatorial agree on unconditional add_set_die")
    passed += 1
else:
    print(f"FAIL: Property 6a — {prop6a_error}")
    failed += 1
    errors.append(("Property 6a", prop6a_error))


# ---------------------------------------------------------------------------
# Property 6b: MC and combinatorial agree on conditional add_set_die (with face_condition)
# Feature: add-set-die-and-pool-color, Property 6: MC and combinatorial backends agree on add_set_die and conditional operations
# **Validates: Requirements 5.7**
# ---------------------------------------------------------------------------

prop6b_pass = True
prop6b_error = None

try:
    @given(data=small_pool_and_face_condition_and_target())
    @settings(max_examples=100, deadline=None)
    def test_prop6b_mc_comb_agree_conditional_add_set_die(data):
        """For any small dice pool, face_condition, and target_result, the average
        damage from MC conditional_add_set_die should be within tolerance of the
        combinatorial conditional_add_partition result."""
        type_str, red, blue, black, face_condition, target_result = data

        # Combinatorial path
        comb_roll = comb_combine_dice(red, blue, black, type_str)
        comb_result = comb_conditional_add_partition(
            comb_roll, face_condition, comb_add_set_die,
            target_result=target_result, type_str=type_str,
        )
        comb_avg = avg_damage(comb_result)

        # MC path
        mc_roll = mc_combine_dice(red, blue, black, type_str, sample_count=MC_SAMPLE_COUNT)
        mc_result = conditional_add_set_die_mc(
            mc_roll, face_condition, target_result, type_str,
        )
        mc_avg = avg_damage(mc_result)

        diff = abs(comb_avg - mc_avg)
        assert diff < TOLERANCE, (
            f"MC/comb avg damage disagree on conditional add_set_die: "
            f"comb={comb_avg:.4f}, mc={mc_avg:.4f}, diff={diff:.4f} > tol={TOLERANCE} "
            f"(pool: {red}R {blue}U {black}B {type_str}, "
            f"face_condition: {face_condition}, target: {target_result})"
        )

    test_prop6b_mc_comb_agree_conditional_add_set_die()
except Exception as e:
    prop6b_pass = False
    prop6b_error = str(e)

if prop6b_pass:
    print("PASS: Property 6b — MC and combinatorial agree on conditional add_set_die")
    passed += 1
else:
    print(f"FAIL: Property 6b — {prop6b_error}")
    failed += 1
    errors.append(("Property 6b", prop6b_error))


# ---------------------------------------------------------------------------
# Property 6c: MC and combinatorial agree on color_in_pool add_dice
# Feature: add-set-die-and-pool-color, Property 6: MC and combinatorial backends agree on add_set_die and conditional operations
# **Validates: Requirements 8.5, 11.1**
# ---------------------------------------------------------------------------

prop6c_pass = True
prop6c_error = None

try:
    @given(data=small_pool_and_color_priority())
    @settings(max_examples=100, deadline=None)
    def test_prop6c_mc_comb_agree_color_in_pool(data):
        """For any small dice pool and color priority, the average damage from MC
        color_in_pool_add should be within tolerance of the combinatorial result."""
        type_str, red, blue, black, color_priority = data

        # Combinatorial path
        comb_roll = comb_combine_dice(red, blue, black, type_str)
        comb_result = comb_color_in_pool_add(comb_roll, color_priority, type_str)
        comb_avg = avg_damage(comb_result)

        # MC path
        mc_roll = mc_combine_dice(red, blue, black, type_str, sample_count=MC_SAMPLE_COUNT)
        mc_result = color_in_pool_add_mc(mc_roll, color_priority, type_str)
        mc_avg = avg_damage(mc_result)

        diff = abs(comb_avg - mc_avg)
        assert diff < TOLERANCE, (
            f"MC/comb avg damage disagree on color_in_pool: "
            f"comb={comb_avg:.4f}, mc={mc_avg:.4f}, diff={diff:.4f} > tol={TOLERANCE} "
            f"(pool: {red}R {blue}U {black}B {type_str}, priority: {color_priority})"
        )

    test_prop6c_mc_comb_agree_color_in_pool()
except Exception as e:
    prop6c_pass = False
    prop6c_error = str(e)

if prop6c_pass:
    print("PASS: Property 6c — MC and combinatorial agree on color_in_pool add_dice")
    passed += 1
else:
    print(f"FAIL: Property 6c — {prop6c_error}")
    failed += 1
    errors.append(("Property 6c", prop6c_error))


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
