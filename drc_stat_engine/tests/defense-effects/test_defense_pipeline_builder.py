"""
test_defense_pipeline_builder.py — Tests for DEFENSE_PRIORITY_LISTS and build_defense_pipeline.

Covers:
- DEFENSE_PRIORITY_LISTS constant values (Req 13.2, 13.3, 13.4)
- build_defense_pipeline resolves priority_list for defense_reroll (safe + gamble)
- build_defense_pipeline resolves priority_list for defense_cancel
- applicable_results filtering preserves priority ordering (Req 2.3, 3.2, 13.5)
- reduce_damage and divide_damage pass through unchanged
"""

import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.strategies import DEFENSE_PRIORITY_LISTS, build_defense_pipeline
from drc_stat_engine.stats.dice_models import DefenseEffect

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

try:
    # --- Constant values (ship) ---
    check("ship safe reroll priority",
          DEFENSE_PRIORITY_LISTS["ship"]["defense_reroll"]["safe"] == ["R_hit+hit", "B_hit+crit", "U_crit", "U_hit"])

    check("ship gamble reroll priority",
          DEFENSE_PRIORITY_LISTS["ship"]["defense_reroll"]["gamble"] == ["R_hit+hit", "B_hit+crit", "R_crit", "R_hit", "U_crit", "U_hit", "B_hit"])

    check("ship defense_cancel priority",
          DEFENSE_PRIORITY_LISTS["ship"]["defense_cancel"] == ["B_hit+crit", "R_hit+hit", "U_crit", "R_crit", "R_hit", "U_hit", "B_hit"])

    # --- Constant values (squad) — crits are worthless, never rerolled/cancelled ---
    check("squad safe reroll priority (no crits)",
          DEFENSE_PRIORITY_LISTS["squad"]["defense_reroll"]["safe"] == ["R_hit+hit", "B_hit+crit", "B_hit", "U_hit"])

    check("squad gamble reroll priority (no crits)",
          DEFENSE_PRIORITY_LISTS["squad"]["defense_reroll"]["gamble"] == ["R_hit+hit", "R_hit", "U_hit", "B_hit", "B_hit+crit"])

    check("squad defense_cancel priority (no crits)",
          DEFENSE_PRIORITY_LISTS["squad"]["defense_cancel"] == ["R_hit+hit", "R_hit", "U_hit", "B_hit", "B_hit+crit"])

    # --- defense_reroll safe, no applicable_results ---
    e = DefenseEffect(type="defense_reroll", count=2, mode="safe")
    result = build_defense_pipeline([e])
    check("defense_reroll safe resolves full priority",
          result[0].priority_list == ["R_hit+hit", "B_hit+crit", "U_crit", "U_hit"],
          f"got {result[0].priority_list}")

    # --- defense_reroll gamble, no applicable_results ---
    e = DefenseEffect(type="defense_reroll", count=1, mode="gamble")
    result = build_defense_pipeline([e])
    check("defense_reroll gamble resolves full priority",
          result[0].priority_list == ["R_hit+hit", "B_hit+crit", "R_crit", "R_hit", "U_crit", "U_hit", "B_hit"],
          f"got {result[0].priority_list}")

    # --- defense_reroll safe with applicable_results filter ---
    e = DefenseEffect(type="defense_reroll", count=1, mode="safe", applicable_results=["U_hit", "R_hit+hit"])
    result = build_defense_pipeline([e])
    check("defense_reroll safe filtered by applicable_results preserves order",
          result[0].priority_list == ["R_hit+hit", "U_hit"],
          f"got {result[0].priority_list}")

    # --- defense_cancel, no applicable_results ---
    e = DefenseEffect(type="defense_cancel", count=1)
    result = build_defense_pipeline([e])
    check("defense_cancel resolves full priority",
          result[0].priority_list == ["B_hit+crit", "R_hit+hit", "U_crit", "R_crit", "R_hit", "U_hit", "B_hit"],
          f"got {result[0].priority_list}")

    # --- defense_cancel with applicable_results filter ---
    e = DefenseEffect(type="defense_cancel", count=1, applicable_results=["R_hit", "B_hit+crit"])
    result = build_defense_pipeline([e])
    check("defense_cancel filtered by applicable_results preserves order",
          result[0].priority_list == ["B_hit+crit", "R_hit"],
          f"got {result[0].priority_list}")

    # --- reduce_damage passes through ---
    e = DefenseEffect(type="reduce_damage", amount=2)
    result = build_defense_pipeline([e])
    check("reduce_damage passes through",
          result[0].type == "reduce_damage" and result[0].amount == 2)

    # --- divide_damage passes through ---
    e = DefenseEffect(type="divide_damage")
    result = build_defense_pipeline([e])
    check("divide_damage passes through",
          result[0].type == "divide_damage")

    # --- Does not mutate originals ---
    original = DefenseEffect(type="defense_reroll", count=1, mode="safe")
    build_defense_pipeline([original])
    check("original not mutated",
          original.priority_list == [],
          f"original.priority_list = {original.priority_list}")

    # --- Mixed pipeline ---
    pipeline = [
        DefenseEffect(type="defense_reroll", count=1, mode="safe"),
        DefenseEffect(type="reduce_damage", amount=3),
        DefenseEffect(type="defense_cancel", count=2, applicable_results=["U_crit"]),
        DefenseEffect(type="divide_damage"),
    ]
    result = build_defense_pipeline(pipeline)
    check("mixed pipeline length", len(result) == 4, f"got {len(result)}")
    check("mixed pipeline[0] is resolved reroll",
          result[0].priority_list == ["R_hit+hit", "B_hit+crit", "U_crit", "U_hit"])
    check("mixed pipeline[1] is reduce_damage",
          result[1].type == "reduce_damage" and result[1].amount == 3)
    check("mixed pipeline[2] is filtered cancel",
          result[2].priority_list == ["U_crit"],
          f"got {result[2].priority_list}")
    check("mixed pipeline[3] is divide_damage",
          result[3].type == "divide_damage")

except Exception as exc:
    print(f"UNEXPECTED ERROR: {exc}")
    import traceback; traceback.print_exc()
    failed += 1

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
