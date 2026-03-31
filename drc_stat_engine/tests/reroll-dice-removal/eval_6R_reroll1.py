"""
Evaluate 6R + reroll 1 blank for max_damage vs balanced strategies.
Outputs the post-fix rerolled DataFrame as CSV for each strategy.
"""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.dice_maths_combinatories import combine_dice, reroll_dice, value_str_to_list
from drc_stat_engine.stats.strategies import STRATEGY_PRIORITY_LISTS

type_str = "ship"
pool_size = 6

# Build the 6R base roll
roll_df = combine_dice(pool_size, 0, 0, type_str)
print(f"Base roll: {len(roll_df)} rows, proba sum = {roll_df['proba'].sum():.10f}")

for strategy in ("max_damage", "balanced"):
    priority = STRATEGY_PRIORITY_LISTS[type_str][strategy]["reroll"]
    rerolled_df, _ = reroll_dice(roll_df.copy(), results_to_reroll=priority, reroll_count=1, type_str=type_str)

    # Sanity checks
    proba_sum = rerolled_df["proba"].sum()
    face_counts = rerolled_df["value"].apply(lambda v: len(value_str_to_list(v)))
    bad_rows = rerolled_df[face_counts != pool_size]

    print(f"\n{'='*60}")
    print(f"Strategy: {strategy}")
    print(f"  Reroll priority: {priority}")
    print(f"  Rows: {len(rerolled_df)}")
    print(f"  Proba sum: {proba_sum:.10f}")
    print(f"  Avg damage: {(rerolled_df['damage'] * rerolled_df['proba']).sum():.6f}")
    print(f"  All rows have {pool_size} faces: {len(bad_rows) == 0}")
    if len(bad_rows) > 0:
        print(f"  BAD ROWS ({len(bad_rows)}):")
        for _, r in bad_rows.iterrows():
            print(f"    value='{r['value']}' faces={len(value_str_to_list(r['value']))}")

    # Write CSV
    csv_path = f"drc_stat_engine/tests/reroll-dice-removal/6R_reroll1_{strategy}.csv"
    rerolled_df.sort_values("value").to_csv(csv_path, index=False)
    print(f"  CSV written to: {csv_path}")
