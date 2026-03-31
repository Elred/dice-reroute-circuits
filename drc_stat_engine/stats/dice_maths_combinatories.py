"""
dice_maths_combinatories.py — Core dice roll mathematics.

Handles all DataFrame-level operations on roll distributions:
- Building single-die DataFrames from profiles
- Combining multiple dice into a joint distribution
- Mutating a roll distribution (reroll, cancel, add dice, set die face)
- Utility functions for parsing and manipulating roll value strings

All functions accept and return a roll DataFrame with columns:
    value   — space-separated sorted string of individual die face results
    proba   — probability of this outcome
    damage  — total damage for this outcome
    crit    — total crits for this outcome
    acc     — total accuracy tokens for this outcome
    blank   — total blanks for this outcome
"""

from ctypes import ArgumentError

import numpy as np
import pandas as pd

from drc_stat_engine.stats.profiles import (
    black_die_ship, black_die_squad,
    blue_die_ship, blue_die_squad,
    red_die_ship, red_die_squad,
)


# ---------------------------------------------------------------------------
# Profile lookup helpers
# ---------------------------------------------------------------------------

def dice_to_dataframe(dice_profile):
    """Convert a die profile list of dicts into a roll DataFrame."""
    return pd.DataFrame(dice_profile)


def dice_to_dict(dice_profile):
    """Convert a die profile list into a {value: attrs} lookup dict."""
    return {
        die_result["value"]: {
            "proba":  die_result["proba"],
            "damage": die_result["damage"],
            "crit":   die_result["crit"],
            "acc":    die_result["acc"],
            "blank":  die_result["blank"],
        }
        for die_result in dice_profile
    }


def value_to_dice_attr_dict(value_str, type_str):
    """Return the attribute dict for a single die face value string."""
    if type_str == "ship":
        for profile in (red_die_ship, blue_die_ship, black_die_ship):
            lookup = dice_to_dict(profile)
            if value_str in lookup:
                return lookup[value_str]
    elif type_str == "squad":
        for profile in (red_die_squad, blue_die_squad, black_die_squad):
            lookup = dice_to_dict(profile)
            if value_str in lookup:
                return lookup[value_str]
    raise ArgumentError(f"value {value_str} not found in dice profiles")


def value_to_dice_count_dict(value_str, type_str="ship"):
    """Return {"red": n, "blue": n, "black": n} for the dice in a value string."""
    dice_result_list = value_str.split(" ")
    if type_str == "ship":
        red_die, blue_die, black_die = red_die_ship, blue_die_ship, black_die_ship
    elif type_str == "squad":
        red_die, blue_die, black_die = red_die_squad, blue_die_squad, black_die_squad
    red_values   = {x["value"] for x in red_die}
    blue_values  = {x["value"] for x in blue_die}
    black_values = {x["value"] for x in black_die}
    return {
        "red":   sum(1 for r in dice_result_list if r in red_values),
        "blue":  sum(1 for r in dice_result_list if r in blue_values),
        "black": sum(1 for r in dice_result_list if r in black_values),
    }


def value_to_dice_count_str(value_str, type_str="ship"):
    """Return a human-readable dice count string like '2R,1U,0B'."""
    counts = value_to_dice_count_dict(value_str, type_str)
    return f"{counts['red']}R,{counts['blue']}U,{counts['black']}B"


# ---------------------------------------------------------------------------
# Value string utilities
# ---------------------------------------------------------------------------

def value_str_to_list(value_str):
    """Split a space-separated value string into a list of face tokens."""
    return value_str.split(" ")


def value_list_to_str(value_list):
    """Join and sort a list of face tokens into a canonical value string."""
    return " ".join(sorted(value_list))


def clean_value_str(value_str):
    """Strip leading or trailing spaces from a value string."""
    return value_str.strip()


# ---------------------------------------------------------------------------
# Roll combination
# ---------------------------------------------------------------------------

def combine_two(roll_df_a, roll_df_b):
    """
    Compute the joint distribution of two independent roll DataFrames via
    a cross join, then aggregate rows that share the same value string.
    """
    comb_df = pd.merge(roll_df_a, roll_df_b, how="cross")
    comb_df["value"]  = comb_df[["value_x", "value_y"]].apply(
        lambda x: clean_value_str(" ".join(sorted(x))), axis=1
    )
    comb_df["proba"]  = comb_df["proba_x"]  * comb_df["proba_y"]
    comb_df["damage"] = comb_df["damage_x"] + comb_df["damage_y"]
    comb_df["crit"]   = comb_df["crit_x"]   + comb_df["crit_y"]
    comb_df["acc"]    = comb_df["acc_x"]    + comb_df["acc_y"]
    comb_df["blank"]  = comb_df["blank_x"]  + comb_df["blank_y"]
    comb_df = comb_df[["value", "proba", "damage", "crit", "acc", "blank"]]
    return comb_df.groupby("value", as_index=False).agg({
        "proba":  "sum",
        "damage": "first",
        "crit":   "first",
        "acc":    "first",
        "blank":  "first",
    })


