"""Smoke tests for _format_pipeline updates: add_set_die, face_condition, color_in_pool."""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.report_engine import _format_pipeline
from drc_stat_engine.stats.dice_models import AttackEffect

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

# 1. add_set_die basic formatting
pipeline = [AttackEffect(type="add_set_die", target_result="R_hit")]
result = _format_pipeline(pipeline)
check("add_set_die basic", "add_set_die [R_hit]" in result, f"got: {result}")

# 2. add_set_die with face_condition
pipeline = [AttackEffect(type="add_set_die", target_result="B_hit+crit", face_condition="R_acc")]
result = _format_pipeline(pipeline)
check("add_set_die with face_condition", "add_set_die [B_hit+crit] if R_acc present" in result, f"got: {result}")

# 3. add_dice with face_condition
pipeline = [AttackEffect(type="add_dice", dice_to_add={"red": 1, "blue": 0, "black": 0}, face_condition="U_hit")]
result = _format_pipeline(pipeline)
check("add_dice with face_condition", "add_dice [1R 0U 0B] if U_hit present" in result, f"got: {result}")

# 4. add_dice with color_in_pool
pipeline = [AttackEffect(type="add_dice", color_in_pool=True, color_priority=["black", "red", "blue"])]
result = _format_pipeline(pipeline)
check("add_dice with color_in_pool", "color_in_pool [" in result, f"got: {result}")
check("add_dice color_in_pool has priority", "['black', 'red', 'blue']" in result, f"got: {result}")

# 5. add_dice with face_condition AND color_in_pool
pipeline = [AttackEffect(type="add_dice", face_condition="R_hit", color_in_pool=True, color_priority=["red", "blue", "black"])]
result = _format_pipeline(pipeline)
check("add_dice fc+cip has face_condition", "if R_hit present" in result, f"got: {result}")
check("add_dice fc+cip has color_in_pool", "color_in_pool [" in result, f"got: {result}")

# 6. Existing formatting unchanged — reroll
pipeline = [AttackEffect(type="reroll", count=2, applicable_results=["R_blank", "U_blank"])]
result = _format_pipeline(pipeline)
check("reroll unchanged", result == "reroll x2 [R_blank, U_blank]", f"got: {result}")

# 7. Existing formatting unchanged — cancel
pipeline = [AttackEffect(type="cancel", count=1, applicable_results=["R_acc"])]
result = _format_pipeline(pipeline)
check("cancel unchanged", result == "cancel x1 [R_acc]", f"got: {result}")

# 8. add_dice without new fields (existing behavior)
pipeline = [AttackEffect(type="add_dice", dice_to_add={"red": 0, "blue": 1, "black": 0})]
result = _format_pipeline(pipeline)
check("add_dice plain unchanged", result == "add_dice [0R 1U 0B]", f"got: {result}")

# 9. Empty pipeline
result = _format_pipeline([])
check("empty pipeline", result == "(none)", f"got: {result}")

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed")
if failed > 0:
    sys.exit(1)
