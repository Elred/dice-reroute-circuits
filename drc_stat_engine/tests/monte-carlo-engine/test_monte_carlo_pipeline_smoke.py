"""
Smoke test for tasks 3.1–3.4: reroll_dice, cancel_dice, add_dice_to_roll, change_die_face.
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
from drc_stat_engine.stats.dice_monte_carlo import (
    combine_dice, reroll_dice, cancel_dice, add_dice_to_roll, change_die_face
)

SEED = 42
N = 1000

try:
    roll = combine_dice(2, 1, 0, 'ship', sample_count=N, seed=SEED)
    s = roll['proba'].sum()
    assert abs(s - 1.0) < 1e-9, f"combine_dice proba sum {s}"
    print(f"PASS combine_dice: proba sum = {s:.10f}")
except Exception as e:
    print(f"FAIL combine_dice: {e}")
    sys.exit(1)

# --- reroll_dice ---
try:
    rr, orig = reroll_dice(roll, ['R_blank', 'B_blank'], 1, 'ship')
    s = rr['proba'].sum()
    assert abs(s - 1.0) < 1e-9, f"reroll proba sum {s}"
    print(f"PASS reroll_dice: proba sum = {s:.10f}")
except Exception as e:
    print(f"FAIL reroll_dice: {e}")
    sys.exit(1)

# reroll with empty list returns unchanged
try:
    rr2, orig2 = reroll_dice(roll, [], 1, 'ship')
    assert rr2 is roll, "empty reroll should return same object"
    print("PASS reroll_dice empty list: returns input unchanged")
except Exception as e:
    print(f"FAIL reroll_dice empty list: {e}")
    sys.exit(1)

# --- cancel_dice ---
try:
    canc, kept = cancel_dice(roll, ['R_blank', 'B_blank'], 1, 'ship')
    merged = pd.concat([canc, kept]).groupby('value', as_index=False).agg(
        {'proba': 'sum', 'damage': 'first', 'crit': 'first', 'acc': 'first', 'blank': 'first'}
    )
    s = merged['proba'].sum()
    assert abs(s - 1.0) < 1e-9, f"cancel merged proba sum {s}"
    print(f"PASS cancel_dice: merged proba sum = {s:.10f}")
except Exception as e:
    print(f"FAIL cancel_dice: {e}")
    sys.exit(1)

# cancel with no matching faces
try:
    # Blue dice have no blanks, so cancel blanks on a blue-only roll should return empty cancelled
    blue_roll = combine_dice(0, 2, 0, 'ship', sample_count=N, seed=SEED)
    canc2, kept2 = cancel_dice(blue_roll, ['R_blank', 'B_blank'], 1, 'ship')
    assert len(canc2) == 0, f"expected empty cancelled_df, got {len(canc2)} rows"
    s2 = kept2['proba'].sum()
    assert abs(s2 - 1.0) < 1e-9, f"kept proba sum {s2}"
    print(f"PASS cancel_dice no match: empty cancelled, kept proba sum = {s2:.10f}")
except Exception as e:
    print(f"FAIL cancel_dice no match: {e}")
    sys.exit(1)

# --- add_dice_to_roll ---
try:
    added = add_dice_to_roll(roll, 0, 0, 1, 'ship')
    s = added['proba'].sum()
    assert abs(s - 1.0) < 1e-9, f"add_dice proba sum {s}"
    # matrix should have one more column
    orig_D = roll.attrs['_mc_state']['matrix'].shape[1]
    new_D  = added.attrs['_mc_state']['matrix'].shape[1]
    assert new_D == orig_D + 1, f"expected D={orig_D+1}, got {new_D}"
    print(f"PASS add_dice_to_roll: proba sum = {s:.10f}, D {orig_D} -> {new_D}")
except Exception as e:
    print(f"FAIL add_dice_to_roll: {e}")
    sys.exit(1)

# add zero dice returns unchanged
try:
    same = add_dice_to_roll(roll, 0, 0, 0, 'ship')
    assert same is roll, "add zero dice should return same object"
    print("PASS add_dice_to_roll zero: returns input unchanged")
except Exception as e:
    print(f"FAIL add_dice_to_roll zero: {e}")
    sys.exit(1)

# --- change_die_face ---
try:
    changed = change_die_face(roll, ['R_blank', 'B_blank'], 'R_hit', 'ship')
    s = changed['proba'].sum()
    assert abs(s - 1.0) < 1e-9, f"change_die_face proba sum {s}"
    print(f"PASS change_die_face: proba sum = {s:.10f}")
except Exception as e:
    print(f"FAIL change_die_face: {e}")
    sys.exit(1)

# change_die_face with empty source_results returns unchanged
try:
    same2 = change_die_face(roll, [], 'R_hit', 'ship')
    assert same2 is roll, "empty source_results should return same object"
    print("PASS change_die_face empty sources: returns input unchanged")
except Exception as e:
    print(f"FAIL change_die_face empty sources: {e}")
    sys.exit(1)

print("\nAll smoke tests PASSED")