def combine_dice(red_dice: int = 0, blue_dice: int = 0, black_dice: int = 0, type_str: str = "ship"):
    """
    Build the joint roll distribution for a pool of red, blue, and black dice.
    Returns a roll DataFrame representing all possible outcomes and their probabilities.
    """
    if type_str == "ship":
        red_die, blue_die, black_die = red_die_ship, blue_die_ship, black_die_ship
    elif type_str == "squad":
        red_die, blue_die, black_die = red_die_squad, blue_die_squad, black_die_squad

    red_range   = range(0, red_dice)
    blue_range  = range(red_dice, red_dice + blue_dice)
    black_range = range(red_dice + blue_dice, red_dice + blue_dice + black_dice)

    roll_df = None
    for idx in range(red_dice + blue_dice + black_dice):
        if idx == 0:
            if red_range:
                roll_df = dice_to_dataframe(red_die)
                continue
            if blue_range:
                roll_df = dice_to_dataframe(blue_die)
                continue
            if black_range:
                roll_df = dice_to_dataframe(black_die)
                continue
        else:
            if idx in red_range:
                roll_df = combine_two(roll_df, dice_to_dataframe(red_die))
            if idx in blue_range:
                roll_df = combine_two(roll_df, dice_to_dataframe(blue_die))
            if idx in black_range:
                roll_df = combine_two(roll_df, dice_to_dataframe(black_die))
    return roll_df


# ---------------------------------------------------------------------------
# Roll mutation helpers
# ---------------------------------------------------------------------------

def _remove_each(faces, to_remove):
    """Remove one occurrence at a time from *faces* for each entry in *to_remove*."""
    remaining = list(faces)
    for face in to_remove:
        remaining.remove(face)
    return " ".join(sorted(remaining))


def remove_dice_from_roll(roll_df, to_remove_dice, type_str="ship"):
    """
    Split roll_df into two parts:
    - removed_df: rows where the specified dice were removed (stats adjusted)
    - kept_df:    rows where no dice matched (unchanged)

    to_remove_dice is a Series aligned with roll_df where each entry is either
    a list of face tokens to remove, or NaN for rows that should be kept.
    """
    kept_df    = roll_df.copy()
    removed_df = roll_df.copy()
    removed_df["removed_dice"] = to_remove_dice
    removed_df = removed_df[
        removed_df["removed_dice"].apply(lambda x: isinstance(x, list))
    ]

    if removed_df.empty:
        kept_df = kept_df.drop("removed_dice", axis=1) if "removed_dice" in kept_df.columns else kept_df
        return removed_df, roll_df.copy()

    for stat in ("damage", "crit", "acc", "blank"):
        removed_df[f"to_remove_{stat}"] = removed_df.apply(
            lambda x: sum(value_to_dice_attr_dict(v, type_str)[stat] for v in x["removed_dice"]),
            axis=1,
        )

    removed_df["value"] = removed_df.apply(
        lambda x: _remove_each(value_str_to_list(x["value"]), x["removed_dice"]),
        axis=1,
    )
    for stat in ("damage", "crit", "acc", "blank"):
        removed_df[stat] = removed_df[stat] - removed_df[f"to_remove_{stat}"]
    removed_df = removed_df.drop(
        [f"to_remove_{s}" for s in ("damage", "crit", "acc", "blank")], axis=1
    )
    removed_df["removed_dice"] = removed_df["removed_dice"].apply(value_list_to_str)

    kept_df = roll_df.copy()
    kept_df["removed_dice"] = to_remove_dice
    kept_df = kept_df[kept_df["removed_dice"].apply(lambda x: not isinstance(x, list))]
    kept_df = kept_df.drop("removed_dice", axis=1)
    return removed_df, kept_df


def add_dice_to_roll(roll_df, red: int = 0, blue: int = 0, black: int = 0, type_str: str = "ship"):
    """Add fresh dice of the given color counts to the roll and combine distributions."""
    if red == 0 and blue == 0 and black == 0:
        return roll_df
    new_dice_df = combine_dice(red, blue, black, type_str)
    return combine_two(roll_df, new_dice_df)


