"""Tests for task 1.2: validate_attack_effect_pipeline updates for new fields."""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.dice_models import (
    AttackEffect,
    DicePool,
    validate_attack_effect_pipeline,
    VALID_FACES_BY_TYPE,
    MAX_DICE,
)

passed = 0
failed = 0

def check(label, fn):
    global passed, failed
    try:
        fn()
        print(f"PASS: {label}")
        passed += 1
    except Exception as e:
        print(f"FAIL: {label} — {e}")
        failed += 1

pool_ship = DicePool(red=1, blue=0, black=0, type="ship")
pool_squad = DicePool(red=0, blue=1, black=0, type="squad")

# ===== add_set_die: target_result required =====

def test_add_set_die_missing_target_result():
    try:
        validate_attack_effect_pipeline([AttackEffect(type="add_set_die")], pool_ship)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "target_result" in str(e), f"Unexpected message: {e}"

check("add_set_die missing target_result raises ValueError", test_add_set_die_missing_target_result)

def test_add_set_die_none_target_result():
    try:
        validate_attack_effect_pipeline([AttackEffect(type="add_set_die", target_result=None)], pool_ship)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "target_result" in str(e), f"Unexpected message: {e}"

check("add_set_die target_result=None raises ValueError", test_add_set_die_none_target_result)

# ===== add_set_die: target_result must be valid face =====

def test_add_set_die_invalid_face():
    try:
        validate_attack_effect_pipeline([AttackEffect(type="add_set_die", target_result="INVALID")], pool_ship)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "not a valid face" in str(e), f"Unexpected message: {e}"

check("add_set_die invalid target_result raises ValueError", test_add_set_die_invalid_face)

def test_add_set_die_valid_ship_faces():
    for face in VALID_FACES_BY_TYPE["ship"]:
        validate_attack_effect_pipeline([AttackEffect(type="add_set_die", target_result=face)], pool_ship)

check("add_set_die accepts all valid ship faces", test_add_set_die_valid_ship_faces)

def test_add_set_die_valid_squad_faces():
    for face in VALID_FACES_BY_TYPE["squad"]:
        validate_attack_effect_pipeline([AttackEffect(type="add_set_die", target_result=face)], pool_squad)

check("add_set_die accepts all valid squad faces", test_add_set_die_valid_squad_faces)

# ===== add_set_die: increments dice count, enforces MAX_DICE =====

def test_add_set_die_max_dice():
    big_pool = DicePool(red=7, blue=7, black=6, type="ship")  # 20 dice = MAX
    try:
        validate_attack_effect_pipeline([AttackEffect(type="add_set_die", target_result="R_hit")], big_pool)
        assert False, "Expected ValueError for exceeding MAX_DICE"
    except ValueError as e:
        assert "exceeding the maximum" in str(e), f"Unexpected message: {e}"

check("add_set_die at MAX_DICE raises ValueError", test_add_set_die_max_dice)

def test_add_set_die_under_max_dice():
    pool_19 = DicePool(red=7, blue=7, black=5, type="ship")  # 19 dice
    validate_attack_effect_pipeline([AttackEffect(type="add_set_die", target_result="R_hit")], pool_19)

check("add_set_die at 19 dice passes (becomes 20)", test_add_set_die_under_max_dice)

def test_add_set_die_multiple_exceed():
    pool_18 = DicePool(red=6, blue=6, black=6, type="ship")  # 18 dice
    pipeline = [
        AttackEffect(type="add_set_die", target_result="R_hit"),  # 19
        AttackEffect(type="add_set_die", target_result="R_hit"),  # 20
        AttackEffect(type="add_set_die", target_result="R_hit"),  # 21 — should fail
    ]
    try:
        validate_attack_effect_pipeline(pipeline, pool_18)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "exceeding the maximum" in str(e), f"Unexpected message: {e}"

check("multiple add_set_die exceeding MAX_DICE raises ValueError", test_add_set_die_multiple_exceed)

# ===== face_condition: only on add_dice and add_set_die =====

def test_face_condition_on_reroll():
    try:
        validate_attack_effect_pipeline(
            [AttackEffect(type="reroll", face_condition="R_hit")], pool_ship)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "face_condition" in str(e), f"Unexpected message: {e}"

check("face_condition on reroll raises ValueError", test_face_condition_on_reroll)

def test_face_condition_on_cancel():
    try:
        validate_attack_effect_pipeline(
            [AttackEffect(type="cancel", face_condition="R_hit")], pool_ship)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "face_condition" in str(e), f"Unexpected message: {e}"

check("face_condition on cancel raises ValueError", test_face_condition_on_cancel)

def test_face_condition_on_change_die():
    try:
        validate_attack_effect_pipeline(
            [AttackEffect(type="change_die", target_result="R_hit", face_condition="R_acc")], pool_ship)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "face_condition" in str(e), f"Unexpected message: {e}"

check("face_condition on change_die raises ValueError", test_face_condition_on_change_die)

