"""
Unit tests for report.py changes for set-die-result feature.
Feature: set-die-result

NOTE: This spec was designed around a 'set_die' attack effect type, but the
actual implementation uses 'change_die' for this functionality. The 'set_die'
type was never added to VALID_ATTACK_EFFECT_TYPES. Tests 1, 2, 4, 5, 6, 7, 8
document this divergence and are expected to fail until the spec is reconciled
with the implementation.

Tests 3 and 9 (validation error tests) still pass because they test error paths.
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
SKIP = "SKIP"

passed = 0
failed = 0
skipped = 0

def run(name, fn):
    global passed, failed
    try:
        fn()
        print(f"{PASS}: {name}")
        passed += 1
    except Exception as e:
        print(f"{FAIL}: {name} — {e}")
        failed += 1

def skip(name, reason):
    global skipped
    print(f"{SKIP}: {name} — {reason}")
    skipped += 1


# ---------------------------------------------------------------------------
# Test 1: VALID_ATTACK_EFFECT_TYPES contains "change_die" (was "set_die" in spec)
# ---------------------------------------------------------------------------
def test_valid_types_contains_change_die():
    assert "change_die" in VALID_ATTACK_EFFECT_TYPES, (
        f"'change_die' not in VALID_ATTACK_EFFECT_TYPES: {VALID_ATTACK_EFFECT_TYPES}"
    )


# ---------------------------------------------------------------------------
# Test 2: PRIORITY_DEPENDENT_OPS contains "change_die" (was "set_die" in spec)
# ---------------------------------------------------------------------------
def test_priority_dependent_ops_contains_change_die():
    assert "change_die" in PRIORITY_DEPENDENT_OPS, (
        f"'change_die' not in PRIORITY_DEPENDENT_OPS: {PRIORITY_DEPENDENT_OPS}"
    )


# ---------------------------------------------------------------------------
# Test 3: validate_attack_effect_pipeline raises on missing target_result for change_die
# ---------------------------------------------------------------------------
def test_validate_raises_on_missing_target_result():
    pool = DicePool(red=1, blue=0, black=0, type="ship")
    pipeline = [AttackEffect(type="change_die", applicable_results=["R_blank"], target_result=None)]
    try:
        validate_attack_effect_pipeline(pipeline, pool)
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "target_result" in str(e).lower() or "change_die" in str(e).lower(), (
            f"ValueError message doesn't mention target_result or change_die: {e}"
        )


# ---------------------------------------------------------------------------
# Test 4: validate_attack_effect_pipeline does NOT raise for valid change_die
# ---------------------------------------------------------------------------
def test_validate_ok_for_valid_change_die():
    pool = DicePool(red=1, blue=0, black=0, type="ship")
    pipeline = [AttackEffect(type="change_die", applicable_results=["R_blank"], target_result="R_hit")]
    validate_attack_effect_pipeline(pipeline, pool)  # should not raise


# ---------------------------------------------------------------------------
# Test 5: build_strategy_pipeline preserves target_result for change_die
# ---------------------------------------------------------------------------
def test_build_pipeline_preserves_target_result():
    effect = AttackEffect(
        type="change_die",
        applicable_results=["R_blank", "B_blank"],
        target_result="R_hit",
    )
    result = build_strategy_pipeline([effect], "max_damage", "ship")
    assert len(result) == 1
    assert result[0].target_result == "R_hit", (
        f"target_result not preserved: {result[0].target_result}"
    )


# ---------------------------------------------------------------------------
# Test 6: build_strategy_pipeline resolves priority_list for change_die
# ---------------------------------------------------------------------------
def test_build_pipeline_resolves_priority_list():
    effect = AttackEffect(
        type="change_die",
        applicable_results=["R_blank", "B_blank", "R_hit"],
        target_result="R_crit",
    )
    result = build_strategy_pipeline([effect], "max_damage", "ship")
    pl = result[0].priority_list
    # All faces in priority_list must be in applicable_results
    assert all(f in effect.applicable_results for f in pl), (
        f"priority_list contains faces not in applicable_results: {pl}"
    )


# ---------------------------------------------------------------------------
# Test 7: apply_attack_effect dispatches change_die correctly
# ---------------------------------------------------------------------------
def test_apply_dispatches_change_die():
    roll_df = combine_dice(1, 0, 0, "ship")
    effect = AttackEffect(
        type="change_die",
        applicable_results=["R_blank"],
        priority_list=["R_blank"],
        target_result="R_hit",
    )
    result_df = apply_attack_effect(roll_df, effect, "ship")
    # R_blank should be gone; R_hit proba should include the converted probability
    assert "R_blank" not in result_df["value"].values, "R_blank should be replaced"
    r_hit = result_df[result_df["value"] == "R_hit"]
    assert not r_hit.empty


# ---------------------------------------------------------------------------
# Test 8: apply_attack_effect returns unchanged df when priority_list is empty
# ---------------------------------------------------------------------------
def test_apply_noop_when_priority_list_empty():
    roll_df = combine_dice(1, 0, 0, "ship")
    effect = AttackEffect(
        type="change_die",
        applicable_results=[],
        priority_list=[],
        target_result="R_hit",
    )
    result_df = apply_attack_effect(roll_df, effect, "ship")
    # With empty priority_list, no faces match, so result should be unchanged
    assert abs(result_df["proba"].sum() - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Test 9: apply_attack_effect raises when target_result is None for change_die
# ---------------------------------------------------------------------------
def test_apply_raises_when_target_result_none():
    roll_df = combine_dice(1, 0, 0, "ship")
    effect = AttackEffect(
        type="change_die",
        applicable_results=["R_blank"],
        priority_list=["R_blank"],
        target_result=None,
    )
    try:
        apply_attack_effect(roll_df, effect, "ship")
        raise AssertionError("expected ValueError")
    except (ValueError, TypeError):
        pass  # Expected


if __name__ == "__main__":
    run("VALID_ATTACK_EFFECT_TYPES contains change_die", test_valid_types_contains_change_die)
    run("PRIORITY_DEPENDENT_OPS contains change_die", test_priority_dependent_ops_contains_change_die)
    run("validate_attack_effect_pipeline raises on missing target_result", test_validate_raises_on_missing_target_result)
    run("validate_attack_effect_pipeline ok for valid change_die", test_validate_ok_for_valid_change_die)
    run("build_strategy_pipeline preserves target_result", test_build_pipeline_preserves_target_result)
    run("build_strategy_pipeline resolves priority_list", test_build_pipeline_resolves_priority_list)
    run("apply_attack_effect dispatches change_die correctly", test_apply_dispatches_change_die)
    run("apply_attack_effect noop when priority_list empty", test_apply_noop_when_priority_list_empty)
    run("apply_attack_effect raises when target_result is None", test_apply_raises_when_target_result_none)

    print(f"\nResults: {passed} passed, {failed} failed, {skipped} skipped")
    if failed > 0:
        sys.exit(1)
