"""
Property tests for combinatorial reroll_all_dice.

Properties tested:
  5. Probability integrity after reroll_all
  6. No-match condition returns unchanged result
  11. Fresh roll preserves pool composition

Validates: Requirements 4.2, 4.3, 4.5
"""
import sys
sys.path.insert(0, '.')

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from drc_stat_engine.stats.dice_models import Condition
from drc_stat_engine.stats.dice_maths_combinatories import (
    combine_dice,
    reroll_all_dice,
    value_to_dice_count_dict,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

@st.composite
def small_dice_pools(draw):
    """Generate small dice pools with 1-4 total dice."""
    red = draw(st.integers(min_value=0, max_value=2))
    blue = draw(st.integers(min_value=0, max_value=2))
    black = draw(st.integers(min_value=0, max_value=2))
    assume(red + blue + black >= 1)
    assume(red + blue + black <= 4)
    type_str = draw(st.sampled_from(["ship", "squad"]))
    return red, blue, black, type_str

# ---------------------------------------------------------------------------
# Feature: conditional-reroll-all, Property 5: Probability integrity after
#          reroll_all
# ---------------------------------------------------------------------------

@given(
    pool=small_dice_pools(),
    attr=st.sampled_from(["damage", "crit", "acc", "blank"]),
    op=st.sampled_from(["lte", "lt", "gte", "gt", "eq", "neq"]),
    thresh=st.integers(min_value=0, max_value=10),
)
@settings(max_examples=100, deadline=None)
def test_property_5_probability_integrity(pool, attr, op, thresh):
    """
    Validates: Requirements 4.2, 4.5

    For any dice pool and any valid Condition, after applying reroll_all_dice
    via the combinatorial backend, the resulting Roll_DataFrame's probabilities
    should sum to 1.0 within tolerance (1e-9).
    """
    red, blue, black, type_str = pool
    roll_df = combine_dice(red, blue, black, type_str)
    cond = Condition(attribute=attr, operator=op, threshold=thresh)
    result_df, _ = reroll_all_dice(roll_df, condition=cond, type_str=type_str)
    total = result_df["proba"].sum()
    assert abs(total - 1.0) < 1e-9, f"Probability sum {total} != 1.0"

# ---------------------------------------------------------------------------
# Feature: conditional-reroll-all, Property 6: No-match condition returns
#          unchanged result
# ---------------------------------------------------------------------------

@given(pool=small_dice_pools())
@settings(max_examples=100, deadline=None)
def test_property_6_no_match_returns_unchanged(pool):
    """
    Validates: Requirements 4.3

    For any Roll_DataFrame and any Condition that matches zero rows
    (e.g. damage gt 999), reroll_all_dice should return a result
    Roll_DataFrame identical to the input.
    """
    red, blue, black, type_str = pool
    roll_df = combine_dice(red, blue, black, type_str)
    # damage gt 999 matches zero rows for any reasonable pool
    cond = Condition(attribute="damage", operator="gt", threshold=999)
    result_df, _ = reroll_all_dice(roll_df, condition=cond, type_str=type_str)
    # Result should be identical to input
    merged = roll_df.merge(result_df, on="value", suffixes=("_orig", "_result"))
    assert len(merged) == len(roll_df), (
        f"Row count mismatch: original {len(roll_df)}, result {len(result_df)}, merged {len(merged)}"
    )
    for _, row in merged.iterrows():
        assert abs(row["proba_orig"] - row["proba_result"]) < 1e-12, (
            f"Proba mismatch for {row['value']}: {row['proba_orig']} vs {row['proba_result']}"
        )

# ---------------------------------------------------------------------------
# Feature: conditional-reroll-all, Property 11: Fresh roll preserves pool
#          composition
# ---------------------------------------------------------------------------

@given(
    pool=small_dice_pools(),
    attr=st.sampled_from(["damage", "crit", "acc", "blank"]),
    op=st.sampled_from(["lte", "gte", "eq"]),
    thresh=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=100, deadline=None)
def test_property_11_fresh_roll_preserves_pool_composition(pool, attr, op, thresh):
    """
    Validates: Requirements 4.2

    For any dice pool and any Condition that matches at least one row,
    after reroll_all_dice via the combinatorial backend, every value string
    in the result should contain the same number of red, blue, and black
    dice as the original pool.
    """
    red, blue, black, type_str = pool
    roll_df = combine_dice(red, blue, black, type_str)
    cond = Condition(attribute=attr, operator=op, threshold=thresh)
    result_df, _ = reroll_all_dice(roll_df, condition=cond, type_str=type_str)
    expected_counts = {"red": red, "blue": blue, "black": black}
    for _, row in result_df.iterrows():
        actual = value_to_dice_count_dict(row["value"], type_str)
        assert actual == expected_counts, (
            f"Pool composition mismatch: {actual} != {expected_counts} "
            f"for value '{row['value']}'"
        )


if __name__ == "__main__":
    test_property_5_probability_integrity()
    print("PASS: Property 5 — Probability integrity after reroll_all")

    test_property_6_no_match_returns_unchanged()
    print("PASS: Property 6 — No-match condition returns unchanged result")

    test_property_11_fresh_roll_preserves_pool_composition()
    print("PASS: Property 11 — Fresh roll preserves pool composition")

    print("\nALL PROPERTY TESTS PASSED")
