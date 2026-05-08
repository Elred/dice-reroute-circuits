"""
Test parse_report_request for add_set_die, face_condition, and color_in_pool parsing.
Validates: Requirements 16.1, 16.2, 16.3
"""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.api.routes import parse_report_request

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

# --- REQ-16.1: Parse add_set_die type ---

# 1. add_set_die with target_result is parsed correctly
data = {
    "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "ship"},
    "pipeline": [
        {"type": "add_set_die", "target_result": "R_hit"}
    ],
    "strategies": ["max_damage"],
}
pool, pipeline, strategies, _defense = parse_report_request(data)
check("add_set_die parsed", pipeline[0].type == "add_set_die")
check("add_set_die target_result", pipeline[0].target_result == "R_hit")

# 2. add_set_die increments running_size (count=any should reflect new size)
data2 = {
    "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "ship"},
    "pipeline": [
        {"type": "add_set_die", "target_result": "R_hit"},
        {"type": "reroll", "count": "any", "applicable_results": ["R_blank"]},
    ],
    "strategies": ["max_damage"],
}
pool2, pipeline2, _, _defense2 = parse_report_request(data2)
check("add_set_die increments running_size",
      pipeline2[1].count == 2,
      f"expected 2, got {pipeline2[1].count}")

# 3. add_set_die without target_result raises KeyError
try:
    parse_report_request({
        "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "ship"},
        "pipeline": [{"type": "add_set_die"}],
        "strategies": ["max_damage"],
    })
    check("add_set_die missing target_result raises KeyError", False, "no exception raised")
except KeyError:
    check("add_set_die missing target_result raises KeyError", True)
except Exception as e:
    check("add_set_die missing target_result raises KeyError", False, f"got {type(e).__name__}: {e}")

# --- REQ-16.2: Parse face_condition ---

# 4. face_condition on add_dice
data3 = {
    "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "ship"},
    "pipeline": [
        {"type": "add_dice", "dice_to_add": {"red": 0, "blue": 0, "black": 1}, "face_condition": "R_acc"}
    ],
    "strategies": ["max_damage"],
}
_, pipeline3, _, _d = parse_report_request(data3)
check("face_condition on add_dice parsed",
      pipeline3[0].face_condition == "R_acc",
      f"got {pipeline3[0].face_condition}")

# 5. face_condition on add_set_die
data4 = {
    "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "ship"},
    "pipeline": [
        {"type": "add_set_die", "target_result": "R_hit", "face_condition": "R_acc"}
    ],
    "strategies": ["max_damage"],
}
_, pipeline4, _, _d = parse_report_request(data4)
check("face_condition on add_set_die parsed",
      pipeline4[0].face_condition == "R_acc",
      f"got {pipeline4[0].face_condition}")

# 6. face_condition absent defaults to None
data5 = {
    "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "ship"},
    "pipeline": [
        {"type": "reroll", "count": 1, "applicable_results": ["R_blank"]}
    ],
    "strategies": ["max_damage"],
}
_, pipeline5, _, _d = parse_report_request(data5)
check("face_condition defaults to None",
      pipeline5[0].face_condition is None,
      f"got {pipeline5[0].face_condition}")

# --- REQ-16.3: Parse color_in_pool and color_priority ---

# 7. color_in_pool on add_dice
data6 = {
    "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "ship"},
    "pipeline": [
        {"type": "add_dice", "color_in_pool": True, "color_priority": ["red", "blue", "black"]}
    ],
    "strategies": ["max_damage"],
}
_, pipeline6, _, _d = parse_report_request(data6)
check("color_in_pool parsed as True",
      pipeline6[0].color_in_pool is True,
      f"got {pipeline6[0].color_in_pool}")
check("color_priority parsed",
      pipeline6[0].color_priority == ["red", "blue", "black"],
      f"got {pipeline6[0].color_priority}")

# 8. color_in_pool absent defaults to False
data7 = {
    "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "ship"},
    "pipeline": [
        {"type": "add_dice", "dice_to_add": {"red": 0, "blue": 0, "black": 1}}
    ],
    "strategies": ["max_damage"],
}
_, pipeline7, _, _d = parse_report_request(data7)
check("color_in_pool defaults to False",
      pipeline7[0].color_in_pool is False,
      f"got {pipeline7[0].color_in_pool}")
check("color_priority defaults to None",
      pipeline7[0].color_priority is None,
      f"got {pipeline7[0].color_priority}")

# 9. color_in_pool with color_priority omitted
data8 = {
    "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "ship"},
    "pipeline": [
        {"type": "add_dice", "color_in_pool": True}
    ],
    "strategies": ["max_damage"],
}
_, pipeline8, _, _d = parse_report_request(data8)
check("color_in_pool True without color_priority",
      pipeline8[0].color_in_pool is True and pipeline8[0].color_priority is None,
      f"got color_in_pool={pipeline8[0].color_in_pool}, color_priority={pipeline8[0].color_priority}")

# 10. Existing types still work (reroll, cancel, change_die, add_dice without new fields)
data9 = {
    "dice_pool": {"red": 1, "blue": 1, "black": 0, "type": "ship"},
    "pipeline": [
        {"type": "reroll", "count": 1, "applicable_results": ["R_blank"]},
        {"type": "cancel", "count": 1, "applicable_results": ["U_blank"]},
        {"type": "change_die", "target_result": "R_hit", "applicable_results": ["R_blank"]},
        {"type": "add_dice", "dice_to_add": {"red": 0, "blue": 0, "black": 1}},
    ],
    "strategies": ["max_damage"],
}
_, pipeline9, _, _d = parse_report_request(data9)
check("existing reroll still works", pipeline9[0].type == "reroll")
check("existing cancel still works", pipeline9[1].type == "cancel")
check("existing change_die still works",
      pipeline9[2].type == "change_die" and pipeline9[2].target_result == "R_hit")
check("existing add_dice still works",
      pipeline9[3].type == "add_dice" and pipeline9[3].dice_to_add == {"red": 0, "blue": 0, "black": 1})
check("existing ops have face_condition=None",
      all(p.face_condition is None for p in pipeline9))
check("existing ops have color_in_pool=False",
      all(p.color_in_pool is False for p in pipeline9))

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
