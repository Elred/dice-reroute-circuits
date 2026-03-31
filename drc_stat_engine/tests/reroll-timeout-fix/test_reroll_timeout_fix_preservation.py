"""
Preservation property tests for reroll-timeout-fix.

These tests verify that behaviors which are CORRECT on the unfixed code remain
correct after the fix is applied. All tests here MUST PASS on both unfixed and
fixed code.

Property 2: Preservation — Low-Cost and Non-Reroll Backend Selection Unchanged

Three sub-properties:
  - Pools ≤ 8 dice with reroll cost ≤ 25 → combinatorial
  - Pools > 8 dice → Monte Carlo (regardless of rerolls)
  - Forced backends ("combinatorial", "montecarlo") → always return the forced module
"""

import sys
sys.path.insert(0, '.')

from hypothesis import given, assume, settings
from hypothesis import strategies as st

from drc_stat_engine.stats.report_engine import _select_backend
from drc_stat_engine.stats.dice_models import DicePool, AttackEffect
import drc_stat_engine.stats.dice_monte_carlo as dice_monte_carlo
import drc_stat_engine.stats.dice_maths_combinatories as dice_maths_combinatories

REROLL_COST_LIMIT = 25


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_reroll(count):
    """Create a reroll AttackEffect."""
    return AttackEffect(type="reroll", count=count, applicable_results=[])


def make_add_dice(red=0, blue=0, black=0):
    """Create an add_dice AttackEffect."""
    return AttackEffect(type="add_dice", dice_to_add={"red": red, "blue": blue, "black": black})


def compute_total_dice(pool, pipeline):
    """Compute total dice including add_dice ops."""
    total = pool.red + pool.blue + pool.black
    for op in pipeline:
        if op.type == "add_dice" and op.dice_to_add:
            total += sum(op.dice_to_add.values())
    return total


def compute_max_reroll(pipeline, total_dice):
    """Compute max effective reroll count from pipeline."""
    max_rr = 0
    for op in pipeline:
        if op.type == "reroll":
            max_rr = max(max_rr, min(op.count, total_dice))
    return max_rr


# ---------------------------------------------------------------------------
# Property-based test: Low-cost reroll pools ≤ 8 → combinatorial
# Feature: reroll-timeout-fix, Property 2: Preservation — Low-Cost and Non-Reroll Backend Selection Unchanged
# ---------------------------------------------------------------------------

@given(
    red=st.integers(min_value=0, max_value=8),
    blue=st.integers(min_value=0, max_value=8),
    black=st.integers(min_value=0, max_value=8),
    reroll_count=st.integers(min_value=0, max_value=8),
)
@settings(max_examples=100)
def test_low_cost_reroll_stays_combinatorial(red, blue, black, reroll_count):
    """
    **Validates: Requirements 3.1, 3.3**

    For any pool with total_dice ≤ 8 and reroll cost ≤ REROLL_COST_LIMIT,
    _select_backend returns dice_maths_combinatories.

    On unfixed code: pools ≤ 8 always return combinatorial (regardless of cost),
    so this subset (cost ≤ 25) trivially passes.
    After fix: these low-cost cases must still return combinatorial.
    """
    # Feature: reroll-timeout-fix, Property 2: Preservation — Low-Cost and Non-Reroll Backend Selection Unchanged

    total_dice = red + blue + black
    assume(total_dice > 0)   # non-empty pool
    assume(total_dice <= 8)  # within combinatorial range

    pipeline = []
    if reroll_count > 0:
        pipeline.append(make_reroll(reroll_count))

    effective_reroll = min(reroll_count, total_dice) if reroll_count > 0 else 0
    cost = total_dice * effective_reroll
    assume(cost <= REROLL_COST_LIMIT)  # low-cost subset

    pool = DicePool(red=red, blue=blue, black=black)
    result = _select_backend(pool, pipeline, "auto")
    assert result is dice_maths_combinatories, (
        f"Expected combinatorial for pool=({red}R,{blue}B,{black}K) "
        f"total_dice={total_dice}, reroll={reroll_count}, cost={cost} ≤ {REROLL_COST_LIMIT}. "
        f"Got MC instead."
    )


