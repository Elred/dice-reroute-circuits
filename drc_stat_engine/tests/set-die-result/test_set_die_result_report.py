"""
Unit tests for report.py changes for set-die-result feature.
Feature: set-die-result
"""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.dice_models import (
    VALID_ATTACK_EFFECT_TYPES,
    AttackEffect, validate_attack_effect_pipeline, DicePool,
)
from drc_stat_engine.stats.strategies import (
    PRIORITY_DEPENDENT_OPS,
    build_strategy_pipeline, STRATEGY_PRIORITY_LISTS,
)
from drc_stat_engine.stats.report_engine import apply_attack_effect
from drc_stat_engine.stats.dice_maths_combinatories import combine_dice

PASS = "PASS"
FAIL = "FAIL"

def run(name, fn):
    try:
        fn()
        print(f"{PASS}: {name}")
    except Exception as e:
        print(f"{FAIL}: {name} — {e}")


# ---------------------------------------------------------------------------
# Test 1: VALID_ATTACK_EFFECT_TYPES contains "set_die"
# ---------------------------------------------------------------------------
def test_valid_types_contains_set_die():
    assert "set_die" in VALID_ATTACK_EFFECT_TYPES, (
        f"'set_die' not in VALID_ATTACK_EFFECT_TYPES: {VALID_ATTACK_EFFECT_TYPES}"
    )


# ---------------------------------------------------------------------------
# Test 2: PRIORITY_DEPENDENT_OPS contains "set_die"
# ---------------------------------------------------------------------------
def test_priority_dependent_ops_contains_set_die():
    assert "set_die" in PRIORITY_DEPENDENT_OPS, (
        f"'set_die' not in PRIORITY_DEPENDENT_OPS: {PRIORITY_DEPENDENT_OPS}"
    )


# ---------------------------------------------------------------------------
# Test 3: validate_attack_effect_pipeline raises on missing target_result
# ---------------------------------------------------------------------------
def test_validate_raises_on_missing_target_result():
    pool = DicePool(red=1, blue=0, black=0, type="ship")
    pipeline = [AttackEffect(type="set_die", applicable_results=["R_blank"], target_result=None)]
    try:
        validate_attack_effect_pipeline(pipeline, pool)
        print(f"{FAIL}: test_validate_raises_on_missing_target_result — expected ValueError")
    except ValueError as e:
        assert "target_result" in str(e).lower() or "set_die" in str(e).lower(), (
            f"ValueError message doesn't mention target_result or set_die: {e}"
        )
        print(f"{PASS}: validate_attack_effect_pipeline raises on missing target_result")
    return  # skip the run() wrapper for this one


# ---------------------------------------------------------------------------
# Test 4: validate_attack_effect_pipeline does NOT raise for valid set_die
# ---------------------------------------------------------------------------
def test_validate_ok_for_valid_set_die():
    pool = DicePool(red=1, blue=0, black=0, type="ship")
    pipeline = [AttackEffect(type="set_die", applicable_results=["R_blank"], target_result="R_hit")]
    validate_attack_effect_pipeline(pipeline, pool)  # should not raise


# ---------------------------------------------------------------------------
# Test 5: build_strategy_pipeline preserves target_result
# ---------------------------------------------------------------------------
def test_build_pipeline_preserves_target_result():
    effect = AttackEffect(
        type="set_die",
        applicable_results=["R_blank", "B_blank"],
        target_result="R_hit",
    )
    result = build_strategy_pipeline([effect], "max_damage", "ship")
    assert len(result) == 1
    assert result[0].target_result == "R_hit", (
        f"target_result not preserved: {result[0].target_result}"
    )


# ---------------------------------------------------------------------------
# Test 6: build_strategy_pipeline resolves priority_list for set_die
# ---------------------------------------------------------------------------
def test_build_pipeline_resolves_priority_list():
    effect = AttackEffect(
        type="set_die",
        applicable_results=["R_blank", "B_blank", "R_hit"],
        target_result="R_crit",
    )
    result = build_strategy_pipeline([effect], "max_damage", "ship")
    pl = result[0].priority_list
    # All faces in priority_list must be in applicable_results
    assert all(f in effect.applicable_results for f in pl), (
        f"priority_list contains faces not in applicable_results: {pl}"
    )
    # Must be a subsequence of the set_die ordering
    ordering = STRATEGY_PRIORITY_LISTS["ship"]["max_damage"]["set_die"]
    ordering_indices = {f: i for i, f in enumerate(ordering)}
    pl_in_ordering = [f for f in pl if f in ordering_indices]
    assert pl_in_ordering == sorted(pl_in_ordering, key=lambda f: ordering_indices[f]), (
        f"priority_list is not a subsequence of the strategy ordering: {pl}"
    )


# ---------------------------------------------------------------------------
# Test 7: apply_attack_effect dispatches set_die correctly
# ---------------------------------------------------------------------------
def test_apply_dispatches_set_die():
    roll_df = combine_dice(1, 0, 0, "ship")
    effect = AttackEffect(
        type="set_die",
        applicable_results=["R_blank"],
        priority_list=["R_blank"],
        target_result="R_hit",
    )
    result_df = apply_attack_effect(roll_df, effect, "ship")
    # R_blank should be gone; R_hit proba should be 0.5
    assert "R_blank" not in result_df["value"].values, "R_blank should be replaced"
    r_hit = result_df[result_df["value"] == "R_hit"]
    assert not r_hit.empty
    assert abs(r_hit.iloc[0]["proba"] - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# Test 8: apply_attack_effect returns unchanged df when priority_list is empty
# ---------------------------------------------------------------------------
def test_apply_noop_when_priority_list_empty():
    roll_df = combine_dice(1, 0, 0, "ship")
    effect = AttackEffect(
        type="set_die",
        applicable_results=[],
        priority_list=[],
        target_result="R_hit",
    )
    result_df = apply_attack_effect(roll_df, effect, "ship")
    assert result_df is roll_df, "Should return the same df object when priority_list is empty"


# ---------------------------------------------------------------------------
# Test 9: apply_attack_effect raises when target_result is None
# ---------------------------------------------------------------------------
def test_apply_raises_when_target_result_none():
    roll_df = combine_dice(1, 0, 0, "ship")
    effect = AttackEffect(
        type="set_die",
        applicable_results=["R_blank"],
        priority_list=["R_blank"],
        target_result=None,
    )
    try:
        apply_attack_effect(roll_df, effect, "ship")
        print(f"{FAIL}: test_apply_raises_when_target_result_none — expected ValueError")
    except ValueError as e:
        assert "target_result" in str(e).lower() or "set_die" in str(e).lower(), (
            f"ValueError message doesn't mention target_result or set_die: {e}"
        )
        print(f"{PASS}: apply_attack_effect raises when target_result is None")
    return


if __name__ == "__main__":
    run("VALID_ATTACK_EFFECT_TYPES contains set_die", test_valid_types_contains_set_die)
    run("PRIORITY_DEPENDENT_OPS contains set_die", test_priority_dependent_ops_contains_set_die)
    test_validate_raises_on_missing_target_result()
    run("validate_attack_effect_pipeline ok for valid set_die", test_validate_ok_for_valid_set_die)
    run("build_strategy_pipeline preserves target_result", test_build_pipeline_preserves_target_result)
    run("build_strategy_pipeline resolves priority_list", test_build_pipeline_resolves_priority_list)
    run("apply_attack_effect dispatches set_die correctly", test_apply_dispatches_set_die)
    run("apply_attack_effect noop when priority_list empty", test_apply_noop_when_priority_list_empty)
    test_apply_raises_when_target_result_none()
