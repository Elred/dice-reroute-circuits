"""
Bug condition exploration test for reroll-timeout-fix.

This test encodes the EXPECTED (fixed) behavior: _select_backend should return
dice_monte_carlo for pool+pipeline combinations where the reroll cost exceeds
REROLL_COST_LIMIT (25).

On UNFIXED code, this test is EXPECTED TO FAIL — the current _select_backend
ignores reroll cost and returns dice_maths_combinatories for all pools ≤ 8 dice,
even when reroll operations would cause combinatorial explosion.

Failure on unfixed code confirms the bug exists.
"""

import sys
sys.path.insert(0, '.')

from hypothesis import given, assume, settings, HealthCheck
from hypothesis import strategies as st

from drc_stat_engine.stats.report_engine import _select_backend
from drc_stat_engine.stats.dice_models import DicePool, AttackEffect
import drc_stat_engine.stats.dice_monte_carlo as dice_monte_carlo
import drc_stat_engine.stats.dice_maths_combinatories as dice_maths_combinatories

REROLL_COST_LIMIT = 25


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_reroll(count, applicable_results=None):
    """Create a reroll AttackEffect."""
    return AttackEffect(
        type="reroll",
        count=count,
        applicable_results=applicable_results or [],
    )


def make_add_dice(red=0, blue=0, black=0):
    """Create an add_dice AttackEffect."""
    return AttackEffect(
        type="add_dice",
        dice_to_add={"red": red, "blue": blue, "black": black},
    )


def compute_reroll_cost(pool, pipeline):
    """
    Compute the reroll cost for a pool+pipeline combination.
    Returns (total_dice, max_reroll_count, cost).
    """
    total_dice = pool.red + pool.blue + pool.black
    for op in pipeline:
        if op.type == "add_dice" and op.dice_to_add:
            total_dice += sum(op.dice_to_add.values())

    max_reroll_count = 0
    for op in pipeline:
        if op.type == "reroll":
            effective = min(op.count, total_dice)
            max_reroll_count = max(max_reroll_count, effective)

    return total_dice, max_reroll_count, total_dice * max_reroll_count


# ---------------------------------------------------------------------------
# Property-based test
# Feature: reroll-timeout-fix, Property 1: Bug Condition — Expensive Reroll Selects Combinatorial
# ---------------------------------------------------------------------------

# Strategy: generate pools with total_dice in [4..8] and reroll ops that push
# cost above 25. We constrain the generator so every example is a valid bug
# condition input.

@given(
    red=st.integers(min_value=0, max_value=8),
    blue=st.integers(min_value=0, max_value=8),
    black=st.integers(min_value=0, max_value=8),
    add_red=st.integers(min_value=0, max_value=3),
    add_blue=st.integers(min_value=0, max_value=3),
    add_black=st.integers(min_value=0, max_value=3),
    reroll_count=st.integers(min_value=1, max_value=8),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.filter_too_much])
def test_bug_condition_expensive_reroll_selects_monte_carlo(
    red, blue, black, add_red, add_blue, add_black, reroll_count
):
    """
    **Validates: Requirements 1.1, 1.3, 2.1, 2.3**

    For any pool+pipeline where total_dice ≤ 8 and
    total_dice × max_reroll_count > REROLL_COST_LIMIT,
    _select_backend should return dice_monte_carlo.

    On unfixed code this FAILS because _select_backend only checks total_dice ≤ 8
    and ignores reroll cost.
    """
    # Feature: reroll-timeout-fix, Property 1: Bug Condition — Expensive Reroll Selects Combinatorial

    base_dice = red + blue + black
    assume(base_dice > 0)  # pool must be non-empty

    added = add_red + add_blue + add_black
    total_dice = base_dice + added
    assume(total_dice <= 8)  # must stay in the ≤ 8 range (where bug lives)

    effective_reroll = min(reroll_count, total_dice)
    cost = total_dice * effective_reroll
    assume(cost > REROLL_COST_LIMIT)  # must exceed threshold

    pool = DicePool(red=red, blue=blue, black=black)
    pipeline = []
    if added > 0:
        pipeline.append(make_add_dice(red=add_red, blue=add_blue, black=add_black))
    pipeline.append(make_reroll(reroll_count))

    result = _select_backend(pool, pipeline, "auto")
    assert result is dice_monte_carlo, (
        f"Bug confirmed: _select_backend returned combinatorial for "
        f"pool=({red}R,{blue}B,{black}K) + add({add_red}R,{add_blue}B,{add_black}K) "
        f"total_dice={total_dice}, reroll={reroll_count}, cost={cost} > {REROLL_COST_LIMIT}. "
        f"Expected dice_monte_carlo, got dice_maths_combinatories."
    )


