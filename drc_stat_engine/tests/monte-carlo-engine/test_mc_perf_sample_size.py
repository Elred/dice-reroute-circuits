"""
Quick benchmark: compare MC pipeline time at 10k vs 50k samples.
Uses a realistic 9-die ship pool (forces MC backend) with a reroll op.
"""
import sys, time
sys.path.insert(0, '.')

import drc_stat_engine.stats.dice_monte_carlo as mc
from drc_stat_engine.stats.dice_models import AttackEffect

POOL = dict(red_dice=3, blue_dice=3, black_dice=3, type_str="ship")
REROLL_RESULTS = ["R_blank", "B_blank", "U_acc", "R_acc"]

def run_pipeline(sample_count, seed=42):
    roll = mc.combine_dice(**POOL, sample_count=sample_count, seed=seed)
    roll = mc.reroll_dice(
        roll,
        results_to_reroll=REROLL_RESULTS,
        reroll_count=9,
        type_str="ship",
    )
    return roll

for n in [10_000, 50_000]:
    # warm-up
    run_pipeline(n)
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        run_pipeline(n)
        times.append(time.perf_counter() - t0)
    avg = sum(times) / len(times)
    print(f"N={n:>6,}  avg={avg*1000:.1f}ms  min={min(times)*1000:.1f}ms  max={max(times)*1000:.1f}ms")
