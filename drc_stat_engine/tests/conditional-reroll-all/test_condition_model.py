"""
Property tests for the Condition dataclass and evaluate_condition (dice_models.py).

Properties tested:
  1. Valid Condition round-trip
  2. Invalid Condition inputs rejected
  3. Condition evaluation matches Python comparison
  4. Condition partitioning covers all rows

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7
"""
import sys
sys.path.insert(0, '.')

from hypothesis import given, settings
from hypothesis import strategies as st

import operator as op_mod

import pandas as pd

from drc_stat_engine.stats.dice_models import (
    Condition,
    evaluate_condition,
    VALID_CONDITION_ATTRIBUTES,
    VALID_CONDITION_OPERATORS,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

valid_attributes = st.sampled_from(["damage", "crit", "acc", "blank"])
valid_operators = st.sampled_from(["lte", "lt", "gte", "gt", "eq", "neq"])
valid_thresholds = st.integers(min_value=0, max_value=20)

invalid_attributes = st.text(min_size=1).filter(lambda s: s not in VALID_CONDITION_ATTRIBUTES)
invalid_operators = st.text(min_size=1).filter(lambda s: s not in VALID_CONDITION_OPERATORS)
# Non-integer thresholds: floats and strings
invalid_thresholds = st.one_of(
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(min_size=1),
)

# ---------------------------------------------------------------------------
# Feature: conditional-reroll-all, Property 1: Valid Condition round-trip
# ---------------------------------------------------------------------------

@given(attr=valid_attributes, op=valid_operators, thresh=valid_thresholds)
@settings(max_examples=100)
def test_property_1_valid_condition_round_trip(attr, op, thresh):
    """Validates: Requirements 1.1"""
    c = Condition(attribute=attr, operator=op, threshold=thresh)
    assert c.attribute == attr, f"attribute mismatch: {c.attribute} != {attr}"
    assert c.operator == op, f"operator mismatch: {c.operator} != {op}"
    assert c.threshold == thresh, f"threshold mismatch: {c.threshold} != {thresh}"

# ---------------------------------------------------------------------------
# Feature: conditional-reroll-all, Property 2: Invalid Condition inputs rejected
# ---------------------------------------------------------------------------

@given(attr=invalid_attributes, op=valid_operators, thresh=valid_thresholds)
@settings(max_examples=100)
def test_property_2a_invalid_attribute_rejected(attr, op, thresh):
    """Validates: Requirements 1.2"""
    try:
        Condition(attribute=attr, operator=op, threshold=thresh)
        assert False, f"Expected ValueError for invalid attribute '{attr}'"
    except ValueError:
        pass

@given(attr=valid_attributes, op=invalid_operators, thresh=valid_thresholds)
@settings(max_examples=100)
def test_property_2b_invalid_operator_rejected(attr, op, thresh):
    """Validates: Requirements 1.3"""
    try:
        Condition(attribute=attr, operator=op, threshold=thresh)
        assert False, f"Expected ValueError for invalid operator '{op}'"
    except ValueError:
        pass

@given(attr=valid_attributes, op=valid_operators, thresh=invalid_thresholds)
@settings(max_examples=100)
def test_property_2c_invalid_threshold_rejected(attr, op, thresh):
    """Validates: Requirements 1.4"""
    try:
        Condition(attribute=attr, operator=op, threshold=thresh)
        assert False, f"Expected ValueError for non-integer threshold {thresh!r}"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Strategies for Properties 3 & 4
# ---------------------------------------------------------------------------

# Map operator strings to Python comparison functions
OPERATOR_MAP = {
    "lte": op_mod.le,
    "lt":  op_mod.lt,
    "gte": op_mod.ge,
    "gt":  op_mod.gt,
    "eq":  op_mod.eq,
    "neq": op_mod.ne,
}

# Strategy: generate a small Roll_DataFrame with 1–10 rows.
# Each row has random non-negative ints for damage/crit/acc/blank,
# a placeholder value string, and a probability that sums to 1.
@st.composite
def roll_dataframes(draw):
    n_rows = draw(st.integers(min_value=1, max_value=10))
    rows = []
    for _ in range(n_rows):
        rows.append({
            "value": "placeholder",
            "proba": 1.0,  # will be normalised below
            "damage": draw(st.integers(min_value=0, max_value=10)),
            "crit":   draw(st.integers(min_value=0, max_value=10)),
            "acc":    draw(st.integers(min_value=0, max_value=10)),
            "blank":  draw(st.integers(min_value=0, max_value=10)),
        })
    df = pd.DataFrame(rows)
    df["proba"] = 1.0 / len(df)
    return df

# ---------------------------------------------------------------------------
# Feature: conditional-reroll-all, Property 3: Condition evaluation matches
#          Python comparison
# ---------------------------------------------------------------------------

@given(
    attr=valid_attributes,
    op=valid_operators,
    thresh=valid_thresholds,
    roll_df=roll_dataframes(),
)
@settings(max_examples=100)
def test_property_3_condition_eval_matches_python(attr, op, thresh, roll_df):
    """Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6"""
    try:
        cond = Condition(attribute=attr, operator=op, threshold=thresh)
        result = evaluate_condition(cond, roll_df)
        py_op = OPERATOR_MAP[op]
        for idx in roll_df.index:
            expected = py_op(roll_df.at[idx, attr], thresh)
            actual = result.iloc[idx]
            assert actual == expected, (
                f"Row {idx}: {attr}={roll_df.at[idx, attr]} {op} {thresh} → "
                f"expected {expected}, got {actual}"
            )
    except Exception as e:
        print(f"FAIL: Property 3 — {e}")
        raise

# ---------------------------------------------------------------------------
# Feature: conditional-reroll-all, Property 4: Condition partitioning covers
#          all rows
# ---------------------------------------------------------------------------

@given(
    attr=valid_attributes,
    op=valid_operators,
    thresh=valid_thresholds,
    roll_df=roll_dataframes(),
)
@settings(max_examples=100)
def test_property_4_condition_partitioning_covers_all_rows(attr, op, thresh, roll_df):
    """Validates: Requirements 3.7"""
    try:
        cond = Condition(attribute=attr, operator=op, threshold=thresh)
        mask = evaluate_condition(cond, roll_df)

        matching = roll_df[mask]
        non_matching = roll_df[~mask]

        # No overlap: indices are disjoint
        overlap = matching.index.intersection(non_matching.index)
        assert len(overlap) == 0, f"Overlap found: {overlap.tolist()}"

        # No omissions: union equals full index
        union = matching.index.union(non_matching.index)
        assert union.sort_values().tolist() == roll_df.index.sort_values().tolist(), (
            f"Union {union.tolist()} != full index {roll_df.index.tolist()}"
        )

        # Probability sums match
        total_proba = roll_df["proba"].sum()
        partition_proba = matching["proba"].sum() + non_matching["proba"].sum()
        assert abs(total_proba - partition_proba) < 1e-9, (
            f"Probability mismatch: total={total_proba}, partition_sum={partition_proba}"
        )
    except Exception as e:
        print(f"FAIL: Property 4 — {e}")
        raise


if __name__ == "__main__":
    test_property_1_valid_condition_round_trip()
    print("PASS: Property 1 — Valid Condition round-trip")

    test_property_2a_invalid_attribute_rejected()
    print("PASS: Property 2a — Invalid attribute rejected")

    test_property_2b_invalid_operator_rejected()
    print("PASS: Property 2b — Invalid operator rejected")

    test_property_2c_invalid_threshold_rejected()
    print("PASS: Property 2c — Invalid threshold rejected")

    test_property_3_condition_eval_matches_python()
    print("PASS: Property 3 — Condition evaluation matches Python comparison")

    test_property_4_condition_partitioning_covers_all_rows()
    print("PASS: Property 4 — Condition partitioning covers all rows")

    print("\nALL PROPERTY TESTS PASSED")
