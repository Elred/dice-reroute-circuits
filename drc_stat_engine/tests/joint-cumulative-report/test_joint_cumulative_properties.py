"""
Property-based tests for joint_cumulative_damage_accuracy.

Feature: joint-cumulative-report
"""
import sys
sys.path.insert(0, '.')

import numpy as np
import pandas as pd
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from drc_stat_engine.stats.report_engine import (
    joint_cumulative_damage_accuracy,
    cumulative_damage,
    cumulative_accuracy,
)


# ---------------------------------------------------------------------------
# Hypothesis strategy: generate valid roll DataFrames
# ---------------------------------------------------------------------------

@st.composite
def roll_dataframes(draw):
    """Generate a valid roll DataFrame with random damage, acc, and probabilities."""
    n_rows = draw(st.integers(min_value=1, max_value=50))
    damage = draw(st.lists(st.integers(min_value=0, max_value=10), min_size=n_rows, max_size=n_rows))
    acc = draw(st.lists(st.integers(min_value=0, max_value=5), min_size=n_rows, max_size=n_rows))
    crit = draw(st.lists(st.integers(min_value=0, max_value=2), min_size=n_rows, max_size=n_rows))
    blank = draw(st.lists(st.integers(min_value=0, max_value=2), min_size=n_rows, max_size=n_rows))

    # Generate probabilities that sum to 1.0 using Dirichlet-like approach
    raw_weights = draw(st.lists(
        st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
        min_size=n_rows, max_size=n_rows,
    ))
    total = sum(raw_weights)
    proba = [w / total for w in raw_weights]

    # Generate unique value strings
    values = [f"v{i}" for i in range(n_rows)]

    df = pd.DataFrame({
        "value": values,
        "proba": proba,
        "damage": damage,
        "crit": crit,
        "acc": acc,
        "blank": blank,
    })
    return df


# ---------------------------------------------------------------------------
# Feature: joint-cumulative-report, Property 1: Joint cumulative oracle correctness
# ---------------------------------------------------------------------------

@given(roll_df=roll_dataframes())
@settings(max_examples=100)
def test_property_1_oracle_correctness(roll_df):
    """
    For any valid roll DataFrame, verify every matrix[i][j] equals the brute-force
    sum of proba where damage >= i AND acc >= j.

    Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.6, 3.1, 3.2, 3.3
    """
    result = joint_cumulative_damage_accuracy(roll_df)

    max_damage = int(roll_df["damage"].max())
    max_acc = int(roll_df["acc"].max())

    # Verify threshold arrays
    assert result["damage_thresholds"] == list(range(0, max_damage + 1)), \
        f"Expected damage_thresholds [0..{max_damage}], got {result['damage_thresholds']}"
    assert result["accuracy_thresholds"] == list(range(0, max_acc + 1)), \
        f"Expected accuracy_thresholds [0..{max_acc}], got {result['accuracy_thresholds']}"

    matrix = result["matrix"]

    # Verify matrix shape
    assert len(matrix) == max_damage + 1, \
        f"Expected {max_damage + 1} rows, got {len(matrix)}"
    assert len(matrix[0]) == max_acc + 1, \
        f"Expected {max_acc + 1} columns, got {len(matrix[0])}"

    # Verify each cell against brute-force oracle
    for i in range(max_damage + 1):
        for j in range(max_acc + 1):
            expected = float(
                roll_df.loc[(roll_df["damage"] >= i) & (roll_df["acc"] >= j), "proba"].sum()
            )
            actual = matrix[i][j]
            assert abs(actual - expected) < 1e-12, \
                f"matrix[{i}][{j}] = {actual}, expected {expected} (diff={abs(actual-expected)})"

    # Verify matrix[0][0] == 1.0 (all outcomes satisfy damage>=0 AND acc>=0)
    assert abs(matrix[0][0] - 1.0) < 1e-12, \
        f"matrix[0][0] should be 1.0, got {matrix[0][0]}"

    # Verify all values in [0.0, 1.0]
    for i in range(max_damage + 1):
        for j in range(max_acc + 1):
            assert -1e-12 <= matrix[i][j] <= 1.0 + 1e-12, \
                f"matrix[{i}][{j}] = {matrix[i][j]} out of [0, 1] range"


# ---------------------------------------------------------------------------
# Feature: joint-cumulative-report, Property 2: Marginal consistency
# ---------------------------------------------------------------------------

@given(roll_df=roll_dataframes())
@settings(max_examples=100)
def test_property_2_marginal_consistency(roll_df):
    """
    For any valid roll DataFrame, verify:
    - matrix[i][0] matches cumulative_damage values
    - matrix[0][j] matches cumulative_accuracy values
    - matrix[i][j] <= matrix[i][0] and matrix[i][j] <= matrix[0][j] for all (i, j)

    Validates: Requirements 1.5
    """
    result = joint_cumulative_damage_accuracy(roll_df)
    matrix = result["matrix"]

    # Get marginals from existing functions
    cum_damage = cumulative_damage(roll_df)
    cum_accuracy = cumulative_accuracy(roll_df)

    max_damage = int(roll_df["damage"].max())
    max_acc = int(roll_df["acc"].max())

    # Verify matrix[i][0] matches cumulative_damage
    for i, (threshold, prob) in enumerate(cum_damage):
        assert abs(matrix[i][0] - prob) < 1e-12, \
            f"matrix[{i}][0] = {matrix[i][0]}, cumulative_damage[{i}] = {prob}"

    # Verify matrix[0][j] matches cumulative_accuracy
    for j, (threshold, prob) in enumerate(cum_accuracy):
        assert abs(matrix[0][j] - prob) < 1e-12, \
            f"matrix[0][{j}] = {matrix[0][j]}, cumulative_accuracy[{j}] = {prob}"

    # Verify joint <= marginals for all (i, j)
    for i in range(max_damage + 1):
        for j in range(max_acc + 1):
            assert matrix[i][j] <= matrix[i][0] + 1e-12, \
                f"matrix[{i}][{j}] = {matrix[i][j]} > matrix[{i}][0] = {matrix[i][0]}"
            assert matrix[i][j] <= matrix[0][j] + 1e-12, \
                f"matrix[{i}][{j}] = {matrix[i][j]} > matrix[0][{j}] = {matrix[0][j]}"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Running Property 1: Oracle correctness...")
    try:
        test_property_1_oracle_correctness()
        print("PASS: Property 1 — oracle correctness")
    except Exception as e:
        print(f"FAIL: Property 1 — {e}")
        sys.exit(1)

    print("Running Property 2: Marginal consistency...")
    try:
        test_property_2_marginal_consistency()
        print("PASS: Property 2 — marginal consistency")
    except Exception as e:
        print(f"FAIL: Property 2 — {e}")
        sys.exit(1)

    print("\nAll property tests passed.")