def test_face_condition_on_add_dice_ok():
    validate_attack_effect_pipeline(
        [AttackEffect(type="add_dice", dice_to_add={"red": 1, "blue": 0, "black": 0}, face_condition="R_hit")],
        pool_ship)

check("face_condition on add_dice passes", test_face_condition_on_add_dice_ok)

def test_face_condition_on_add_set_die_ok():
    validate_attack_effect_pipeline(
        [AttackEffect(type="add_set_die", target_result="R_hit", face_condition="R_acc")],
        pool_ship)

check("face_condition on add_set_die passes", test_face_condition_on_add_set_die_ok)

# ===== face_condition: must be non-empty string =====

def test_face_condition_empty_string():
    try:
        validate_attack_effect_pipeline(
            [AttackEffect(type="add_dice", dice_to_add={"red": 1, "blue": 0, "black": 0}, face_condition="")],
            pool_ship)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "non-empty string" in str(e), f"Unexpected message: {e}"

check("face_condition empty string raises ValueError", test_face_condition_empty_string)

# ===== color_in_pool: only on add_dice =====

def test_color_in_pool_on_add_set_die():
    try:
        validate_attack_effect_pipeline(
            [AttackEffect(type="add_set_die", target_result="R_hit", color_in_pool=True)], pool_ship)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "color_in_pool" in str(e), f"Unexpected message: {e}"

check("color_in_pool on add_set_die raises ValueError", test_color_in_pool_on_add_set_die)

def test_color_in_pool_on_reroll():
    try:
        validate_attack_effect_pipeline(
            [AttackEffect(type="reroll", color_in_pool=True)], pool_ship)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "color_in_pool" in str(e), f"Unexpected message: {e}"

check("color_in_pool on reroll raises ValueError", test_color_in_pool_on_reroll)

def test_color_in_pool_on_add_dice_ok():
    validate_attack_effect_pipeline(
        [AttackEffect(type="add_dice", dice_to_add={"red": 1, "blue": 0, "black": 0}, color_in_pool=True)],
        pool_ship)

check("color_in_pool on add_dice passes", test_color_in_pool_on_add_dice_ok)

# ===== color_priority: must be permutation of ["red", "blue", "black"] =====

def test_color_priority_valid():
    validate_attack_effect_pipeline(
        [AttackEffect(type="add_dice", dice_to_add={"red": 1}, color_in_pool=True,
                      color_priority=["black", "red", "blue"])],
        pool_ship)

check("valid color_priority passes", test_color_priority_valid)

def test_color_priority_invalid_extra():
    try:
        validate_attack_effect_pipeline(
            [AttackEffect(type="add_dice", dice_to_add={"red": 1}, color_in_pool=True,
                          color_priority=["red", "blue", "black", "red"])],
            pool_ship)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "color_priority" in str(e), f"Unexpected message: {e}"

check("color_priority with extra element raises ValueError", test_color_priority_invalid_extra)

def test_color_priority_invalid_names():
    try:
        validate_attack_effect_pipeline(
            [AttackEffect(type="add_dice", dice_to_add={"red": 1}, color_in_pool=True,
                          color_priority=["red", "green", "black"])],
            pool_ship)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "color_priority" in str(e), f"Unexpected message: {e}"

check("color_priority with invalid color name raises ValueError", test_color_priority_invalid_names)

def test_color_priority_duplicates():
    try:
        validate_attack_effect_pipeline(
            [AttackEffect(type="add_dice", dice_to_add={"red": 1}, color_in_pool=True,
                          color_priority=["red", "red", "red"])],
            pool_ship)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "color_priority" in str(e), f"Unexpected message: {e}"

check("color_priority with duplicates raises ValueError", test_color_priority_duplicates)

def test_color_priority_empty():
    try:
        validate_attack_effect_pipeline(
            [AttackEffect(type="add_dice", dice_to_add={"red": 1}, color_in_pool=True,
                          color_priority=[])],
            pool_ship)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "color_priority" in str(e), f"Unexpected message: {e}"

check("color_priority empty list raises ValueError", test_color_priority_empty)

def test_color_priority_none_ok():
    """color_priority=None is fine — resolved later by strategy pipeline."""
    validate_attack_effect_pipeline(
        [AttackEffect(type="add_dice", dice_to_add={"red": 1}, color_in_pool=True,
                      color_priority=None)],
        pool_ship)

check("color_priority=None with color_in_pool passes", test_color_priority_none_ok)

# ===== Existing validations still work =====

def test_existing_change_die_still_works():
    try:
        validate_attack_effect_pipeline([AttackEffect(type="change_die")], pool_ship)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "target_result" in str(e)

check("existing change_die validation still works", test_existing_change_die_still_works)

def test_existing_unknown_type_still_works():
    try:
        validate_attack_effect_pipeline([AttackEffect(type="bogus")], pool_ship)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "unknown attack effect type" in str(e)

check("existing unknown type validation still works", test_existing_unknown_type_still_works)

# ===== Summary =====
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
