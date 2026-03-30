import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.dice_maths_combinatories import combine_dice
from drc_stat_engine.stats.dice_models import DicePool, AttackEffect
from drc_stat_engine.stats.strategies import build_strategy_pipeline
from drc_stat_engine.stats.report_engine import run_pipeline, cumulative_accuracy

try:
    pool = DicePool(red=2, blue=1, black=0, type='ship')
    roll_df = combine_dice(2, 1, 0, 'ship')

    pipeline = [AttackEffect(
        type='change_die',
        count=1,
        applicable_results=['R_hit', 'R_crit', 'R_hit+hit', 'U_hit', 'U_crit'],
        target_result='acc'
    )]

    built = build_strategy_pipeline(pipeline, 'max_damage', 'ship')
    print(f"priority_list after build: {built[0].priority_list}")

    final = run_pipeline(roll_df.copy(), built, 'ship')
    acc = cumulative_accuracy(final)
    print("Cumulative accuracy:")
    for threshold, prob in acc:
        print(f"  P(acc >= {threshold}) = {prob*100:.2f}%")

    # The key assertion: P(acc >= 1) must be > 0
    p_acc_1 = dict(acc).get(1, 0.0)
    assert p_acc_1 > 0.0, f"FAIL: P(acc >= 1) = {p_acc_1}, expected > 0"
    print(f"\nPASS: P(acc >= 1) = {p_acc_1*100:.2f}% (correctly non-zero)")

except Exception as e:
    import traceback
    print(f"FAIL: {e}")
    traceback.print_exc()