def reroll_dice(roll_df, results_to_reroll="blanks", reroll_count=1, type_str="ship"):
    """
    Reroll up to reroll_count dice showing faces in results_to_reroll (priority order).
    Returns (rerolled_df, initial_roll_df).
    """
    if results_to_reroll == "blanks":
        results_to_reroll = ["B_blank", "R_blank"]
    initial_roll_df = roll_df.copy()

    dice_to_reroll = (
        roll_df["value"]
        .apply(value_str_to_list)
        .apply(lambda roll: sorted(
            [r for r in roll if r in results_to_reroll],
            key=lambda n: results_to_reroll.index(n),
        )[:reroll_count])
        .apply(lambda roll: roll if roll else np.nan)
        .dropna()
    )
    rr_df, no_rr_df = remove_dice_from_roll(roll_df, dice_to_reroll, type_str)

    if rr_df.empty:
        return initial_roll_df, initial_roll_df

    # Group by dice-count composition (r,u,b) rather than exact face string.
    # Many distinct removed_dice strings share the same color counts (e.g.
    # "R_blank R_blank" and "R_hit R_blank" both yield 2R,0U,0B when rerolling
    # blanks). Grouping this way reduces the number of combine_two cross-joins
    # from O(unique face combos) to O(unique color-count combos), which is much
    # smaller for large pools.
    rr_df["_dice_key"] = rr_df["removed_dice"].apply(
        lambda s: tuple(value_to_dice_count_dict(s, type_str)[c] for c in ("red", "blue", "black"))
    )
    rrd_df_list = []
    for dice_key, group_df in rr_df.groupby("_dice_key"):
        r, u, b = dice_key
        sub_df = add_dice_to_roll(
            group_df.drop(columns=["_dice_key"]),
            red=r,
            blue=u,
            black=b,
            type_str=type_str,
        )
        rrd_df_list.append(sub_df)
    rr_df = rr_df.drop(columns=["_dice_key"])

    rerolled_df = pd.concat([no_rr_df] + rrd_df_list)
    return rerolled_df.groupby("value", as_index=False).agg({
        "proba":  "sum",
        "damage": "first",
        "crit":   "first",
        "acc":    "first",
        "blank":  "first",
    }), initial_roll_df


def cancel_dice(roll_df, results_to_cancel="blanks", cancel_count=1, type_str="ship"):
    """
    Cancel up to cancel_count dice showing faces in results_to_cancel (priority order).
    Returns (cancelled_df, kept_df).
    """
    if results_to_cancel == "blanks":
        results_to_cancel = ["B_blank", "R_blank"]
    initial_roll_df = roll_df.copy()

    dice_to_cancel = (
        roll_df["value"]
        .apply(value_str_to_list)
        .apply(lambda roll: sorted(
            [r for r in roll if r in results_to_cancel],
            key=lambda n: results_to_cancel.index(n),
        )[:cancel_count])
        .apply(lambda roll: roll if roll else np.nan)
        .dropna()
    )
    if dice_to_cancel.empty:
        return roll_df.iloc[0:0].copy(), initial_roll_df

    return remove_dice_from_roll(roll_df, dice_to_cancel, type_str)


# ---------------------------------------------------------------------------
# Set die face
# ---------------------------------------------------------------------------

def _all_pool_results(type_str: str) -> list:
    """Return all result dicts for the given type_str across all colors."""
    if type_str == "ship":
        return red_die_ship + blue_die_ship + black_die_ship
    elif type_str == "squad":
        return red_die_squad + blue_die_squad + black_die_squad
    return []


def _resolve_color_agnostic_result(target_result: str, type_str: str) -> str:
    """
    Resolve a color-agnostic result type (e.g. 'hit') to the best color-specific
    result in the pool for type_str. Best = highest damage+crit+acc score; ties
    broken by damage desc, crit desc, acc desc.
    Raises ValueError if no matching result is found.
    """
    all_results = _all_pool_results(type_str)
    candidates = [f for f in all_results if f["value"].split("_", 1)[-1] == target_result]
    if not candidates:
        raise ValueError(
            f"Color-agnostic target '{target_result}' has no matching result "
            f"in pool for type '{type_str}'."
        )
    return max(candidates, key=lambda f: (
        f["damage"] + f["crit"] + f["acc"],
        f["damage"],
        f["crit"],
        f["acc"],
    ))["value"]


