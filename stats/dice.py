from ctypes import ArgumentError
from profiles import red_die, blue_die, black_die
import pandas as pd
import numpy as np

def dice_to_dataframe(dice_profile):
    return pd.DataFrame(dice_profile)

def dice_to_dict(dice_profile):
    return {
        die_face["value"]: {
            "proba": die_face["proba"],
            "damage": die_face["damage"],
            "crit": die_face["crit"],
            "acc": die_face["acc"],
            "blank": die_face["blank"]
        } for die_face in dice_profile
    }

def value_to_dice_attr_dict(value_str):
    if value_str in dice_to_dict(red_die).keys():
        return dice_to_dict(red_die)[value_str]
    if value_str in dice_to_dict(blue_die).keys():
        return dice_to_dict(blue_die)[value_str]
    if value_str in dice_to_dict(black_die).keys():
        return dice_to_dict(black_die)[value_str]

def value_to_dice_count_dict(value_str):
    dice_result_list = value_str.split(" ")
    red_dice_count = len([res for res in dice_result_list if res in [x["value"] for x in red_die]])
    blue_dice_count = len([res for res in dice_result_list if res in [x["value"] for x in blue_die]])
    black_dice_count = len([res for res in dice_result_list if res in [x["value"] for x in black_die]])
    return {"red": red_dice_count, "blue": blue_dice_count, "black": black_dice_count}

def value_to_dice_count_str(value_str):
    dice_result_list = value_str.split(" ")
    red_dice_count = len([res for res in dice_result_list if res in [x["value"] for x in red_die]])
    blue_dice_count = len([res for res in dice_result_list if res in [x["value"] for x in blue_die]])
    black_dice_count = len([res for res in dice_result_list if res in [x["value"] for x in black_die]])
    return f"{red_dice_count}R,{blue_dice_count}U,{black_dice_count}B"

def value_str_to_list(value_str):
    return value_str.split(" ")

def value_list_to_str(value_list):
    return " ".join(sorted(value_list))

def clean_value_str(value_str):
    if value_str[0] == " ":
        return value_str[1:]
    if value_str[-1] == " ":
        return value_str[:-1]
    return value_str

def combine_two(roll_df_a, roll_df_b):
    comb_df = pd.merge(roll_df_a, roll_df_b, how="cross")
    comb_columns = ["value", "proba", "damage", "crit", "acc", "blank"]
    comb_df["value"] = comb_df[["value_x", "value_y"]].apply(lambda x: clean_value_str(" ".join(sorted(x))), axis=1)
    comb_df["proba"] = comb_df["proba_x"] * comb_df["proba_y"]
    comb_df["damage"] = comb_df["damage_x"] + comb_df["damage_y"]
    comb_df["crit"] = comb_df["crit_x"] + comb_df["crit_y"]
    comb_df["acc"] = comb_df["acc_x"] + comb_df["acc_y"]
    comb_df["blank"] = comb_df["blank_x"] + comb_df["blank_y"]
    comb_df = comb_df[comb_columns]
    comb_df = comb_df.groupby("value", as_index=False).agg({
        "proba": "sum",
        "damage": "first",
        "crit": "first",
        "acc": "first",
        "blank": "first",
    })
    return comb_df

def combine_dice(red_dice: int = 0, blue_dice: int = 0, black_dice: int = 0):
    roll_df = None
    red_range = range(0, red_dice)
    blue_range = range(red_dice, red_dice+blue_dice)
    black_range = range(red_dice+blue_dice, red_dice+blue_dice+black_dice)
    for idx in range(red_dice+blue_dice+black_dice):
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

