"""Property-based tests for add_set_die model validation (Properties 1, 8, 11, 13).

Uses Hypothesis for property-based testing. Each property test is tagged with
a comment referencing the design property it validates.
"""
import sys
sys.path.insert(0, '.')

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from drc_stat_engine.stats.dice_models import (
    AttackEffect,
    DicePool,
    validate_attack_effect_pipeline,
    VALID_FACES_BY_TYPE,
    VALID_ATTACK_EFFECT_TYPES,
    MAX_DICE,
)

# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

all_faces = {
    "ship": sorted(VALID_FACES_BY_TYPE["ship"]),
    "squad": sorted(VALID_FACES_BY_TYPE["squad"]),
}
all_valid_faces = set(all_faces["ship"]) | set(all_faces["squad"])

pool_types = st.sampled_from(["ship", "squad"])

valid_face_for_type = st.one_of(
    st.tuples(st.just("ship"), st.sampled_from(all_faces["ship"])),
    st.tuples(st.just("squad"), st.sampled_from(all_faces["squad"])),
)

invalid_face_strings = st.text(min_size=1).filter(lambda s: s not in all_valid_faces)

valid_color_priority = st.permutations(["red", "blue", "black"])

invalid_color_priority = st.lists(st.text(), min_size=0, max_size=5).filter(
    lambda l: sorted(l) != ["black", "blue", "red"]
)

# Types that should NOT have face_condition or color_in_pool
non_add_types = ["reroll", "cancel", "change_die", "reroll_all"]

passed = 0
failed = 0
errors = []

# ---------------------------------------------------------------------------
# Property 1: add_set_die validation accepts valid faces and rejects invalid ones
# Feature: add-set-die-and-pool-color, Property 1: add_set_die validation accepts valid faces and rejects invalid ones
# **Validates: Requirements 1.2, 1.3, 1.4, 14.1, 14.2**
# ---------------------------------------------------------------------------

prop1_pass = True
prop1_error = None

try:
    @given(data=valid_face_for_type)
    @settings(max_examples=100)
    def test_prop1_valid_faces_accepted(data):
        """Valid face strings for the pool type should pass validation."""
        type_str, face = data
        pool = DicePool(red=1, blue=0, black=0, type=type_str)
        pipeline = [AttackEffect(type="add_set_die", target_result=face)]
        # Should not raise
        validate_attack_effect_pipeline(pipeline, pool)

    test_prop1_valid_faces_accepted()
except Exception as e:
    prop1_pass = False
    prop1_error = str(e)

try:
    @given(face=invalid_face_strings, type_str=pool_types)
    @settings(max_examples=100)
    def test_prop1_invalid_faces_rejected(face, type_str):
        """Invalid face strings should raise ValueError."""
        pool = DicePool(red=1, blue=0, black=0, type=type_str)
        pipeline = [AttackEffect(type="add_set_die", target_result=face)]
        try:
            validate_attack_effect_pipeline(pipeline, pool)
            raise AssertionError(f"Expected ValueError for face '{face}' on type '{type_str}'")
        except ValueError:
            pass  # Expected

    test_prop1_invalid_faces_rejected()
except Exception as e:
    prop1_pass = False
    prop1_error = str(e)

try:
    @given(type_str=pool_types)
    @settings(max_examples=100)
    def test_prop1_none_target_rejected(type_str):
        """None target_result should raise ValueError."""
        pool = DicePool(red=1, blue=0, black=0, type=type_str)
        pipeline = [AttackEffect(type="add_set_die", target_result=None)]
        try:
            validate_attack_effect_pipeline(pipeline, pool)
            raise AssertionError("Expected ValueError for target_result=None")
        except ValueError:
            pass  # Expected

    test_prop1_none_target_rejected()
except Exception as e:
    prop1_pass = False
    prop1_error = str(e)

if prop1_pass:
    print("PASS: Property 1 — add_set_die validation accepts valid faces and rejects invalid ones")
    passed += 1
else:
    print(f"FAIL: Property 1 — {prop1_error}")
    failed += 1
    errors.append(("Property 1", prop1_error))


