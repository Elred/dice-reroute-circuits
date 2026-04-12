"""
strategies.py — Strategy definitions and pipeline resolution.

Defines the priority lists for each strategy (per dice type), and the
build_strategy_pipeline function that resolves an abstract pipeline into
a concrete one ready for execution.
"""

from typing import List

from drc_stat_engine.stats.dice_models import AttackEffect
from drc_stat_engine.stats.profiles import (
    red_die_ship, blue_die_ship, black_die_ship,
    red_die_squad, blue_die_squad, black_die_squad,
)

ALL_FACES = {
    "ship": [f["value"] for f in red_die_ship + blue_die_ship + black_die_ship],
    "squad": [f["value"] for f in red_die_squad + blue_die_squad + black_die_squad],
}


# ---------------------------------------------------------------------------
# Strategy priority lists (per dice type)
# Requirements: 6.2, 6.3, 6.4
# ---------------------------------------------------------------------------
#
# Priority order = reroll/cancel lowest-value faces first.
# Ship face attributes (for reference):
#   R_blank:    damage=0, crit=0, acc=0  (blank)
#   B_blank:    damage=0, crit=0, acc=0  (blank)
#   R_acc:      damage=0, crit=0, acc=1
#   U_acc:      damage=0, crit=0, acc=1
#   R_hit:      damage=1, crit=0, acc=0
#   U_hit:      damage=1, crit=0, acc=0
#   B_hit:      damage=1, crit=0, acc=0
#   R_crit:     damage=1, crit=1, acc=0
#   U_crit:     damage=1, crit=1, acc=0
#   R_hit+hit:  damage=2, crit=0, acc=0
#   B_hit+crit: damage=2, crit=1, acc=0
#
# Squad face attributes (key differences):
#   R_crit:     damage=0, crit=0, acc=0  (worthless face for squad)
#   U_crit:     damage=0, crit=0, acc=0  (worthless face for squad)
#   B_hit+crit: damage=1, crit=0, acc=0  (no crit for squad)

STRATEGY_PRIORITY_LISTS = {
    "ship": {
        # Exposed strategies: max_damage, balanced, black_doubles, max_accuracy_blue
        "max_damage": {
            "reroll": ["R_blank", "B_blank", "U_acc", "R_acc"],
            "change_die": {
                "hit":    ["R_blank", "B_blank", "U_acc", "R_acc"],
                "acc":    ["R_blank", "B_blank"],
                "double": ["R_blank", "B_blank", "U_acc", "R_acc", "U_hit", "B_hit", "R_hit", "U_crit", "R_crit"],
            },
            "cancel": ["R_blank", "B_blank", "U_acc", "R_acc", "U_hit", "B_hit", "R_hit", "U_crit", "R_crit", "R_hit+hit", "B_hit+crit"],
        },
        "balanced": {
            "reroll": ["R_blank", "B_blank"],
            "change_die": {
                "hit":    ["R_blank", "B_blank"],
                "acc":    ["R_blank", "B_blank"],
                "double": ["R_blank", "B_blank", "U_acc", "R_acc", "U_hit", "B_hit", "R_hit", "U_crit", "R_crit"],
            },
            "cancel": ["R_blank", "B_blank", "U_acc", "R_acc", "U_hit", "B_hit", "R_hit", "U_crit", "R_crit", "R_hit+hit", "B_hit+crit"],
        },
        # black_doubles: balanced + reroll black hits to find doubles
        "black_doubles": {
            "reroll": ["R_blank", "B_blank", "B_hit"],
            "change_die": {
                "hit":    ["R_blank", "B_blank", "U_acc", "R_acc"],
                "acc":    ["R_blank", "B_blank"],
                "double": ["R_blank", "B_blank", "U_acc", "R_acc", "U_hit", "B_hit", "R_hit", "U_crit", "R_crit"],
            },
            "cancel": ["R_blank", "B_blank", "U_acc", "R_acc", "U_hit", "B_hit", "R_hit", "U_crit", "R_crit", "R_hit+hit", "B_hit+crit"],
        },
        # max_accuracy_blue: reroll blue hits/crits to fish for accuracy tokens
        "max_accuracy_blue": {
            "reroll": ["R_blank", "B_blank", "U_hit", "U_crit"],
            "change_die": {
                "hit":    ["R_blank", "B_blank", "U_acc", "R_acc"],
                "acc":    ["R_blank", "B_blank", "U_hit", "U_crit"],
                "double": ["R_blank", "B_blank", "U_acc", "R_acc", "U_hit", "B_hit", "R_hit", "U_crit", "R_crit"],
            },
            "cancel": ["R_blank", "B_blank", "U_hit", "B_hit", "R_hit", "U_crit", "R_crit", "U_acc", "R_acc", "R_hit+hit", "B_hit+crit"],
        },
    },
    "squad": {
        # Exposed strategies: max_damage, balanced, max_accuracy_blue (no black_doubles for squad)
        # Squad face attributes (key differences from ship):
        #   R_crit / U_crit: damage=0 (worthless — treat like blank)
        #   B_hit+crit:      damage=1, no crit
        "max_damage": {
            "reroll": ["R_blank", "B_blank", "R_crit", "U_crit", "R_acc", "U_acc"],
            "change_die": {
                "hit":    ["R_blank", "B_blank", "R_crit", "U_crit", "R_acc", "U_acc"],
                "acc":    ["R_blank", "B_blank", "R_crit", "U_crit"],
                "double": ["R_blank", "B_blank", "R_crit", "U_crit", "R_acc", "U_acc", "R_hit", "U_hit", "B_hit"],
            },
            "cancel": ["R_blank", "B_blank", "R_crit", "U_crit", "R_acc", "U_acc", "R_hit", "U_hit", "B_hit", "B_hit+crit", "R_hit+hit"],
        },
        "balanced": {
            "reroll": ["R_blank", "B_blank", "R_crit", "U_crit"],
            "change_die": {
                "hit":    ["R_blank", "B_blank", "R_crit", "U_crit"],
                "acc":    ["R_blank", "B_blank", "R_crit", "U_crit"],
                "double": ["R_blank", "B_blank", "R_crit", "U_crit", "R_acc", "U_acc", "R_hit", "U_hit", "B_hit"],
            },
            "cancel": ["R_blank", "B_blank", "R_crit", "U_crit", "R_acc", "U_acc", "R_hit", "U_hit", "B_hit", "B_hit+crit", "R_hit+hit"],
        },
        "max_accuracy_blue": {
            "reroll": ["R_blank", "B_blank", "R_crit", "U_crit", "U_hit"],
            "change_die": {
                "hit":    ["R_blank", "B_blank", "R_crit", "U_crit", "R_acc", "U_acc"],
                "acc":    ["R_blank", "B_blank", "R_crit", "U_crit", "U_hit"],
                "double": ["R_blank", "B_blank", "R_crit", "U_crit", "R_acc", "U_acc", "R_hit", "U_hit", "B_hit"],
            },
            "cancel": ["R_blank", "B_blank", "R_crit", "U_crit", "U_hit", "R_hit", "B_hit", "R_acc", "U_acc", "B_hit+crit", "R_hit+hit"],
        },
    },
}