def remove_dice(roll_df, to_remove_dice):
    kept_df = roll_df.copy()
    removed_df = roll_df.copy()
    removed_df["removed_dice"] = to_remove_dice
    removed_df = removed_df[removed_df["removed_dice"].apply(lambda x: True if type(x) is list else False)]

    removed_df["to_remove_damage"] = removed_df.apply(lambda x: sum([value_to_dice_attr_dict(value)["damage"] for value in x["removed_dice"]]), axis=1)
    removed_df["to_remove_crit"] = removed_df.apply(lambda x: sum([value_to_dice_attr_dict(value)["crit"] for value in x["removed_dice"]]), axis=1)
    removed_df["to_remove_acc"] = removed_df.apply(lambda x: sum([value_to_dice_attr_dict(value)["acc"] for value in x["removed_dice"]]), axis=1)
    removed_df["to_remove_blank"] = removed_df.apply(lambda x: sum([value_to_dice_attr_dict(value)["blank"] for value in x["removed_dice"]]), axis=1)

    removed_df["value"] = removed_df.apply(lambda x: " ".join(sorted([value for value in value_str_to_list(x["value"]) if value not in x["removed_dice"]])), axis=1)
    removed_df["damage"] = removed_df["damage"] - removed_df["to_remove_damage"]
    removed_df["crit"] = removed_df["crit"] - removed_df["to_remove_crit"]
    removed_df["acc"] = removed_df["acc"] - removed_df["to_remove_acc"]
    removed_df["blank"] = removed_df["blank"] - removed_df["to_remove_blank"]
    removed_df = removed_df.drop(["to_remove_damage", "to_remove_crit", "to_remove_acc", "to_remove_blank"], axis=1)
    removed_df["removed_dice"] = removed_df["removed_dice"].apply(lambda x: value_list_to_str(x))

    kept_df = roll_df.copy()
    kept_df["removed_dice"] = to_remove_dice
    kept_df = kept_df[kept_df["removed_dice"].apply(lambda x: False if type(x) is list else True)]
    kept_df = kept_df.drop("removed_dice", axis=1)
    return removed_df, kept_df

def add_dice_to_roll(roll_df, to_add_dice):
    dice_dict = value_to_dice_count_dict(to_add_dice)
    rr_dice_df = combine_dice(dice_dict["red"], dice_dict["blue"], dice_dict["black"])
    return combine_two(roll_df, rr_dice_df)

def reroll_dice(roll_df, results_to_reroll="blanks", reroll_count=1):
    if results_to_reroll == "blanks":
        results_to_reroll = ["B_blank", "R_blank"]
    if results_to_reroll == "blanks":
        results_to_reroll = ["R_acc", "U_acc"]
    initial_roll_df = roll_df.copy()
    dice_to_reroll = roll_df["value"].apply(
        lambda roll: value_str_to_list(roll)
    ).apply(
        lambda roll: sorted([res for res in roll if res in results_to_reroll], key=lambda n: results_to_reroll.index(n))[0:reroll_count]
    ).apply(lambda roll: roll if len(roll) > 0 else np.NaN).dropna()
    rr_df, no_rr_df = remove_dice(roll_df, dice_to_reroll)

    rerolls_types = rr_df["removed_dice"].unique()
    rrd_df_list = []
    for reroll in rerolls_types:
        subrrd_df = add_dice_to_roll(rr_df[rr_df["removed_dice"] == reroll], reroll)
        rrd_df_list.append(subrrd_df)
    rerolled_df = pd.concat([no_rr_df]+rrd_df_list)
    rerolled_df = rerolled_df.groupby("value", as_index=False).agg({
        "proba": "sum",
        "damage": "first",
        "crit": "first",
        "acc": "first",
        "blank": "first",
    })
    return rerolled_df, initial_roll_df

def filter_roll(roll_df, conditions_dict):
    for key in conditions_dict.keys():
        operator = conditions_dict[key]["operator"]
        amount = conditions_dict[key]["amount"]
        print(f"filtering {operator} {amount} {key}")
        if operator == "lt":
            roll_df = roll_df[roll_df[key] < amount]
        if operator == "lte":
            roll_df = roll_df[roll_df[key] <= amount]
        if operator == "gt":
            roll_df = roll_df[roll_df[key] > amount]
        if operator == "gte":
            roll_df = roll_df[roll_df[key] >= amount]
        if operator == "eq":
            roll_df = roll_df[roll_df[key] == amount]
        if operator == "neq":
            roll_df = roll_df[roll_df[key] != amount]
    return roll_df

def average_damage(roll_df):
    avg_dmg = (roll_df["damage"]*roll_df["proba"]).sum()
    print(f"average damage for roll: {avg_dmg}")
    return avg_dmg

def roll_proba(roll_df):
    proba = roll_df["proba"].sum()
    print(f"proba for roll: {proba*100}")
    return proba

if __name__ == "__main__":
    filter_4dmg_2acc = {
        "acc": {
            "operator": "gte",
            "amount": 2
        },
        "damage": {
            "operator": "gte",
            "amount": 4
        }
    }
    import timeit
    start = timeit.default_timer()
    roll_df = combine_dice(4, 5, 0)
    roll_df, _ = reroll_dice(roll_df, ["R_blank"], 1)
    stop = timeit.default_timer()
    print('Time: ', stop - start)
    filtered_roll = filter_roll(roll_df, filter_4dmg_2acc)
    print(roll_proba(filtered_roll))