# ---------------------------------------------------------------------------
# Property 8: Invalid color_priority rejected
# Feature: add-set-die-and-pool-color, Property 8: Invalid color_priority rejected
# **Validates: Requirements 8.3, 9.4, 9.5, 14.3**
# ---------------------------------------------------------------------------

prop8_pass = True
prop8_error = None

try:
    @given(bad_priority=invalid_color_priority)
    @settings(max_examples=100)
    def test_prop8_invalid_color_priority_rejected(bad_priority):
        """Any list that is not a valid permutation of ["red", "blue", "black"]
        should raise ValueError when used as color_priority on add_dice with color_in_pool=True."""
        pool = DicePool(red=1, blue=0, black=0, type="ship")
        pipeline = [AttackEffect(
            type="add_dice",
            dice_to_add={"red": 1, "blue": 0, "black": 0},
            color_in_pool=True,
            color_priority=bad_priority,
        )]
        try:
            validate_attack_effect_pipeline(pipeline, pool)
            raise AssertionError(
                f"Expected ValueError for invalid color_priority {bad_priority}"
            )
        except ValueError:
            pass  # Expected

    test_prop8_invalid_color_priority_rejected()
except Exception as e:
    prop8_pass = False
    prop8_error = str(e)

try:
    @given(good_priority=valid_color_priority)
    @settings(max_examples=100)
    def test_prop8_valid_color_priority_accepted(good_priority):
        """Valid permutations of ["red", "blue", "black"] should pass validation."""
        pool = DicePool(red=1, blue=0, black=0, type="ship")
        pipeline = [AttackEffect(
            type="add_dice",
            dice_to_add={"red": 1, "blue": 0, "black": 0},
            color_in_pool=True,
            color_priority=good_priority,
        )]
        validate_attack_effect_pipeline(pipeline, pool)

    test_prop8_valid_color_priority_accepted()
except Exception as e:
    prop8_pass = False
    prop8_error = str(e)

if prop8_pass:
    print("PASS: Property 8 — Invalid color_priority rejected")
    passed += 1
else:
    print(f"FAIL: Property 8 — {prop8_error}")
    failed += 1
    errors.append(("Property 8", prop8_error))


# ---------------------------------------------------------------------------
# Property 11: Validation rejects face_condition and color_in_pool on wrong operation types
# Feature: add-set-die-and-pool-color, Property 11: Validation rejects face_condition and color_in_pool on wrong operation types
# **Validates: Requirements 14.4, 14.5**
# ---------------------------------------------------------------------------

prop11_pass = True
prop11_error = None

# We need to build valid effects for each non-add type so validation doesn't
# fail for unrelated reasons (e.g. missing condition on reroll_all).
from drc_stat_engine.stats.dice_models import Condition

def _make_base_effect(op_type):
    """Create a minimally valid AttackEffect for the given type."""
    if op_type == "change_die":
        return AttackEffect(type=op_type, target_result="R_hit")
    elif op_type == "reroll_all":
        return AttackEffect(type=op_type, condition=Condition(attribute="damage", operator="lte", threshold=2))
    else:
        return AttackEffect(type=op_type)

try:
    @given(op_type=st.sampled_from(non_add_types))
    @settings(max_examples=100)
    def test_prop11_face_condition_rejected_on_wrong_types(op_type):
        """face_condition on reroll, cancel, change_die, or reroll_all should raise ValueError."""
        pool = DicePool(red=1, blue=0, black=0, type="ship")
        effect = _make_base_effect(op_type)
        effect.face_condition = "R_hit"
        try:
            validate_attack_effect_pipeline([effect], pool)
            raise AssertionError(
                f"Expected ValueError for face_condition on '{op_type}'"
            )
        except ValueError as e:
            assert "face_condition" in str(e), f"Unexpected error message: {e}"

    test_prop11_face_condition_rejected_on_wrong_types()
except Exception as e:
    prop11_pass = False
    prop11_error = str(e)

# color_in_pool on any type other than add_dice should raise ValueError
non_add_dice_types = ["reroll", "cancel", "change_die", "reroll_all", "add_set_die"]

