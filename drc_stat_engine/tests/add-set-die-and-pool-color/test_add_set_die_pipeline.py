"""Property-based tests for strategy pipeline and formatting (Properties 9, 10, 12).

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
    VALID_FACES_BY_TYPE,
)
from drc_stat_engine.stats.strategies import (
    build_strategy_pipeline,
    STRATEGY_PRIORITY_LISTS,
)
from drc_stat_engine.stats.report_engine import _format_pipeline

# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

all_faces = {
    "ship": sorted(VALID_FACES_BY_TYPE["ship"]),
    "squad": sorted(VALID_FACES_BY_TYPE["squad"]),
}

ship_strategies = sorted(STRATEGY_PRIORITY_LISTS["ship"].keys())
squad_strategies = sorted(STRATEGY_PRIORITY_LISTS["squad"].keys())

# (type_str, strategy) pairs
strategy_pool_pairs = st.one_of(
    st.tuples(st.just("ship"), st.sampled_from(ship_strategies)),
    st.tuples(st.just("squad"), st.sampled_from(squad_strategies)),
)

valid_color_priority = st.permutations(["red", "blue", "black"])

passed = 0
failed = 0
errors = []


# ---------------------------------------------------------------------------
# Property 9: Strategy pipeline resolves color_priority correctly
# Feature: add-set-die-and-pool-color, Property 9: Strategy pipeline resolves color_priority correctly
# **Validates: Requirements 9.1, 9.2, 9.6, 12.3, 12.4**
# ---------------------------------------------------------------------------

prop9_pass = True
prop9_error = None

try:
    @given(
        pair=strategy_pool_pairs,
        user_priority=st.one_of(st.none(), valid_color_priority),
    )
    @settings(max_examples=100)
    def test_prop9_color_priority_resolution(pair, user_priority):
        """When build_strategy_pipeline processes an add_dice effect with
        color_in_pool=True: if the effect has a user-provided color_priority,
        the resolved effect should preserve that list; if the effect has no
        color_priority (None), the resolved effect should have the strategy's
        default color_priority."""
        type_str, strategy = pair
        effect = AttackEffect(
            type="add_dice",
            dice_to_add={"red": 1, "blue": 0, "black": 0},
            color_in_pool=True,
            color_priority=list(user_priority) if user_priority is not None else None,
        )
        resolved = build_strategy_pipeline([effect], strategy, type_str)
        assert len(resolved) == 1, f"Expected 1 resolved effect, got {len(resolved)}"
        resolved_op = resolved[0]

        if user_priority is not None:
            # User-provided priority should be preserved
            assert resolved_op.color_priority == list(user_priority), (
                f"Expected user priority {user_priority}, got {resolved_op.color_priority}"
            )
        else:
            # Should resolve from strategy default
            expected = STRATEGY_PRIORITY_LISTS[type_str][strategy]["color_priority"]
            assert resolved_op.color_priority == expected, (
                f"Expected strategy default {expected}, got {resolved_op.color_priority}"
            )

        # color_in_pool should always be preserved
        assert resolved_op.color_in_pool is True, (
            f"Expected color_in_pool=True, got {resolved_op.color_in_pool}"
        )

    test_prop9_color_priority_resolution()
except Exception as e:
    prop9_pass = False
    prop9_error = str(e)

if prop9_pass:
    print("PASS: Property 9 — Strategy pipeline resolves color_priority correctly")
    passed += 1
else:
    print(f"FAIL: Property 9 — {prop9_error}")
    failed += 1
    errors.append(("Property 9", prop9_error))


# ---------------------------------------------------------------------------
# Property 10: Strategy pipeline preserves add_set_die and face_condition
# Feature: add-set-die-and-pool-color, Property 10: Strategy pipeline preserves add_set_die and face_condition
# **Validates: Requirements 12.1, 12.2**
# ---------------------------------------------------------------------------

prop10_pass = True
prop10_error = None

# Sub-test 10a: add_set_die target_result and face_condition preserved
try:
    @given(
        pair=strategy_pool_pairs,
        face_cond=st.one_of(st.none(), st.sampled_from(["R_hit", "U_acc", "B_blank"])),
    )
    @settings(max_examples=100)
    def test_prop10a_add_set_die_preserved(pair, face_cond):
        """For any strategy and pool type, when build_strategy_pipeline processes
        an add_set_die effect, the resolved effect should have target_result and
        face_condition fields identical to the input."""
        type_str, strategy = pair
        # Pick a valid face for this pool type
        face = sorted(VALID_FACES_BY_TYPE[type_str])[0]
        effect = AttackEffect(
            type="add_set_die",
            target_result=face,
            face_condition=face_cond,
        )
        resolved = build_strategy_pipeline([effect], strategy, type_str)
        assert len(resolved) == 1
        resolved_op = resolved[0]
        assert resolved_op.type == "add_set_die", (
            f"Expected type 'add_set_die', got '{resolved_op.type}'"
        )
        assert resolved_op.target_result == face, (
            f"Expected target_result '{face}', got '{resolved_op.target_result}'"
        )
        assert resolved_op.face_condition == face_cond, (
            f"Expected face_condition '{face_cond}', got '{resolved_op.face_condition}'"
        )

    test_prop10a_add_set_die_preserved()
except Exception as e:
    prop10_pass = False
    prop10_error = str(e)

# Sub-test 10b: add_dice face_condition preserved
try:
    @given(
        pair=strategy_pool_pairs,
        face_cond=st.sampled_from(["R_hit", "U_acc", "B_blank", "R_crit"]),
    )
    @settings(max_examples=100)
    def test_prop10b_add_dice_face_condition_preserved(pair, face_cond):
        """For any strategy and pool type, when build_strategy_pipeline processes
        an add_dice effect with a face_condition, the resolved effect should have
        face_condition identical to the input."""
        type_str, strategy = pair
        effect = AttackEffect(
            type="add_dice",
            dice_to_add={"red": 1, "blue": 0, "black": 0},
            face_condition=face_cond,
        )
        resolved = build_strategy_pipeline([effect], strategy, type_str)
        assert len(resolved) == 1
        resolved_op = resolved[0]
        assert resolved_op.face_condition == face_cond, (
            f"Expected face_condition '{face_cond}', got '{resolved_op.face_condition}'"
        )

    test_prop10b_add_dice_face_condition_preserved()
except Exception as e:
    prop10_pass = False
    prop10_error = str(e)

if prop10_pass:
    print("PASS: Property 10 — Strategy pipeline preserves add_set_die and face_condition")
    passed += 1
else:
    print(f"FAIL: Property 10 — {prop10_error}")
    failed += 1
    errors.append(("Property 10", prop10_error))


# ---------------------------------------------------------------------------
# Property 12: Format pipeline output contains expected substrings
# Feature: add-set-die-and-pool-color, Property 12: Format pipeline output contains expected substrings
# **Validates: Requirements 15.1, 15.2, 15.3**
# ---------------------------------------------------------------------------

prop12_pass = True
prop12_error = None

# Sub-test 12a: add_set_die formatting
try:
    @given(
        type_str=st.sampled_from(["ship", "squad"]),
    )
    @settings(max_examples=100)
    def test_prop12a_add_set_die_format(type_str):
        """For any pipeline containing an add_set_die effect, _format_pipeline
        should produce a string containing 'add_set_die [{target_result}]'."""
        face = sorted(VALID_FACES_BY_TYPE[type_str])[0]
        pipeline = [AttackEffect(type="add_set_die", target_result=face)]
        output = _format_pipeline(pipeline)
        expected_substr = f"add_set_die [{face}]"
        assert expected_substr in output, (
            f"Expected '{expected_substr}' in output '{output}'"
        )

    test_prop12a_add_set_die_format()
except Exception as e:
    prop12_pass = False
    prop12_error = str(e)

# Sub-test 12b: face_condition formatting
try:
    @given(
        face_cond=st.sampled_from(["R_hit", "U_acc", "B_blank", "R_crit", "B_hit+crit"]),
    )
    @settings(max_examples=100)
    def test_prop12b_face_condition_format(face_cond):
        """For any effect with a face_condition, the output should contain
        'if {face} present'."""
        # Test on add_set_die with face_condition
        pipeline_set = [AttackEffect(
            type="add_set_die", target_result="R_hit", face_condition=face_cond,
        )]
        output_set = _format_pipeline(pipeline_set)
        expected = f"if {face_cond} present"
        assert expected in output_set, (
            f"Expected '{expected}' in output '{output_set}'"
        )

        # Test on add_dice with face_condition
        pipeline_add = [AttackEffect(
            type="add_dice",
            dice_to_add={"red": 1, "blue": 0, "black": 0},
            face_condition=face_cond,
        )]
        output_add = _format_pipeline(pipeline_add)
        assert expected in output_add, (
            f"Expected '{expected}' in output '{output_add}'"
        )

    test_prop12b_face_condition_format()
except Exception as e:
    prop12_pass = False
    prop12_error = str(e)

# Sub-test 12c: color_in_pool formatting
try:
    @given(priority=valid_color_priority)
    @settings(max_examples=100)
    def test_prop12c_color_in_pool_format(priority):
        """For any add_dice with color_in_pool=True, the output should contain
        'color_in_pool'."""
        pipeline = [AttackEffect(
            type="add_dice",
            dice_to_add={"red": 1, "blue": 0, "black": 0},
            color_in_pool=True,
            color_priority=list(priority),
        )]
        output = _format_pipeline(pipeline)
        assert "color_in_pool" in output, (
            f"Expected 'color_in_pool' in output '{output}'"
        )

    test_prop12c_color_in_pool_format()
except Exception as e:
    prop12_pass = False
    prop12_error = str(e)

if prop12_pass:
    print("PASS: Property 12 — Format pipeline output contains expected substrings")
    passed += 1
else:
    print(f"FAIL: Property 12 — {prop12_error}")
    failed += 1
    errors.append(("Property 12", prop12_error))


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