def change_die_face(
    roll_df: "pd.DataFrame",
    source_results: list,
    target_result: str,
    type_str: str = "ship",
) -> "pd.DataFrame":
    """
    Force one die in each outcome to show target_result, replacing the
    highest-priority source result found in that outcome.

    - source_results: ordered list of eligible source result strings (highest priority first).
    - target_result: the result to substitute in. Color-agnostic (no '_') → resolved to
      the best color-specific result in the pool.
    - Returns roll_df unchanged when no outcome contains any result from source_results.
    """
    if not source_results:
        return roll_df

    if "_" not in target_result:
        target_result = _resolve_color_agnostic_result(target_result, type_str)

    # Color-presence guard: if the target color is not in the pool, return unchanged
    target_color = target_result.split("_", 1)[0]
    all_tokens = {token for value_str in roll_df["value"] for token in value_str.split(" ")}
    if not any(t.startswith(target_color + "_") for t in all_tokens):
        return roll_df

    target_attrs = value_to_dice_attr_dict(target_result, type_str)

    result_rows = []
    for _, row in roll_df.iterrows():
        tokens = value_str_to_list(row["value"])
        matched_source = next((sf for sf in source_results if sf in tokens), None)

        if matched_source is None:
            result_rows.append(row.to_dict())
            continue

        source_attrs = value_to_dice_attr_dict(matched_source, type_str)
        new_tokens = tokens.copy()
        new_tokens.remove(matched_source)
        new_tokens.append(target_result)

        result_rows.append({
            "value":  value_list_to_str(new_tokens),
            "proba":  row["proba"],
            "damage": row["damage"] - source_attrs["damage"] + target_attrs["damage"],
            "crit":   row["crit"]   - source_attrs["crit"]   + target_attrs["crit"],
            "acc":    row["acc"]    - source_attrs["acc"]     + target_attrs["acc"],
            "blank":  row["blank"]  - source_attrs["blank"]   + target_attrs["blank"],
        })

    result_df = pd.DataFrame(result_rows, columns=["value", "proba", "damage", "crit", "acc", "blank"])
    return result_df.groupby("value", as_index=False).agg({
        "proba":  "sum",
        "damage": "first",
        "crit":   "first",
        "acc":    "first",
        "blank":  "first",
    })


# ---------------------------------------------------------------------------
# Analysis helpers (used in dice.py main() and legacy callers)
# ---------------------------------------------------------------------------

def filter_roll_for_value(roll_df, dice_result_str):
    roll_df["val_to_check"] = dice_result_str
    roll_df["contains"] = roll_df.apply(
        lambda x: all(val in x["value"].split(" ") for val in x["val_to_check"].split(" ")),
        axis=1,
    )
    roll_df = roll_df.drop("val_to_check", axis=1)
    result = roll_df[roll_df["contains"]].drop("contains", axis=1)
    return result


def filter_roll(roll_df, conditions_dict):
    for key, condition in conditions_dict.items():
        if key == "value":
            dice_result = condition["result"]
            roll_df = pd.concat([
                filter_roll_for_value(roll_df, val) for val in dice_result
            ]).drop_duplicates().reset_index(drop=True)
        else:
            amount   = condition["amount"]
            operator = condition["operator"]
            ops = {
                "lt":  lambda df, k, v: df[df[k] < v],
                "lte": lambda df, k, v: df[df[k] <= v],
                "gt":  lambda df, k, v: df[df[k] > v],
                "gte": lambda df, k, v: df[df[k] >= v],
                "eq":  lambda df, k, v: df[df[k] == v],
                "neq": lambda df, k, v: df[df[k] != v],
            }
            if operator in ops:
                roll_df = ops[operator](roll_df, key, amount)
    return roll_df


def average_damage(roll_df):
    """Return E[damage] and print it."""
    avg_dmg = (roll_df["damage"] * roll_df["proba"]).sum()
    print(f"average damage for roll: {avg_dmg}")
    return avg_dmg


def roll_proba(roll_df):
    """Return the total probability mass of a (filtered) roll and print it."""
    proba = roll_df["proba"].sum()
    print(f"proba for roll: {proba * 100}%")
    return proba


# ---------------------------------------------------------------------------
# Scenario runner (kept for direct module execution)
# ---------------------------------------------------------------------------

def main():
    type_str = "ship"
    sato_cancel_priority = [
        "R_blank", "B_blank", "R_acc", "U_acc",
        "R_hit", "U_hit", "B_hit", "R_crit", "U_crit",
        "R_hit+hit", "B_hit+crit",
    ]

    print("#########")
    print("Scenario: Salvation + OLD Sato")
    print("Step 1) Initial roll: 1 red 2 black dice")
    roll_df = combine_dice(1, 0, 2, type_str)
    average_damage(roll_df)

    print("#########")
    print("Scenario: Salvation + ARC Sato")
    print("Step 1) Initial roll: 3 red dice")
    roll_df = combine_dice(3, 0, 0, type_str)
    average_damage(roll_df)

    print("\nStep 2) Sato 2 black dice")
    roll_df = add_dice_to_roll(roll_df, red=0, blue=0, black=2, type_str=type_str)
    roll_df, _ = cancel_dice(roll_df, sato_cancel_priority, 2, type_str)
    average_damage(roll_df)


if __name__ == "__main__":
    main()
