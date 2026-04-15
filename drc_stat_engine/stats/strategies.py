"""
strategies.py — Strategy definitions and pipeline resolution.

Defines the priority lists for each strategy (per dice type), and the
build_strategy_pipeline function that resolves an abstract pipeline into
a concrete one ready for execution.
"""

from typing import List

from drc_stat_engine.stats.dice_models import AttackEffect, DefenseEffect
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
            "color_priority": ["black", "red", "blue"],
        },
        "balanced": {
            "reroll": ["R_blank", "B_blank"],
            "change_die": {
                "hit":    ["R_blank", "B_blank"],
                "acc":    ["R_blank", "B_blank"],
                "double": ["R_blank", "B_blank", "U_acc", "R_acc", "U_hit", "B_hit", "R_hit", "U_crit", "R_crit"],
            },
            "cancel": ["R_blank", "B_blank", "U_acc", "R_acc", "U_hit", "B_hit", "R_hit", "U_crit", "R_crit", "R_hit+hit", "B_hit+crit"],
            "color_priority": ["red", "blue", "black"],
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
            "color_priority": ["black", "red", "blue"],
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
            "color_priority": ["blue", "red", "black"],
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
            "color_priority": ["red", "blue", "black"],
        },
        "balanced": {
            "reroll": ["R_blank", "B_blank", "R_crit", "U_crit"],
            "change_die": {
                "hit":    ["R_blank", "B_blank", "R_crit", "U_crit"],
                "acc":    ["R_blank", "B_blank", "R_crit", "U_crit"],
                "double": ["R_blank", "B_blank", "R_crit", "U_crit", "R_acc", "U_acc", "R_hit", "U_hit", "B_hit"],
            },
            "cancel": ["R_blank", "B_blank", "R_crit", "U_crit", "R_acc", "U_acc", "R_hit", "U_hit", "B_hit", "B_hit+crit", "R_hit+hit"],
            "color_priority": ["red", "blue", "black"],
        },
        "max_accuracy_blue": {
            "reroll": ["R_blank", "B_blank", "R_crit", "U_crit", "U_hit"],
            "change_die": {
                "hit":    ["R_blank", "B_blank", "R_crit", "U_crit", "R_acc", "U_acc"],
                "acc":    ["R_blank", "B_blank", "R_crit", "U_crit", "U_hit"],
                "double": ["R_blank", "B_blank", "R_crit", "U_crit", "R_acc", "U_acc", "R_hit", "U_hit", "B_hit"],
            },
            "cancel": ["R_blank", "B_blank", "R_crit", "U_crit", "U_hit", "R_hit", "B_hit", "R_acc", "U_acc", "B_hit+crit", "R_hit+hit"],
            "color_priority": ["blue", "red", "black"],
        },
    },
}

# ---------------------------------------------------------------------------
# Defense priority lists
# Requirements: 13.1, 13.2, 13.3, 13.4
# ---------------------------------------------------------------------------

