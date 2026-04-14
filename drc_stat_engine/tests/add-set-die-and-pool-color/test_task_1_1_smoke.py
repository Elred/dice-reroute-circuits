"""Smoke test for task 1.1: dice_models.py extensions."""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.dice_models import (
    VALID_ATTACK_EFFECT_TYPES,
    COLOR_PREFIXES,
    AttackEffect,
    evaluate_face_condition,
    select_color_from_pool,
)

passed = 0
failed = 0

# --- Sub-task 1: add_set_die in VALID_ATTACK_EFFECT_TYPES ---
try:
    assert "add_set_die" in VALID_ATTACK_EFFECT_TYPES, "add_set_die not in VALID_ATTACK_EFFECT_TYPES"
    print("PASS: add_set_die is in VALID_ATTACK_EFFECT_TYPES")
    passed += 1
except AssertionError as e:
    print(f"FAIL: {e}")
    failed += 1

# --- Sub-task 2: face_condition field ---
try:
    ae = AttackEffect(type="add_set_die")
    assert ae.face_condition is None, f"Expected None, got {ae.face_condition}"
    ae2 = AttackEffect(type="add_dice", face_condition="R_acc")
    assert ae2.face_condition == "R_acc", f"Expected R_acc, got {ae2.face_condition}"
    print("PASS: face_condition field works correctly")
    passed += 1
except Exception as e:
    print(f"FAIL: face_condition — {e}")
    failed += 1

# --- Sub-task 3: color_in_pool field ---
try:
    ae = AttackEffect(type="add_dice")
    assert ae.color_in_pool is False, f"Expected False, got {ae.color_in_pool}"
    ae2 = AttackEffect(type="add_dice", color_in_pool=True)
    assert ae2.color_in_pool is True, f"Expected True, got {ae2.color_in_pool}"
    print("PASS: color_in_pool field works correctly")
    passed += 1
except Exception as e:
    print(f"FAIL: color_in_pool — {e}")
    failed += 1

# --- Sub-task 4: color_priority field ---
try:
    ae = AttackEffect(type="add_dice")
    assert ae.color_priority is None, f"Expected None, got {ae.color_priority}"
    ae2 = AttackEffect(type="add_dice", color_priority=["red", "blue", "black"])
    assert ae2.color_priority == ["red", "blue", "black"]
    print("PASS: color_priority field works correctly")
    passed += 1
except Exception as e:
    print(f"FAIL: color_priority — {e}")
    failed += 1

# --- Sub-task 5: COLOR_PREFIXES constant ---
try:
    assert COLOR_PREFIXES == {"red": "R", "blue": "U", "black": "B"}, f"Unexpected: {COLOR_PREFIXES}"
    print("PASS: COLOR_PREFIXES is correct")
    passed += 1
except Exception as e:
    print(f"FAIL: COLOR_PREFIXES — {e}")
    failed += 1

# --- Sub-task 6: evaluate_face_condition ---
try:
    assert evaluate_face_condition("R_acc", "R_hit R_acc B_blank") is True
    assert evaluate_face_condition("R_acc", "R_hit B_blank") is False
    assert evaluate_face_condition("R_hit", "R_hit") is True
    assert evaluate_face_condition("R_hit", "") is False
    # Ensure no partial match: "R_hit" should not match "R_hit+crit"
    assert evaluate_face_condition("R_hit", "R_hit+crit B_blank") is False
    print("PASS: evaluate_face_condition works correctly")
    passed += 1
except Exception as e:
    print(f"FAIL: evaluate_face_condition — {e}")
    failed += 1

# --- Sub-task 7: select_color_from_pool ---
try:
    # Red present, priority red first
    result = select_color_from_pool(["red", "blue", "black"], "R_hit U_acc B_blank")
    assert result == "red", f"Expected red, got {result}"
    # Priority black first, all present
    result = select_color_from_pool(["black", "red", "blue"], "R_hit U_acc B_blank")
    assert result == "black", f"Expected black, got {result}"
    # Only blue present
    result = select_color_from_pool(["red", "blue", "black"], "U_acc U_hit")
    assert result == "blue", f"Expected blue, got {result}"
    # Fallback when no prefix matches (edge case)
    result = select_color_from_pool(["red", "blue", "black"], "")
    assert result == "red", f"Expected red (fallback), got {result}"
    print("PASS: select_color_from_pool works correctly")
    passed += 1
except Exception as e:
    print(f"FAIL: select_color_from_pool — {e}")
    failed += 1

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
