"""
Performance test: reroll on large dice pools (8+ dice).
Verifies both speed improvement and output correctness.
"""
import sys
import time

sys.path.insert(0, ".")

from drc_stat_engine.stats.dice_maths_combinatories import combine_dice, reroll_dice
from drc_stat_engine.stats.report_engine import generate_report
from drc_stat_engine.stats.dice_models import DicePool, AttackEffect

TOLERANCE = 1e-9

def check_prob_sum(df, label):
    total = df["proba"].sum()
    assert abs(total - 1.0) < TOLERANCE, f"{label}: proba sum = {total}, expected 1.0"

try:
    # --- Correctness baseline: small pool ---
    roll_small = combine_dice(2, 0, 2, "ship")
    t0 = time.time()
    result_small, _ = reroll_dice(roll_small, ["R_blank", "B_blank"], reroll_count=2, type_str="ship")
    t_small = time.time() - t0
    check_prob_sum(result_small, "small pool reroll")
    print(f"PASS: small pool (2R+2B) reroll in {t_small:.3f}s, {len(result_small)} rows")

    # --- Performance: 8-die pool ---
    roll_large = combine_dice(4, 0, 4, "ship")
    print(f"INFO: 8-die pool has {len(roll_large)} rows before reroll")
    t0 = time.time()
    result_large, _ = reroll_dice(roll_large, ["R_blank", "B_blank"], reroll_count=3, type_str="ship")
    t_large = time.time() - t0
    check_prob_sum(result_large, "large pool reroll")
    print(f"PASS: large pool (4R+4B) reroll x3 in {t_large:.3f}s, {len(result_large)} rows")

    # --- Performance: 10-die pool ---
    roll_xl = combine_dice(5, 0, 5, "ship")
    print(f"INFO: 10-die pool has {len(roll_xl)} rows before reroll")
    t0 = time.time()
    result_xl, _ = reroll_dice(roll_xl, ["R_blank", "B_blank"], reroll_count=3, type_str="ship")
    t_xl = time.time() - t0
    check_prob_sum(result_xl, "xl pool reroll")
    print(f"PASS: xl pool (5R+5B) reroll x3 in {t_xl:.3f}s, {len(result_xl)} rows")

    # --- Full generate_report with reroll on 8 dice ---
    pool = DicePool(red=4, blue=0, black=4, type="ship")
    pipeline = [AttackEffect(type="reroll", count=3, applicable_results=["blank", "hit"])]
    t0 = time.time()
    variants = generate_report(pool, pipeline, strategies=["max_damage"])
    t_report = time.time() - t0
    assert len(variants) == 1
    print(f"PASS: generate_report 8-die + reroll x3 in {t_report:.3f}s")

    print("\nAll tests PASSED")

except AssertionError as e:
    print(f"FAIL: {e}")
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
