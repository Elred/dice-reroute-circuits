"""
Property and unit tests for reroll_all pipeline integration.

Properties tested:
  8. Strategy pipeline resolves reroll_all correctly
  9. Validation rejects invalid reroll_all effects

Validates: Requirements 6.1, 6.2, 6.3, 8.1, 8.2
"""
import sys
sys.path.insert(0, '.')

from hypothesis import given, settings
from hypothesis import strategies as st

from drc_stat_engine.stats.dice_models import (
    AttackEffect,
    Condition,
    DicePool,
    validate_attack_effect_pipeline,
    VALID_CONDITION_ATTRIBUTES,
    VALID_CONDITION_OPERATORS,
)
from drc_stat_engine.stats.strategies import (
    build_strategy_pipeline,
    ALL_FACES,
    STRATEGY_PRIORITY_LISTS,
)
from drc_stat_engine.stats.dice_models import VALID_ATTACK_EFFECT_TYPES
from drc_stat_engine.stats.strategies import PRIORITY_DEPENDENT_OPS
from drc_stat_engine.stats.report_engine import (
    _format_pipeline,
    apply_attack_effect,
    generate_report,
)
from drc_stat_engine.stats.dice_maths_combinatories import combine_dice, reroll_all_dice
import pandas as pd

# ---------------------------------------------------------------------------
# Feature: conditional-reroll-all, Property 8: Strategy pipeline resolves
#          reroll_all correctly
# ---------------------------------------------------------------------------

@given(
    type_str=st.sampled_from(["ship", "squad"]),
    attr=st.sampled_from(["damage", "crit", "acc", "blank"]),
    op=st.sampled_from(["lte", "lt", "gte", "gt", "eq", "neq"]),
    thresh=st.integers(min_value=0, max_value=10),
)
@settings(max_examples=100, deadline=None)
def test_property_8_strategy_pipeline_resolves_reroll_all(type_str, attr, op, thresh):
    """Validates: Requirements 6.1, 6.2, 6.3"""
    cond = Condition(attribute=attr, operator=op, threshold=thresh)
    pipeline = [AttackEffect(type="reroll_all", condition=cond)]

    # Test with every strategy available for this type
    for strategy in STRATEGY_PRIORITY_LISTS[type_str]:
        resolved = build_strategy_pipeline(pipeline, strategy, type_str)
        assert len(resolved) == 1
        effect = resolved[0]

        expected_faces = ALL_FACES[type_str]
        assert set(effect.applicable_results) == set(expected_faces), (
            f"applicable_results mismatch for {strategy}/{type_str}"
        )
        assert set(effect.priority_list) == set(expected_faces), (
            f"priority_list mismatch for {strategy}/{type_str}"
        )
        assert effect.condition is not None, "condition should be preserved"
        assert effect.condition.attribute == attr
        assert effect.condition.operator == op
        assert effect.condition.threshold == thresh


# ---------------------------------------------------------------------------
# Feature: conditional-reroll-all, Property 9: Validation rejects invalid
#          reroll_all effects
# ---------------------------------------------------------------------------

# 9a: reroll_all with condition=None → ValueError
def test_property_9a_reroll_all_without_condition_rejected():
    """Validates: Requirements 8.1"""
    pool = DicePool(red=1, blue=0, black=0, type="ship")
    pipeline = [AttackEffect(type="reroll_all", condition=None)]
    try:
        validate_attack_effect_pipeline(pipeline, pool)
        print("FAIL: expected ValueError for reroll_all without condition")
        assert False
    except ValueError:
        pass

# 9b: reroll_all with invalid condition attribute → ValueError at Condition construction
@given(attr=st.text(min_size=1).filter(lambda s: s not in VALID_CONDITION_ATTRIBUTES))
@settings(max_examples=100)
def test_property_9b_reroll_all_with_invalid_condition_attribute(attr):
    """Validates: Requirements 8.2"""
    try:
        Condition(attribute=attr, operator="lte", threshold=0)
        assert False, f"Expected ValueError for invalid attribute '{attr}'"
    except ValueError:
        pass

# 9c: reroll_all with invalid condition operator → ValueError at Condition construction
@given(op=st.text(min_size=1).filter(lambda s: s not in VALID_CONDITION_OPERATORS))
@settings(max_examples=100)
def test_property_9c_reroll_all_with_invalid_condition_operator(op):
    """Validates: Requirements 8.2"""
    try:
        Condition(attribute="damage", operator=op, threshold=0)
        assert False, f"Expected ValueError for invalid operator '{op}'"
    except ValueError:
        pass

# 9d: reroll_all with non-integer threshold → ValueError at Condition construction
@given(thresh=st.one_of(st.floats(allow_nan=False, allow_infinity=False), st.text(min_size=1)))
@settings(max_examples=100)
def test_property_9d_reroll_all_with_invalid_condition_threshold(thresh):
    """Validates: Requirements 8.2"""
    try:
        Condition(attribute="damage", operator="lte", threshold=thresh)
        assert False, f"Expected ValueError for non-integer threshold {thresh!r}"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Feature: conditional-reroll-all, Property 10: Format pipeline includes
