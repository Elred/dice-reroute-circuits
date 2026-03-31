"""
Compare combinatorial vs Monte Carlo engines.
Pool: 6R ship
Pipeline: [reroll 6 blanks, reroll 1 blank] with balanced strategy
"""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.dice_models import DicePool, AttackEffect
from drc_stat_engine.stats.report_engine import generate_report

ALL_RED = ["R_blank", "R_hit", "R_crit", "R_acc", "R_hit+hit"]

pool = DicePool(red=6, blue=0, black=0, type="ship")
pipeline = [
    AttackEffect(type="reroll", count=6, applicable_results=list(ALL_RED)),
    AttackEffect(type="reroll", count=1, applicable_results=list(ALL_RED)),
]

# Combinatorial
print("Running combinatorial...")
comb = generate_report(pool, pipeline, strategies=["balanced"], backend="combinatorial")
comb_v = comb[0]

# Monte Carlo (high sample count for accuracy)
print("Running Monte Carlo (500k samples)...")
mc = generate_report(pool, pipeline, strategies=["balanced"], backend="montecarlo", sample_count=500_000, seed=42)
mc_v = mc[0]

print(f"\n{'='*60}")
print(f"Pool: 6R ship | Pipeline: reroll 6, reroll 1 | Strategy: balanced")
print(f"{'='*60}")

print(f"\n{'Metric':<25} {'Combinatorial':>15} {'Monte Carlo':>15} {'Delta':>10}")
print(f"{'-'*65}")
print(f"{'Avg damage':<25} {comb_v['avg_damage']:>15.6f} {mc_v['avg_damage']:>15.6f} {abs(comb_v['avg_damage'] - mc_v['avg_damage']):>10.6f}")
print(f"{'P(crit >= 1)':<25} {comb_v['crit']:>15.6f} {mc_v['crit']:>15.6f} {abs(comb_v['crit'] - mc_v['crit']):>10.6f}")
print(f"{'P(damage = 0)':<25} {comb_v['damage_zero']:>15.6f} {mc_v['damage_zero']:>15.6f} {abs(comb_v['damage_zero'] - mc_v['damage_zero']):>10.6f}")
print(f"{'P(acc = 0)':<25} {comb_v['acc_zero']:>15.6f} {mc_v['acc_zero']:>15.6f} {abs(comb_v['acc_zero'] - mc_v['acc_zero']):>10.6f}")
print(f"{'Engine type':<25} {comb_v['engine_type']:>15} {mc_v['engine_type']:>15}")

print(f"\nCumulative damage P(dmg >= X):")
print(f"{'X':<5} {'Combinatorial':>15} {'Monte Carlo':>15} {'Delta':>10}")
comb_dmg = dict(comb_v['damage'])
mc_dmg = dict(mc_v['damage'])
all_x = sorted(set(list(comb_dmg.keys()) + list(mc_dmg.keys())))
for x in all_x:
    cv = comb_dmg.get(x, 0.0)
    mv = mc_dmg.get(x, 0.0)
    print(f"{x:<5} {cv:>15.6f} {mv:>15.6f} {abs(cv - mv):>10.6f}")

print(f"\nCumulative accuracy P(acc >= X):")
print(f"{'X':<5} {'Combinatorial':>15} {'Monte Carlo':>15} {'Delta':>10}")
comb_acc = dict(comb_v['accuracy'])
mc_acc = dict(mc_v['accuracy'])
all_x = sorted(set(list(comb_acc.keys()) + list(mc_acc.keys())))
for x in all_x:
    cv = comb_acc.get(x, 0.0)
    mv = mc_acc.get(x, 0.0)
    print(f"{x:<5} {cv:>15.6f} {mv:>15.6f} {abs(cv - mv):>10.6f}")
