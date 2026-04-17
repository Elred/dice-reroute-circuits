"""
Smoke tests for task 7.1: build_strategy_pipeline updates for add_set_die,
face_condition, color_in_pool, and color_priority resolution.
"""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.dice_models import AttackEffect
from drc_stat_engine.stats.strategies import build_strategy_pipeline, STRATEGY_PRIORITY_LISTS

passed = 0
failed = 0

def check(label, condition, detail=""):
    global passed, failed
    if condition:
        print(f"PASS: {label}")
        passed += 1
    else:
        print(f"FAIL: {label} — {detail}")
        failed += 1

# --- 1. add_set_die passes through unchanged ---
pipeline = [AttackEffect(type="add_set_die", target_result="R_hit")]
result = build_strategy_pipeline(pipeline, "max_damage", "ship")
check("add_set_die pass-through: type preserved",
      result[0].type == "add_set_die")
check("add_set_die pass-through: target_result preserved",
      result[0].target_result == "R_hit")
check("add_set_die pass-through: face_condition is None",
      result[0].face_condition is None)

# --- 2. add_set_die with face_condition preserved ---
pipeline = [AttackEffect(type="add_set_die", target_result="B_hit+crit", face_condition="R_acc")]
result = build_strategy_pipeline(pipeline, "balanced", "ship")
check("add_set_die with face_condition: target_result preserved",
      result[0].target_result == "B_hit+crit")
check("add_set_die with face_condition: face_condition preserved",
      result[0].face_condition == "R_acc")

# --- 3. add_dice with face_condition preserved ---
pipeline = [AttackEffect(type="add_dice", dice_to_add={"red": 1, "blue": 0, "black": 0}, face_condition="U_acc")]
result = build_strategy_pipeline(pipeline, "max_damage", "ship")
check("add_dice with face_condition: face_condition preserved",
      result[0].face_condition == "U_acc")
check("add_dice with face_condition: dice_to_add preserved",
      result[0].dice_to_add == {"red": 1, "blue": 0, "black": 0})

# --- 4. add_dice with color_in_pool=True, no user color_priority → resolved from strategy ---
pipeline = [AttackEffect(type="add_dice", color_in_pool=True)]
result = build_strategy_pipeline(pipeline, "max_damage", "ship")
check("color_in_pool resolved from strategy (max_damage/ship)",
      result[0].color_priority == ["black", "red", "blue"],
      f"got {result[0].color_priority}")
check("color_in_pool flag preserved",
      result[0].color_in_pool is True)

# --- 5. add_dice with color_in_pool=True, user-provided color_priority preserved ---
user_priority = ["blue", "black", "red"]
pipeline = [AttackEffect(type="add_dice", color_in_pool=True, color_priority=user_priority)]
result = build_strategy_pipeline(pipeline, "max_damage", "ship")
check("user-provided color_priority preserved",
      result[0].color_priority == ["blue", "black", "red"],
      f"got {result[0].color_priority}")

# --- 6. Verify strategy defaults for all strategies/types ---
expected_defaults = {
    ("ship", "max_damage"): ["black", "red", "blue"],
    ("ship", "balanced"): ["red", "blue", "black"],
    ("ship", "black_doubles"): ["black", "red", "blue"],
    ("ship", "max_accuracy_blue"): ["blue", "red", "black"],
    ("squad", "max_damage"): ["red", "blue", "black"],
    ("squad", "balanced"): ["red", "blue", "black"],
    ("squad", "max_accuracy_blue"): ["blue", "red", "black"],
}
for (type_str, strat), expected in expected_defaults.items():
    pipeline = [AttackEffect(type="add_dice", color_in_pool=True)]
    result = build_strategy_pipeline(pipeline, strat, type_str)
    check(f"color_priority default for {strat}/{type_str}",
          result[0].color_priority == expected,
          f"expected {expected}, got {result[0].color_priority}")

# --- 7. add_dice without color_in_pool — color_priority stays None ---
pipeline = [AttackEffect(type="add_dice", dice_to_add={"red": 0, "blue": 0, "black": 1})]
result = build_strategy_pipeline(pipeline, "max_damage", "ship")
check("add_dice without color_in_pool: color_priority is None",
      result[0].color_priority is None)
check("add_dice without color_in_pool: color_in_pool is False",
      result[0].color_in_pool is False)

# --- 8. Existing behavior: reroll still works ---
pipeline = [AttackEffect(type="reroll", count=1, applicable_results=["R_blank", "B_blank"])]
result = build_strategy_pipeline(pipeline, "max_damage", "ship")
check("reroll still resolves priority_list",
      result[0].priority_list == ["R_blank", "B_blank"],
      f"got {result[0].priority_list}")

# --- 9. add_dice with both face_condition and color_in_pool ---
pipeline = [AttackEffect(type="add_dice", color_in_pool=True, face_condition="R_hit")]
result = build_strategy_pipeline(pipeline, "balanced", "squad")
check("add_dice with face_condition + color_in_pool: face_condition preserved",
      result[0].face_condition == "R_hit")
check("add_dice with face_condition + color_in_pool: color_in_pool preserved",
      result[0].color_in_pool is True)
check("add_dice with face_condition + color_in_pool: color_priority resolved",
      result[0].color_priority == ["red", "blue", "black"],
      f"got {result[0].color_priority}")

# --- Summary ---
print(f"\n{'='*40}")
print(f"Total: {passed + failed} | Passed: {passed} | Failed: {failed}")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print(f"{failed} TEST(S) FAILED")