try:
    @given(op_type=st.sampled_from(non_add_dice_types))
    @settings(max_examples=100)
    def test_prop11_color_in_pool_rejected_on_wrong_types(op_type):
        """color_in_pool=True on any type other than add_dice should raise ValueError."""
        pool = DicePool(red=1, blue=0, black=0, type="ship")
        if op_type == "add_set_die":
            effect = AttackEffect(type=op_type, target_result="R_hit", color_in_pool=True)
        elif op_type == "change_die":
            effect = AttackEffect(type=op_type, target_result="R_hit", color_in_pool=True)
        elif op_type == "reroll_all":
            effect = AttackEffect(
                type=op_type,
                condition=Condition(attribute="damage", operator="lte", threshold=2),
                color_in_pool=True,
            )
        else:
            effect = AttackEffect(type=op_type, color_in_pool=True)
        try:
            validate_attack_effect_pipeline([effect], pool)
            raise AssertionError(
                f"Expected ValueError for color_in_pool on '{op_type}'"
            )
        except ValueError as e:
            assert "color_in_pool" in str(e), f"Unexpected error message: {e}"

    test_prop11_color_in_pool_rejected_on_wrong_types()
except Exception as e:
    prop11_pass = False
    prop11_error = str(e)

# Positive: face_condition on add_dice and add_set_die should pass
try:
    @given(type_str=pool_types)
    @settings(max_examples=100)
    def test_prop11_face_condition_accepted_on_correct_types(type_str):
        """face_condition on add_dice and add_set_die should pass validation."""
        pool = DicePool(red=1, blue=0, black=0, type=type_str)
        # add_dice with face_condition
        validate_attack_effect_pipeline(
            [AttackEffect(type="add_dice", dice_to_add={"red": 1, "blue": 0, "black": 0},
                          face_condition="R_hit")],
            pool,
        )
        # add_set_die with face_condition
        face = sorted(VALID_FACES_BY_TYPE[type_str])[0]
        validate_attack_effect_pipeline(
            [AttackEffect(type="add_set_die", target_result=face, face_condition="R_hit")],
            pool,
        )

    test_prop11_face_condition_accepted_on_correct_types()
except Exception as e:
    prop11_pass = False
    prop11_error = str(e)

if prop11_pass:
    print("PASS: Property 11 — Validation rejects face_condition and color_in_pool on wrong operation types")
    passed += 1
else:
    print(f"FAIL: Property 11 — {prop11_error}")
    failed += 1
    errors.append(("Property 11", prop11_error))


# ---------------------------------------------------------------------------
# Property 13: MAX_DICE enforcement for add_set_die
# Feature: add-set-die-and-pool-color, Property 13: MAX_DICE enforcement for add_set_die
# **Validates: Requirements 1.6, 2.5**
# ---------------------------------------------------------------------------

prop13_pass = True
prop13_error = None

try:
    @given(
        base_red=st.integers(min_value=1, max_value=MAX_DICE - 1),
        num_add_set_die=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=100)
    def test_prop13_max_dice_enforcement(base_red, num_add_set_die):
        """Pipelines that would exceed MAX_DICE should raise ValueError;
        pipelines that stay within the limit should pass."""
        # Clamp base_red so pool is valid (1..MAX_DICE)
        base_red = min(base_red, MAX_DICE)
        pool = DicePool(red=base_red, blue=0, black=0, type="ship")
        total_after = base_red + num_add_set_die
        pipeline = [
            AttackEffect(type="add_set_die", target_result="R_hit")
            for _ in range(num_add_set_die)
        ]
        if total_after > MAX_DICE:
            try:
                validate_attack_effect_pipeline(pipeline, pool)
                raise AssertionError(
                    f"Expected ValueError: base={base_red} + add={num_add_set_die} = {total_after} > {MAX_DICE}"
                )
            except ValueError:
                pass  # Expected
        else:
            # Should pass without error
            validate_attack_effect_pipeline(pipeline, pool)

    test_prop13_max_dice_enforcement()
except Exception as e:
    prop13_pass = False
    prop13_error = str(e)

if prop13_pass:
    print("PASS: Property 13 — MAX_DICE enforcement for add_set_die")
    passed += 1
else:
    print(f"FAIL: Property 13 — {prop13_error}")
    failed += 1
    errors.append(("Property 13", prop13_error))

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