#          condition details
# ---------------------------------------------------------------------------

@given(
    attr=st.sampled_from(["damage", "crit", "acc", "blank"]),
    op=st.sampled_from(["lte", "lt", "gte", "gt", "eq", "neq"]),
    thresh=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=100)
def test_property_10_format_pipeline_includes_condition(attr, op, thresh):
    """Validates: Requirements 9.1, 9.2"""
    cond = Condition(attribute=attr, operator=op, threshold=thresh)
    pipeline = [AttackEffect(type="reroll_all", condition=cond)]
    output = _format_pipeline(pipeline)
    expected = f"reroll_all [condition: {attr} {op} {thresh}]"
    assert output == expected, f"Expected '{expected}', got '{output}'"


# ---------------------------------------------------------------------------
# Unit tests for pipeline dispatch and end-to-end
# ---------------------------------------------------------------------------

def test_reroll_all_in_valid_types():
    """Validates: Requirement 2.1"""
    assert "reroll_all" in VALID_ATTACK_EFFECT_TYPES, "reroll_all not in VALID_ATTACK_EFFECT_TYPES"

def test_reroll_all_in_priority_dependent_ops():
    """Validates: Requirement 6.3"""
    assert "reroll_all" in PRIORITY_DEPENDENT_OPS, "reroll_all not in PRIORITY_DEPENDENT_OPS"

def test_apply_attack_effect_dispatches_reroll_all():
    """Validates: Requirement 7.1"""
    cond = Condition(attribute="damage", operator="lte", threshold=0)
    effect = AttackEffect(type="reroll_all", condition=cond, priority_list=["R_blank"])
    roll_df = combine_dice(1, 0, 0, "ship")
    result = apply_attack_effect(roll_df, effect, "ship")
    assert isinstance(result, pd.DataFrame), "apply_attack_effect should return a DataFrame"
    assert abs(result["proba"].sum() - 1.0) < 1e-9, "Probabilities should sum to 1.0"

def test_reroll_all_dice_return_type():
    """Validates: Requirement 7.4"""
    cond = Condition(attribute="damage", operator="lte", threshold=0)
    roll_df = combine_dice(1, 0, 0, "ship")
    result = reroll_all_dice(roll_df, condition=cond, type_str="ship")
    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    assert len(result) == 2, f"Expected 2-tuple, got {len(result)}-tuple"
    assert isinstance(result[0], pd.DataFrame), "First element should be DataFrame"
    assert isinstance(result[1], pd.DataFrame), "Second element should be DataFrame"

def test_generate_report_with_reroll_all():
    """End-to-end: generate_report with reroll_all produces valid output."""
    pool = DicePool(red=1, blue=1, black=0, type="ship")
    cond = Condition(attribute="damage", operator="lte", threshold=1)
    pipeline = [AttackEffect(type="reroll_all", condition=cond)]
    variants = generate_report(pool, pipeline, strategies=["max_damage"], backend="combinatorial")
    assert len(variants) == 1, f"Expected 1 variant, got {len(variants)}"
    v = variants[0]
    assert v["label"] == "max_damage"
    assert len(v["damage"]) > 0, "damage distribution should not be empty"
    assert len(v["accuracy"]) > 0, "accuracy distribution should not be empty"
    assert 0.0 <= v["crit"] <= 1.0, f"crit probability out of range: {v['crit']}"
    assert v["avg_damage"] >= 0, f"avg_damage should be non-negative: {v['avg_damage']}"


if __name__ == "__main__":
    test_property_8_strategy_pipeline_resolves_reroll_all()
    print("PASS: Property 8 — Strategy pipeline resolves reroll_all correctly")

    test_property_9a_reroll_all_without_condition_rejected()
    print("PASS: Property 9a — reroll_all without condition rejected")

    test_property_9b_reroll_all_with_invalid_condition_attribute()
    print("PASS: Property 9b — reroll_all with invalid condition attribute rejected")

    test_property_9c_reroll_all_with_invalid_condition_operator()
    print("PASS: Property 9c — reroll_all with invalid condition operator rejected")

    test_property_9d_reroll_all_with_invalid_condition_threshold()
    print("PASS: Property 9d — reroll_all with invalid condition threshold rejected")

    test_property_10_format_pipeline_includes_condition()
    print("PASS: Property 10 — Format pipeline includes condition details")

    test_reroll_all_in_valid_types()
    print("PASS: reroll_all in VALID_ATTACK_EFFECT_TYPES")

    test_reroll_all_in_priority_dependent_ops()
    print("PASS: reroll_all in PRIORITY_DEPENDENT_OPS")

    test_apply_attack_effect_dispatches_reroll_all()
    print("PASS: apply_attack_effect dispatches reroll_all correctly")

    test_reroll_all_dice_return_type()
    print("PASS: reroll_all_dice returns tuple of two DataFrames")

    test_generate_report_with_reroll_all()
    print("PASS: generate_report with reroll_all produces valid output")

    print("\nALL PROPERTY 8, 9, 10 & UNIT TESTS PASSED")