# ---------------------------------------------------------------------------
# Concrete test cases
# Feature: reroll-timeout-fix, Property 1: Bug Condition — Expensive Reroll Selects Combinatorial
# ---------------------------------------------------------------------------

def test_concrete_5R_3B_reroll_5():
    """5R+3B pool with reroll 5: cost = 8×5 = 40 > 25. Should select MC."""
    # Feature: reroll-timeout-fix, Property 1: Bug Condition — Expensive Reroll Selects Combinatorial
    pool = DicePool(red=5, blue=0, black=3)
    pipeline = [make_reroll(5)]
    _, _, cost = compute_reroll_cost(pool, pipeline)
    assert cost == 40, f"Expected cost 40, got {cost}"

    result = _select_backend(pool, pipeline, "auto")
    assert result is dice_monte_carlo, (
        f"Bug confirmed: 5R+3B with reroll 5 (cost={cost}) returned combinatorial, "
        f"expected MC."
    )


def test_concrete_4R_3B_reroll_4():
    """4R+3B pool with reroll 4: cost = 7×4 = 28 > 25. Should select MC."""
    # Feature: reroll-timeout-fix, Property 1: Bug Condition — Expensive Reroll Selects Combinatorial
    pool = DicePool(red=4, blue=0, black=3)
    pipeline = [make_reroll(4)]
    _, _, cost = compute_reroll_cost(pool, pipeline)
    assert cost == 28, f"Expected cost 28, got {cost}"

    result = _select_backend(pool, pipeline, "auto")
    assert result is dice_monte_carlo, (
        f"Bug confirmed: 4R+3B with reroll 4 (cost={cost}) returned combinatorial, "
        f"expected MC."
    )


def test_concrete_4R_3B_add1R_reroll5_reroll1():
    """4R+3B + [add 1R, reroll 5, reroll 1]: total=8, max_reroll=5, cost=40 > 25."""
    # Feature: reroll-timeout-fix, Property 1: Bug Condition — Expensive Reroll Selects Combinatorial
    pool = DicePool(red=4, blue=0, black=3)
    pipeline = [
        make_add_dice(red=1),
        make_reroll(5),
        make_reroll(1),
    ]
    total, max_rr, cost = compute_reroll_cost(pool, pipeline)
    assert total == 8, f"Expected total_dice 8, got {total}"
    assert max_rr == 5, f"Expected max_reroll 5, got {max_rr}"
    assert cost == 40, f"Expected cost 40, got {cost}"

    result = _select_backend(pool, pipeline, "auto")
    assert result is dice_monte_carlo, (
        f"Bug confirmed: 4R+3B + [add 1R, reroll 5, reroll 1] (cost={cost}) "
        f"returned combinatorial, expected MC."
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    passed = 0
    failed = 0
    errors = []

    # Concrete tests
    for name, fn in [
        ("5R+3B reroll 5 (cost=40)", test_concrete_5R_3B_reroll_5),
        ("4R+3B reroll 4 (cost=28)", test_concrete_4R_3B_reroll_4),
        ("4R+3B + [add 1R, reroll 5, reroll 1] (cost=40)", test_concrete_4R_3B_add1R_reroll5_reroll1),
    ]:
        try:
            fn()
            print(f"PASS: {name}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {name} — {e}")
            failed += 1
            errors.append(str(e))
        except Exception as e:
            print(f"ERROR: {name} — {type(e).__name__}: {e}")
            failed += 1
            errors.append(f"{type(e).__name__}: {e}")

    # Property-based test
    try:
        test_bug_condition_expensive_reroll_selects_monte_carlo()
        print("PASS: Property test — expensive reroll selects MC")
        passed += 1
    except AssertionError as e:
        print(f"FAIL: Property test — {e}")
        failed += 1
        errors.append(str(e))
    except Exception as e:
        print(f"FAIL: Property test — {type(e).__name__}: {e}")
        failed += 1
        errors.append(f"{type(e).__name__}: {e}")

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    if errors:
        print(f"\nCounterexamples / failures:")
        for err in errors:
            print(f"  - {err}")