# Attack effect types that require a resolved priority_list before execution
PRIORITY_DEPENDENT_OPS = {"reroll", "cancel", "change_die", "reroll_all"}


# ---------------------------------------------------------------------------
# Strategy pipeline builder
# Requirements: 6.1, 6.5
# ---------------------------------------------------------------------------

def build_strategy_pipeline(
    pipeline: List[AttackEffect],
    strategy: str,
    type_str: str,
) -> List[AttackEffect]:
    """
    Return a copy of the pipeline with priority_list resolved on all
    priority-dependent attack effects (reroll, cancel, change_die).

    The resolved priority_list = strategy ordering filtered to faces in
    applicable_results, preserving the strategy's order.
    applicable_results is never modified.

    Non-priority-dependent attack effects (add_dice) are passed through unchanged.
    Requirements: 6.1, 6.5
    """
    strategy_lists = STRATEGY_PRIORITY_LISTS[type_str][strategy]
    result = []

    for op in pipeline:
        if op.type in PRIORITY_DEPENDENT_OPS:
            if op.type == "reroll_all":
                all_faces = ALL_FACES[type_str]
                result.append(AttackEffect(
                    type=op.type,
                    count=op.count,
                    applicable_results=list(all_faces),
                    priority_list=list(all_faces),
                    condition=op.condition,
                ))
                continue
            elif op.type == "change_die":
                # For change_die, use applicable_results directly as the priority ordering
                # when the user has specified them; otherwise fall back to the strategy's
                # change_die sub-key list derived from the target result suffix.
                if op.applicable_results:
                    resolved = list(op.applicable_results)
                else:
                    suffix = (op.target_result or "").split("_", 1)[-1]
                    if suffix in ("hit+hit", "hit+crit"):
                        sub_key = "double"
                    elif suffix == "acc":
                        sub_key = "acc"
                    else:
                        sub_key = "hit"
                    resolved = list(strategy_lists["change_die"][sub_key])
            else:
                ordering = strategy_lists[op.type]  # "reroll" or "cancel"
                applicable_set = set(op.applicable_results)
                resolved = [face for face in ordering if face in applicable_set]

            result.append(AttackEffect(
                type=op.type,
                count=op.count,
                applicable_results=list(op.applicable_results),
                priority_list=resolved,
                target_result=op.target_result,
            ))
        else:
            result.append(AttackEffect(
                type=op.type,
                count=op.count,
                applicable_results=list(op.applicable_results),
                priority_list=list(op.priority_list),
                dice_to_add=dict(op.dice_to_add) if op.dice_to_add is not None else None,
            ))

    return result