DEFENSE_PRIORITY_LISTS = {
    "ship": {
        "defense_reroll": {
            "safe":           ["R_hit+hit", "B_hit+crit", "U_crit", "U_hit"],
            "gamble": ["R_hit+hit", "B_hit+crit", "R_crit", "R_hit", "U_crit", "U_hit", "B_hit"],
        },
        "defense_cancel": ["B_hit+crit", "R_hit+hit", "U_crit", "R_crit", "R_hit", "U_hit", "B_hit"],
    },
    "squad": {
        # Squad crits (R_crit, U_crit) are worthless (0 damage, 0 crit) — never reroll/cancel them.
        # B_hit+crit is only 1 damage for squad (no crit), so it's lower priority than R_hit+hit.
        "defense_reroll": {
            "safe":           ["R_hit+hit", "B_hit+crit", "B_hit", "U_hit"],
            "gamble": ["R_hit+hit", "R_hit", "U_hit", "B_hit", "B_hit+crit"],
        },
        "defense_cancel": ["R_hit+hit", "R_hit", "U_hit", "B_hit", "B_hit+crit"],
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

    Non-priority-dependent attack effects (add_dice, add_set_die) are passed
    through unchanged, with face_condition, color_in_pool, and color_priority
    preserved. When color_in_pool=True and no user-provided color_priority,
    the strategy's default color_priority is resolved.

    Requirements: 6.1, 6.5, 9.1, 9.2, 9.3, 9.6, 12.1, 12.2, 12.3, 12.4
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
        elif op.type == "add_set_die":
            # Pass through unchanged — no priority resolution needed.
            # Preserve face_condition and target_result as-is.
            result.append(AttackEffect(
                type=op.type,
                count=op.count,
                target_result=op.target_result,
                face_condition=op.face_condition,
            ))
        else:
            # add_dice (and any future non-priority-dependent ops)
            # Resolve color_priority from strategy default when color_in_pool=True
            # and no user-provided list.
            resolved_color_priority = op.color_priority
            if op.color_in_pool and not op.color_priority:
                resolved_color_priority = list(strategy_lists["color_priority"])

            result.append(AttackEffect(
                type=op.type,
                count=op.count,
                applicable_results=list(op.applicable_results),
                priority_list=list(op.priority_list),
                dice_to_add=dict(op.dice_to_add) if op.dice_to_add is not None else None,
                face_condition=op.face_condition,
                color_in_pool=op.color_in_pool,
                color_priority=list(resolved_color_priority) if resolved_color_priority is not None else None,
            ))

    return result


# ---------------------------------------------------------------------------
# Defense pipeline builder
# Requirements: 2.3, 2.5, 3.2, 3.4, 13.5
# ---------------------------------------------------------------------------

def build_defense_pipeline(pipeline: List[DefenseEffect], type_str: str = "ship") -> List[DefenseEffect]:
    """
    Return a copy of the pipeline with priority_list resolved on all
    defense_reroll and defense_cancel effects.

    For defense_reroll: looks up DEFENSE_PRIORITY_LISTS[type_str]["defense_reroll"][effect.mode].
    For defense_cancel: looks up DEFENSE_PRIORITY_LISTS[type_str]["defense_cancel"].

    If applicable_results is non-empty, the resolved priority_list is filtered
    to only include faces present in applicable_results, preserving priority ordering.

    reduce_damage and divide_damage effects are passed through unchanged (copied).
    """
    type_lists = DEFENSE_PRIORITY_LISTS[type_str]
    result = []

    for effect in pipeline:
        if effect.type == "defense_reroll":
            full_priority = type_lists["defense_reroll"][effect.mode]
            if effect.applicable_results:
                allowed = set(effect.applicable_results)
                resolved = [face for face in full_priority if face in allowed]
            else:
                resolved = list(full_priority)
            result.append(DefenseEffect(
                type=effect.type,
                count=effect.count,
                mode=effect.mode,
                amount=effect.amount,
                applicable_results=list(effect.applicable_results),
                priority_list=resolved,
            ))
        elif effect.type == "defense_cancel":
            full_priority = type_lists["defense_cancel"]
            if effect.applicable_results:
                allowed = set(effect.applicable_results)
                resolved = [face for face in full_priority if face in allowed]
            else:
                resolved = list(full_priority)
            result.append(DefenseEffect(
                type=effect.type,
                count=effect.count,
                mode=effect.mode,
                amount=effect.amount,
                applicable_results=list(effect.applicable_results),
                priority_list=resolved,
            ))
        else:
            # reduce_damage / divide_damage — pass through unchanged
            result.append(DefenseEffect(
                type=effect.type,
                count=effect.count,
                mode=effect.mode,
                amount=effect.amount,
                applicable_results=list(effect.applicable_results),
                priority_list=list(effect.priority_list),
            ))

    return result
