from ctypes import ArgumentError
from profiles import red_die, blue_die, black_die

def combine_two(a_results, b_results):
    combinations = {}
    for a_res in a_results:
        for b_res in b_results:
            comb_value = " ".join(sorted(a_res['value'].split() + b_res['value'].split()))
            comb_proba = a_res["proba"] * b_res["proba"]
            comb_damage = a_res["damage"] + b_res["damage"]
            comb_acc = a_res["acc"] + b_res["acc"]
            comb_crit = a_res["crit"] + b_res["crit"]
            if combinations.get(comb_value, None) is not None :
                combinations[comb_value] = {
                    "value": comb_value,
                    "proba": comb_proba + combinations[comb_value]["proba"], 
                    "damage": comb_damage,
                    "acc": comb_acc,
                    "crit": comb_crit
                }
            else :
                combinations[comb_value] = {
                    "value": comb_value, 
                    "proba": comb_proba, 
                    "damage": comb_damage, 
                    "acc": comb_acc, 
                    "crit": comb_crit
                }
    return list(combinations.values())

def combine_dice(red_dice: int = 0, blue_dice: int = 0, black_dice: int = 0):
    combinations = []
    red_range = range(0, red_dice)
    blue_range = range(red_dice, red_dice+blue_dice)
    black_range = range(red_dice+blue_dice, red_dice+blue_dice+black_dice)
    for idx in range(red_dice+blue_dice+black_dice):
        if idx == 0:
            if red_range:
                combinations = red_die
                continue
            if blue_range:
                combinations = blue_die
                continue
            if black_range:
                combinations = black_die
                continue
        else:
            if idx in red_range:
                combinations = combine_two(combinations, red_die)
            if idx in blue_range:
                combinations = combine_two(combinations, blue_die)
            if idx in black_range:
                combinations = combine_two(combinations, black_die)
    return combinations

def reroll_one(results, reroll_strategy):
    pass

def chances_of_exactly(results, damage_amount: int = 0, acc_amount: int = 0, crit_amount: int = 0):
    return sum([
            result["proba"] 
            for result in results 
            if (result["damage"] == damage_amount and result["crit"] == crit_amount and result["acc"] == acc_amount)
        ])

def chances_of_atleast(results, damage_amount: int = 0, acc_amount: int = 0, crit_amount: int = 0):
    return sum([
            result["proba"] 
            for result in results 
            if (result["damage"] >= damage_amount and result["crit"] >= crit_amount and result["acc"] >= acc_amount)
        ])

def average_damage(results):
    return sum([res["damage"]*res["proba"] for res in results])


if __name__ == "__main__":
    result = combine_dice(0, 2, 0)
    print(result)
    print(f"Check_proba: {sum([res['proba'] for res in result])}")
    print(chances_of_atleast(result, 2, 0, 1))