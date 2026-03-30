"""
Smoke test for tasks 5.1, 5.2, 5.3 — _select_backend and generate_report with backend param.
"""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.report_engine import generate_report, _select_backend
from drc_stat_engine.stats.dice_models import DicePool, AttackEffect
import drc_stat_engine.stats.dice_maths_combinatories as comb
import drc_stat_engine.stats.dice_monte_carlo as mc

try:
    # Test _select_backend
    pool_small = DicePool(red=2, blue=1, black=0, type='ship')
    pool_large = DicePool(red=5, blue=2, black=2, type='ship')
    assert _select_backend(pool_small, 'auto') is comb, 'auto small should use comb'
    assert _select_backend(pool_large, 'auto') is mc, 'auto large should use mc'
    assert _select_backend(pool_small, 'combinatorial') is comb
    assert _select_backend(pool_small, 'montecarlo') is mc
    print('PASS: _select_backend')

    # Test generate_report with combinatorial backend
    variants = generate_report(pool_small, [], ['max_damage'], backend='combinatorial')
    assert len(variants) == 1
    assert 'damage' in variants[0]
    print('PASS: generate_report combinatorial')

    # Test generate_report with MC backend
    variants_mc = generate_report(pool_small, [], ['max_damage'], backend='montecarlo', sample_count=1000, seed=42)
    assert len(variants_mc) == 1
    assert 'damage' in variants_mc[0]
    print('PASS: generate_report montecarlo')

    # Test ValueError for unknown backend
    try:
        _select_backend(pool_small, 'unknown')
        print('FAIL: expected ValueError')
    except ValueError as e:
        print(f'PASS: ValueError for unknown backend: {e}')

except Exception as e:
    import traceback
    print(f'FAIL: unexpected error: {e}')
    traceback.print_exc()
