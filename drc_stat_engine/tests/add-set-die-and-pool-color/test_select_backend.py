"""
Test _select_backend accounts for add_set_die and color_in_pool dice counts.
"""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.dice_models import AttackEffect, DicePool
from drc_stat_engine.stats.report_engine import _select_backend
import drc_stat_engine.stats.dice_monte_carlo as dice_monte_carlo
import drc_stat_engine.stats.dice_maths_combinatories as dice_maths_combinatories

pool = DicePool(red=2, blue=2, black=2, type="ship")  # 6 base dice

# --- Test 1: add_set_die counted (6 base + 3 add_set_die = 9 > 8 → MC) ---
try:
    pipeline = [
        AttackEffect(type="add_set_die", target_result="R_hit"),
        AttackEffect(type="add_set_die", target_result="R_hit"),
        AttackEffect(type="add_set_die", target_result="R_hit"),
    ]
    result = _select_backend(pool, pipeline, "auto")
    assert result is dice_monte_carlo, f"Expected MC, got {result}"
    print("PASS: add_set_die ops push total above 8 → MC selected")
except Exception as e:
    print(f"FAIL: {e}")

# --- Test 2: add_set_die counted but stays under limit (6 + 2 = 8 → combinatorial) ---
try:
    pipeline = [
        AttackEffect(type="add_set_die", target_result="R_hit"),
        AttackEffect(type="add_set_die", target_result="R_hit"),
    ]
    result = _select_backend(pool, pipeline, "auto")
    assert result is dice_maths_combinatories, f"Expected combinatorial, got {result}"
    print("PASS: add_set_die ops keep total at 8 → combinatorial selected")
except Exception as e:
    print(f"FAIL: {e}")

# --- Test 3: color_in_pool add_dice counted as 1 die each ---
try:
    pipeline = [
        AttackEffect(type="add_dice", color_in_pool=True, color_priority=["red", "blue", "black"]),
        AttackEffect(type="add_dice", color_in_pool=True, color_priority=["red", "blue", "black"]),
        AttackEffect(type="add_dice", color_in_pool=True, color_priority=["red", "blue", "black"]),
    ]
    # 6 base + 3 color_in_pool = 9 > 8 → MC
    result = _select_backend(pool, pipeline, "auto")
    assert result is dice_monte_carlo, f"Expected MC, got {result}"
    print("PASS: color_in_pool add_dice ops push total above 8 → MC selected")
except Exception as e:
    print(f"FAIL: {e}")

# --- Test 4: regular add_dice still works ---
try:
    pipeline = [
        AttackEffect(type="add_dice", dice_to_add={"red": 1, "blue": 1, "black": 1}),
    ]
    # 6 base + 3 regular = 9 > 8 → MC
    result = _select_backend(pool, pipeline, "auto")
    assert result is dice_monte_carlo, f"Expected MC, got {result}"
    print("PASS: regular add_dice still counted correctly → MC selected")
except Exception as e:
    print(f"FAIL: {e}")

# --- Test 5: mix of all types ---
try:
    small_pool = DicePool(red=1, blue=1, black=1, type="ship")  # 3 base
    pipeline = [
        AttackEffect(type="add_set_die", target_result="R_hit"),           # +1 = 4
        AttackEffect(type="add_dice", color_in_pool=True, color_priority=["red", "blue", "black"]),  # +1 = 5
        AttackEffect(type="add_dice", dice_to_add={"red": 1, "blue": 0, "black": 0}),  # +1 = 6
    ]
    result = _select_backend(small_pool, pipeline, "auto")
    assert result is dice_maths_combinatories, f"Expected combinatorial, got {result}"
    print("PASS: mixed pipeline stays under limit → combinatorial selected")
except Exception as e:
    print(f"FAIL: {e}")

# --- Test 6: explicit backend overrides still work ---
try:
    pipeline = [AttackEffect(type="add_set_die", target_result="R_hit")]
    result = _select_backend(pool, pipeline, "combinatorial")
    assert result is dice_maths_combinatories, f"Expected combinatorial, got {result}"
    result = _select_backend(pool, pipeline, "montecarlo")
    assert result is dice_monte_carlo, f"Expected MC, got {result}"
    print("PASS: explicit backend overrides still work")
except Exception as e:
    print(f"FAIL: {e}")

print("\nAll _select_backend tests complete.")
