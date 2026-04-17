"""
Property tests for Monte Carlo reroll_all_dice.

Properties tested:
  7. MC and combinatorial backends agree

Validates: Requirements 5.1
"""
import sys
sys.path.insert(0, '.')

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from drc_stat_engine.stats.dice_models import Condition
import drc_stat_engine.stats.dice_maths_combinatories as comb
import drc_stat_engine.stats.dice_monte_carlo as mc

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

@st.composite
def small_dice_pools(draw):
    """Generate small dice pools with 1-3 total dice."""
    red = draw(st.integers(min_value=0, max_value=2))
    blue = draw(st.integers(min_value=0, max_value=2))
    black = draw(st.integers(min_value=0, max_value=2))
    assume(red + blue + black >= 1)
    assume(red + blue + black <= 3)
    type_str = draw(st.sampled_from(["ship", "squad"]))
    return red, blue, black, type_str

# ---------------------------------------------------------------------------
# Feature: conditional-reroll-all, Property 7: MC and combinatorial backends
#          agree
# ---------------------------------------------------------------------------

@given(
    pool=small_dice_pools(),
    attr=st.sampled_from(["damage", "crit", "acc", "blank"]),
    op=st.sampled_from(["lte", "gte", "eq"]),
    thresh=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=50, deadline=None)
def test_property_7_mc_combinatorial_agreement(pool, attr, op, thresh):
    """
    Validates: Requirements 5.1

    For any small dice pool (≤ 3 dice) and any valid Condition, the average
    damage computed by the Monte Carlo backend's reroll_all_dice (with a large
    sample count) should be within a reasonable tolerance of the combinatorial
    backend's exact result.
    """
    red, blue, black, type_str = pool
    cond = Condition(attribute=attr, operator=op, threshold=thresh)

    # Combinatorial (exact)
    comb_roll = comb.combine_dice(red, blue, black, type_str)
    comb_result, _ = comb.reroll_all_dice(comb_roll, condition=cond, type_str=type_str)
    comb_avg = (comb_result["damage"] * comb_result["proba"]).sum()

    # Monte Carlo (approximate) — use large sample for accuracy
    mc_roll = mc.combine_dice(red, blue, black, type_str, sample_count=100_000, seed=42)
    mc_result, _ = mc.reroll_all_dice(mc_roll, condition=cond, type_str=type_str)
    mc_avg = (mc_result["damage"] * mc_result["proba"]).sum()

    # Tolerance: 0.15 for MC approximation
    assert abs(comb_avg - mc_avg) < 0.15, (
        f"MC avg damage {mc_avg:.4f} differs from combinatorial {comb_avg:.4f} "
        f"by {abs(comb_avg - mc_avg):.4f} (tolerance 0.15)"
    )


if __name__ == "__main__":
    test_property_7_mc_combinatorial_agreement()
    print("PASS: Property 7 — MC and combinatorial backends agree")

    print("\nALL PROPERTY TESTS PASSED")
