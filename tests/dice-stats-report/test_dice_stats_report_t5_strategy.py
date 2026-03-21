"""
Tests for task 5: strategy-based report variants.
Covers STRATEGY_PRIORITY_LISTS, build_strategy_pipeline, and generate_report.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'stats'))

from report import (
    DicePool, Operation,
    STRATEGY_PRIORITY_LISTS, PRIORITY_DEPENDENT_OPS,
    build_strategy_pipeline, generate_report,
)

PASS = 0
FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"PASS: {label}")
        PASS += 1
    else:
        print(f"FAIL: {label}" + (f" — {detail}" if detail else ""))
        FAIL += 1

# ---------------------------------------------------------------------------
# 5.1 — Strategy priority lists: all strategies defined for both types
# ---------------------------------------------------------------------------

SHIP_STRATEGIES = ("max_damage", "max_doubles", "max_accuracy", "max_crits")
SQUAD_STRATEGIES = ("max_damage", "max_accuracy", "max_crits")

for strategy in SHIP_STRATEGIES:
    pl = STRATEGY_PRIORITY_LISTS["ship"][strategy]
    check(
        f"STRATEGY_PRIORITY_LISTS['ship'][{strategy!r}] is non-empty list",
        isinstance(pl, list) and len(pl) > 0,
    )

for strategy in SQUAD_STRATEGIES:
    pl = STRATEGY_PRIORITY_LISTS["squad"][strategy]
    check(
        f"STRATEGY_PRIORITY_LISTS['squad'][{strategy!r}] is non-empty list",
        isinstance(pl, list) and len(pl) > 0,
    )

# ---------------------------------------------------------------------------
# 5.1 — Ship strategy ordering invariants
# ---------------------------------------------------------------------------

# max_damage: only blanks and acc faces are candidates; blanks come first
ship_md = STRATEGY_PRIORITY_LISTS["ship"]["max_damage"]
check("ship max_damage: R_blank before R_acc", ship_md.index("R_blank") < ship_md.index("R_acc"))
check("ship max_damage: B_blank before U_acc", ship_md.index("B_blank") < ship_md.index("U_acc"))
check("ship max_damage: U_acc before R_acc (blue acc rerolled first)",
      ship_md.index("U_acc") < ship_md.index("R_acc"))
# hits and doubles are NOT in max_damage (kept unconditionally)
check("ship max_damage: R_hit not in list (kept unconditionally)", "R_hit" not in ship_md)
check("ship max_damage: R_hit+hit not in list (kept unconditionally)", "R_hit+hit" not in ship_md)
check("ship max_damage: B_hit+crit not in list (kept unconditionally)", "B_hit+crit" not in ship_md)

# max_doubles: blanks and acc before hits before crits; doubles kept (not listed)
ship_mdb = STRATEGY_PRIORITY_LISTS["ship"]["max_doubles"]
check("ship max_doubles: R_blank before R_hit", ship_mdb.index("R_blank") < ship_mdb.index("R_hit"))
check("ship max_doubles: U_acc before R_hit", ship_mdb.index("U_acc") < ship_mdb.index("R_hit"))
check("ship max_doubles: R_hit before R_crit", ship_mdb.index("R_hit") < ship_mdb.index("R_crit"))
check("ship max_doubles: R_hit+hit not in list (kept unconditionally)", "R_hit+hit" not in ship_mdb)
check("ship max_doubles: B_hit+crit not in list (kept unconditionally)", "B_hit+crit" not in ship_mdb)

# max_accuracy: acc faces not listed (kept); blue hits rerolled before red hits; no black faces
ship_ma = STRATEGY_PRIORITY_LISTS["ship"]["max_accuracy"]
check("ship max_accuracy: R_blank before R_hit", ship_ma.index("R_blank") < ship_ma.index("R_hit"))
check("ship max_accuracy: U_hit before R_hit (blue rerolled first)", ship_ma.index("U_hit") < ship_ma.index("R_hit"))
check("ship max_accuracy: U_crit before R_crit (blue rerolled first)", ship_ma.index("U_crit") < ship_ma.index("R_crit"))
check("ship max_accuracy: R_acc not in list (kept unconditionally)", "R_acc" not in ship_ma)
check("ship max_accuracy: U_acc not in list (kept unconditionally)", "U_acc" not in ship_ma)
check("ship max_accuracy: B_blank not in list (black faces excluded)", "B_blank" not in ship_ma)
check("ship max_accuracy: B_hit not in list (black faces excluded)", "B_hit" not in ship_ma)
check("ship max_accuracy: B_hit+crit not in list (black faces excluded)", "B_hit+crit" not in ship_ma)

# max_crits: blanks and acc and hits are candidates; crits and doubles kept
ship_mc = STRATEGY_PRIORITY_LISTS["ship"]["max_crits"]
check("ship max_crits: R_blank before R_hit", ship_mc.index("R_blank") < ship_mc.index("R_hit"))
check("ship max_crits: U_acc before R_hit", ship_mc.index("U_acc") < ship_mc.index("R_hit"))
check("ship max_crits: R_crit not in list (kept unconditionally)", "R_crit" not in ship_mc)
check("ship max_crits: U_crit not in list (kept unconditionally)", "U_crit" not in ship_mc)
check("ship max_crits: R_hit+hit not in list (kept unconditionally)", "R_hit+hit" not in ship_mc)
check("ship max_crits: B_hit+crit not in list (kept unconditionally)", "B_hit+crit" not in ship_mc)

# ---------------------------------------------------------------------------
# 5.1 — Squad strategy ordering invariants (unchanged)
# ---------------------------------------------------------------------------

for strategy in SQUAD_STRATEGIES:
    sq_pl = STRATEGY_PRIORITY_LISTS["squad"][strategy]
    check(
        f"squad {strategy}: R_crit before R_hit (zero-value face rerolled first)",
        sq_pl.index("R_crit") < sq_pl.index("R_hit"),
    )

# ---------------------------------------------------------------------------
# 5.1 — No duplicate faces within any strategy list
# ---------------------------------------------------------------------------

for type_str, strategies in (("ship", SHIP_STRATEGIES), ("squad", SQUAD_STRATEGIES)):
    for strategy in strategies:
        pl = STRATEGY_PRIORITY_LISTS[type_str][strategy]
        check(
            f"{type_str} {strategy}: no duplicate faces",
            len(pl) == len(set(pl)),
            f"duplicates={[f for f in pl if pl.count(f) > 1]}",
        )

# ---------------------------------------------------------------------------
# 5.2 — build_strategy_pipeline
# ---------------------------------------------------------------------------

ship_all_faces = [
    "R_blank", "B_blank", "R_acc", "U_acc",
    "R_hit", "U_hit", "B_hit", "R_crit", "U_crit",
    "R_hit+hit", "B_hit+crit",
]

base_pipeline = [
    Operation(type="reroll", count=2, applicable_results=ship_all_faces),
    Operation(type="add_dice", dice_to_add={"black": 1}),
    Operation(type="cancel", count=1, applicable_results=ship_all_faces),
]

result = build_strategy_pipeline(base_pipeline, "max_damage", "ship")
expected_list = STRATEGY_PRIORITY_LISTS["ship"]["max_damage"]

check(
    "build_strategy_pipeline: reroll priority_list matches strategy (all faces applicable)",
    result[0].priority_list == expected_list,
    f"got={result[0].priority_list}",
)
check("build_strategy_pipeline: reroll count preserved", result[0].count == 2)
check(
    "build_strategy_pipeline: reroll applicable_results not mutated",
    set(result[0].applicable_results) == set(ship_all_faces),
)
check(
    "build_strategy_pipeline: add_dice dice_to_add unchanged",
    result[1].dice_to_add == {"black": 1},
)
check(
    "build_strategy_pipeline: cancel priority_list matches strategy",
    result[2].priority_list == expected_list,
)
check(
    "build_strategy_pipeline: original pipeline not mutated",
    set(base_pipeline[0].applicable_results) == set(ship_all_faces),
)
check("build_strategy_pipeline: returns new list", result is not base_pipeline)

# applicable_results restricts priority_list to intersection with strategy
blanks_only = [Operation(type="reroll", count=1, applicable_results=["R_blank", "B_blank"])]
result_blanks = build_strategy_pipeline(blanks_only, "max_damage", "ship")
check(
    "build_strategy_pipeline: priority_list filtered to applicable_results",
    result_blanks[0].priority_list == ["R_blank", "B_blank"],
)
check(
    "build_strategy_pipeline: faces not in strategy excluded from priority_list",
    "R_hit" not in result_blanks[0].priority_list,
)

# Faces in applicable_results but not in strategy list → excluded from priority_list
hits_and_blanks = [Operation(type="reroll", count=1, applicable_results=["R_hit", "R_blank", "B_blank"])]
result_h = build_strategy_pipeline(hits_and_blanks, "max_damage", "ship")
check(
    "build_strategy_pipeline: max_damage excludes R_hit (not in strategy list)",
    "R_hit" not in result_h[0].priority_list,
)
check(
    "build_strategy_pipeline: max_damage keeps R_blank and B_blank",
    set(result_h[0].priority_list) == {"R_blank", "B_blank"},
)

# Strategy order preserved within filtered priority_list
hits_and_blanks2 = [Operation(type="reroll", count=1, applicable_results=["R_hit", "R_blank", "B_blank"])]
result_h2 = build_strategy_pipeline(hits_and_blanks2, "max_doubles", "ship")
check(
    "build_strategy_pipeline: max_doubles strategy order preserved — blanks before hits",
    result_h2[0].priority_list.index("R_blank") < result_h2[0].priority_list.index("R_hit"),
)

# add_dice-only pipeline passes through unchanged
add_only = [Operation(type="add_dice", count=1, applicable_results=["B_blank"])]
result2 = build_strategy_pipeline(add_only, "max_accuracy", "ship")
check(
    "build_strategy_pipeline: add_dice applicable_results unchanged",
    result2[0].applicable_results == ["B_blank"],
)

# ---------------------------------------------------------------------------
# 5.3 — generate_report
# ---------------------------------------------------------------------------

pool = DicePool(red=2, blue=1, black=0, type="ship")

# add_dice-only pipeline
no_prio_pipeline = [Operation(type="add_dice", dice_to_add={"black": 1})]
variants = generate_report(pool, no_prio_pipeline, ["max_damage"])
check("generate_report: 1 variant for 1 strategy", len(variants) == 1)
check("generate_report: variant label is strategy name", variants[0]["label"] == "max_damage")
check(
    "generate_report: variant has damage/accuracy/crit keys",
    all(k in variants[0] for k in ("damage", "accuracy", "crit")),
)
check("generate_report: cumulative_damage[0] == (0, 1.0)", variants[0]["damage"][0] == (0, 1.0))

# All four ship strategies produce valid variants
pool_rb = DicePool(red=2, blue=1, black=1, type="ship")
prio_pipeline = [Operation(type="reroll", count=1, applicable_results=["R_blank", "B_blank", "R_acc", "U_acc", "R_hit", "U_hit", "B_hit", "R_crit", "U_crit"])]
all_ship_strategies = ["max_damage", "max_doubles", "max_accuracy", "max_crits"]
variants2 = generate_report(pool_rb, prio_pipeline, all_ship_strategies)
check("generate_report: 4 variants for 4 ship strategies", len(variants2) == 4)
check(
    "generate_report: variant labels match strategies",
    [v["label"] for v in variants2] == all_ship_strategies,
)
for v in variants2:
    check(f"generate_report: {v['label']} damage[0] == (0, 1.0)", v["damage"][0] == (0, 1.0))
    check(f"generate_report: {v['label']} crit in [0,1]", 0.0 <= v["crit"] <= 1.0)

# max_damage keeps hits → higher damage than max_accuracy (which rerolls hits)
pool_rd = DicePool(red=2, blue=1, black=0, type="ship")
cmp_pipeline = [Operation(type="reroll", count=1, applicable_results=["R_blank", "R_acc", "U_acc", "R_hit", "U_hit", "U_crit"])]
cmp_variants = generate_report(pool_rd, cmp_pipeline, ["max_damage", "max_accuracy"])
dmg_md = cmp_variants[0]["damage"]
dmg_ma = cmp_variants[1]["damage"]
check(
    "generate_report: max_damage P(dmg>=1) >= max_accuracy P(dmg>=1)",
    dmg_md[1][1] >= dmg_ma[1][1],
)

# max_doubles keeps doubles → higher max damage threshold than max_damage
pool_r = DicePool(red=3, blue=0, black=0, type="ship")
dbl_pipeline = [Operation(type="reroll", count=2, applicable_results=["R_blank", "R_acc", "R_hit", "R_crit"])]
dbl_variants = generate_report(pool_r, dbl_pipeline, ["max_damage", "max_doubles"])
# max_doubles rerolls crits too (keeping R_hit+hit), so should have higher top-end damage
dbl_md = dbl_variants[0]["damage"]
dbl_mdb = dbl_variants[1]["damage"]
check(
    "generate_report: max_doubles max damage threshold >= max_damage max damage threshold",
    dbl_mdb[-1][0] >= dbl_md[-1][0],
)

# Unknown strategy raises ValueError
try:
    generate_report(pool_rb, prio_pipeline, ["unknown_strategy"])
    check("generate_report: unknown strategy raises ValueError", False)
except ValueError:
    check("generate_report: unknown strategy raises ValueError", True)

# Default strategy is max_damage
default_variants = generate_report(pool_rb, prio_pipeline)
check("generate_report: default → 1 variant", len(default_variants) == 1)
check("generate_report: default label is max_damage", default_variants[0]["label"] == "max_damage")

# Empty pipeline
empty_variants = generate_report(pool_rb, [], ["max_damage"])
check("generate_report: empty pipeline → 1 variant", len(empty_variants) == 1)
check("generate_report: empty pipeline label is strategy name", empty_variants[0]["label"] == "max_damage")

# ---------------------------------------------------------------------------
print(f"\n{'='*40}")
print(f"Results: {PASS} passed, {FAIL} failed")