# ---------------------------------------------------------------------------
# Property-based test: Large pools (> 8 dice) → Monte Carlo
# Feature: reroll-timeout-fix, Property 2: Preservation — Low-Cost and Non-Reroll Backend Selection Unchanged
# ---------------------------------------------------------------------------

@given(
    red=st.integers(min_value=0, max_value=15),
    blue=st.integers(min_value=0, max_value=15),
    black=st.integers(min_value=0, max_value=15),
    reroll_count=st.integers(min_value=0, max_value=10),
)
@settings(max_examples=100)
def test_large_pool_always_monte_carlo(red, blue, black, reroll_count):
    """
    **Validates: Requirements 3.2, 3.5**

    For any pool with total_dice > 8, _select_backend returns dice_monte_carlo
    regardless of reroll operations in the pipeline.
    """
    # Feature: reroll-timeout-fix, Property 2: Preservation — Low-Cost and Non-Reroll Backend Selection Unchanged

    total_dice = red + blue + black
    assume(total_dice > 8)
    assume(total_dice <= 20)  # respect MAX_DICE

    pipeline = []
    if reroll_count > 0:
        pipeline.append(make_reroll(reroll_count))

    pool = DicePool(red=red, blue=blue, black=black)
    result = _select_backend(pool, pipeline, "auto")
    assert result is dice_monte_carlo, (
        f"Expected MC for pool=({red}R,{blue}B,{black}K) "
        f"total_dice={total_dice} > 8. Got combinatorial instead."
    )


# ---------------------------------------------------------------------------
# Property-based test: Forced backends always return the forced module
# Feature: reroll-timeout-fix, Property 2: Preservation — Low-Cost and Non-Reroll Backend Selection Unchanged
# ---------------------------------------------------------------------------

@given(
    red=st.integers(min_value=0, max_value=10),
    blue=st.integers(min_value=0, max_value=10),
    black=st.integers(min_value=0, max_value=10),
    reroll_count=st.integers(min_value=0, max_value=8),
    backend=st.sampled_from(["combinatorial", "montecarlo"]),
)
@settings(max_examples=100)
def test_forced_backend_always_returns_forced_module(red, blue, black, reroll_count, backend):
    """
    **Validates: Requirements 3.4**

    Forced backends ("combinatorial", "montecarlo") bypass auto logic entirely
    and always return the corresponding module.
    """
    # Feature: reroll-timeout-fix, Property 2: Preservation — Low-Cost and Non-Reroll Backend Selection Unchanged

    total_dice = red + blue + black
    assume(total_dice > 0)
    assume(total_dice <= 20)

    pipeline = []
    if reroll_count > 0:
        pipeline.append(make_reroll(reroll_count))

    pool = DicePool(red=red, blue=blue, black=black)
    result = _select_backend(pool, pipeline, backend)

    if backend == "combinatorial":
        assert result is dice_maths_combinatories, (
            f"Forced 'combinatorial' should return dice_maths_combinatories, got MC. "
            f"pool=({red}R,{blue}B,{black}K), reroll={reroll_count}"
        )
    else:
        assert result is dice_monte_carlo, (
            f"Forced 'montecarlo' should return dice_monte_carlo, got combinatorial. "
            f"pool=({red}R,{blue}B,{black}K), reroll={reroll_count}"
        )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    passed = 0
    failed = 0
    errors = []

    tests = [
        ("Property: low-cost reroll stays combinatorial", test_low_cost_reroll_stays_combinatorial),
        ("Property: large pool always MC", test_large_pool_always_monte_carlo),
        ("Property: forced backend returns forced module", test_forced_backend_always_returns_forced_module),
    ]

    for name, fn in tests:
        try:
            fn()
            print(f"PASS: {name}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {name} — {e}")
            failed += 1
            errors.append(str(e))
        except Exception as e:
            print(f"FAIL: {name} — {type(e).__name__}: {e}")
            failed += 1
            errors.append(f"{type(e).__name__}: {e}")

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    if errors:
        print(f"\nFailures:")
        for err in errors:
            print(f"  - {err}")
