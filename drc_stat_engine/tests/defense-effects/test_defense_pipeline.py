"""Property-based tests for defense pipeline functions (Properties 6-10).

Feature: defense-effects, Properties 6-10: Defense pipeline damage modification and sorting
**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4**

Uses Hypothesis to verify:
- Property 6: reduce_damage_df formula correctness
- Property 7: divide_damage_df formula correctness
- Property 8: Damage modification preserves non-damage columns
- Property 9: Damage modification preserves probability mass
- Property 10: sort_defense_pipeline enforces fixed order with stable sub-ordering
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from drc_stat_engine.stats.report_engine import sort_defense_pipeline, reduce_damage_df, divide_damage_df
from drc_stat_engine.stats.dice_models import DefenseEffect

# ---------------------------------------------------------------------------
# Strategies / Generators
# ---------------------------------------------------------------------------

@st.composite
def roll_dataframes(draw):
    """Generate a roll DataFrame with realistic columns and normalized probabilities."""
    n_rows = draw(st.integers(min_value=1, max_value=20))
    rows = []
    for _ in range(n_rows):
        rows.append({
            "value": draw(st.sampled_from(["R_hit", "U_crit", "B_blank", "R_hit+hit", "B_hit+crit", "R_blank"])),
            "damage": draw(st.integers(min_value=0, max_value=10)),
            "crit": draw(st.integers(min_value=0, max_value=3)),
            "acc": draw(st.integers(min_value=0, max_value=3)),
            "blank": draw(st.integers(min_value=0, max_value=3)),
        })
    df = pd.DataFrame(rows)
    # Assign normalized probabilities
    raw_proba = draw(st.lists(st.floats(min_value=0.01, max_value=1.0), min_size=n_rows, max_size=n_rows))
    total = sum(raw_proba)
    df["proba"] = [p / total for p in raw_proba]
    return df


@st.composite
def defense_effect_lists(draw):
    """Generate random lists of DefenseEffect for pipeline sorting tests."""
    n = draw(st.integers(min_value=0, max_value=10))
    effects = []
    for _ in range(n):
        t = draw(st.sampled_from(["defense_reroll", "defense_cancel", "reduce_damage", "divide_damage"]))
        if t == "defense_reroll":
            effects.append(DefenseEffect(type=t, count=1, mode=draw(st.sampled_from(["safe", "could_be_blank"]))))
        elif t == "defense_cancel":
            effects.append(DefenseEffect(type=t, count=1))
        elif t == "reduce_damage":
            effects.append(DefenseEffect(type=t, amount=draw(st.integers(min_value=1, max_value=5))))
        else:
            effects.append(DefenseEffect(type=t))
    return effects


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------
passed = 0
failed = 0
errors = []

# ---------------------------------------------------------------------------
# Property 6: Reduce damage formula
# Feature: defense-effects, Property 6: Reduce damage formula
# **Validates: Requirements 4.1, 4.2**
# For any roll_df and positive N, reduce_damage_df sets damage to
# max(0, damage - N), no negative values.
# ---------------------------------------------------------------------------
t6_pass = True
t6_error = None

try:
    @given(roll_df=roll_dataframes(), amount=st.integers(min_value=1, max_value=10))
    @settings(max_examples=100)
    def test_reduce_damage_formula(roll_df, amount):
        original_damages = roll_df["damage"].tolist()
        result = reduce_damage_df(roll_df, amount)

        # After groupby, we need to verify the formula by checking that every
        # damage value in the result is max(0, original - amount) for some original.
        # More precisely: the set of damage values in the result should be exactly
        # {max(0, d - amount) for d in original_damages}.
        expected_damages = {max(0, d - amount) for d in original_damages}
        actual_damages = set(result["damage"].tolist())
        assert actual_damages == expected_damages, (
            f"amount={amount}, expected damage set={expected_damages}, got={actual_damages}"
        )

        # Verify no negative damage values
        assert (result["damage"] >= 0).all(), (
            f"Negative damage found after reduce_damage_df: {result['damage'].tolist()}"
        )

        # Verify row-level formula: for each unique (value, damage, crit, acc, blank)
        # in the result, the damage should be max(0, original_damage - amount)
        # We verify this by checking that each row's damage is achievable
        for _, row in result.iterrows():
            assert row["damage"] >= 0, f"Negative damage: {row['damage']}"

    test_reduce_damage_formula()
except Exception as e:
    t6_pass = False
    t6_error = str(e)

if t6_pass:
    print("PASS: Property 6 — reduce_damage_df sets damage to max(0, damage - N), no negatives")
    passed += 1
else:
    print(f"FAIL: Property 6 — {t6_error}")
    failed += 1
    errors.append(("Property 6: Reduce damage formula", t6_error))

# ---------------------------------------------------------------------------
# Property 7: Divide damage formula
# Feature: defense-effects, Property 7: Divide damage formula
# **Validates: Requirements 5.1, 5.2, 5.3**
# For any roll_df, divide_damage_df sets damage to ceil(damage / 2),
# zero stays zero, odd rounds up.
# ---------------------------------------------------------------------------
t7_pass = True
t7_error = None

try:
    @given(roll_df=roll_dataframes())
    @settings(max_examples=100)
    def test_divide_damage_formula(roll_df):
        original_damages = roll_df["damage"].tolist()
        result = divide_damage_df(roll_df)

        # The set of damage values in the result should be exactly
        # {(d + 1) // 2 for d in original_damages}
        expected_damages = {(d + 1) // 2 for d in original_damages}
        actual_damages = set(result["damage"].tolist())
        assert actual_damages == expected_damages, (
            f"expected damage set={expected_damages}, got={actual_damages}"
        )

        # Verify zero stays zero
        if 0 in set(original_damages):
            assert 0 in actual_damages, "Zero damage should remain zero after divide"

        # Verify odd rounds up: for each original odd damage d,
        # (d + 1) // 2 should be in the result
        for d in original_damages:
            expected = (d + 1) // 2
            assert expected in actual_damages, (
                f"Original damage {d} should map to {expected}, not found in result"
            )

    test_divide_damage_formula()
except Exception as e:
    t7_pass = False
    t7_error = str(e)

if t7_pass:
    print("PASS: Property 7 — divide_damage_df sets damage to ceil(damage / 2)")
    passed += 1
else:
    print(f"FAIL: Property 7 — {t7_error}")
    failed += 1
    errors.append(("Property 7: Divide damage formula", t7_error))


# ---------------------------------------------------------------------------
# Property 8: Damage modification preserves non-damage columns
# Feature: defense-effects, Property 8: Damage modification preserves non-damage columns
# **Validates: Requirements 4.3, 5.4**
# For any roll_df, reduce_damage and divide_damage do not modify
# crit, acc, blank columns. The set of (value, crit, acc, blank) tuples
# should be the same before and after.
# ---------------------------------------------------------------------------
t8_pass = True
t8_error = None

try:
    @given(roll_df=roll_dataframes(), amount=st.integers(min_value=1, max_value=10))
    @settings(max_examples=100)
    def test_damage_mod_preserves_non_damage_columns(roll_df, amount):
        # Capture original (value, crit, acc, blank) tuples
        original_tuples = set(
            tuple(row) for row in roll_df[["value", "crit", "acc", "blank"]].values.tolist()
        )

        # Test reduce_damage_df
        reduced = reduce_damage_df(roll_df, amount)
        reduced_tuples = set(
            tuple(row) for row in reduced[["value", "crit", "acc", "blank"]].values.tolist()
        )
        assert reduced_tuples == original_tuples, (
            f"reduce_damage changed non-damage columns: "
            f"original={original_tuples}, after={reduced_tuples}"
        )

        # Test divide_damage_df
        divided = divide_damage_df(roll_df)
        divided_tuples = set(
            tuple(row) for row in divided[["value", "crit", "acc", "blank"]].values.tolist()
        )
        assert divided_tuples == original_tuples, (
            f"divide_damage changed non-damage columns: "
            f"original={original_tuples}, after={divided_tuples}"
        )

    test_damage_mod_preserves_non_damage_columns()
except Exception as e:
    t8_pass = False
    t8_error = str(e)

if t8_pass:
    print("PASS: Property 8 — damage modification preserves crit, acc, blank columns")
    passed += 1
else:
    print(f"FAIL: Property 8 — {t8_error}")
    failed += 1
    errors.append(("Property 8: Preserves non-damage columns", t8_error))

# ---------------------------------------------------------------------------
# Property 9: Damage modification preserves probability mass
# Feature: defense-effects, Property 9: Damage modification preserves probability mass
# **Validates: Requirements 4.4, 5.5**
# For any roll_df where proba sums to 1.0, after reduce or divide,
# proba still sums to 1.0 (within 1e-9).
# ---------------------------------------------------------------------------
t9_pass = True
t9_error = None

try:
    @given(roll_df=roll_dataframes(), amount=st.integers(min_value=1, max_value=10))
    @settings(max_examples=100)
    def test_damage_mod_preserves_probability_mass(roll_df, amount):
        original_sum = roll_df["proba"].sum()
        assert abs(original_sum - 1.0) < 1e-9, (
            f"Precondition: proba should sum to 1.0, got {original_sum}"
        )

        # Test reduce_damage_df
        reduced = reduce_damage_df(roll_df, amount)
        reduced_sum = reduced["proba"].sum()
        assert abs(reduced_sum - 1.0) < 1e-9, (
            f"reduce_damage: proba sums to {reduced_sum}, expected 1.0"
        )

        # Test divide_damage_df
        divided = divide_damage_df(roll_df)
        divided_sum = divided["proba"].sum()
        assert abs(divided_sum - 1.0) < 1e-9, (
            f"divide_damage: proba sums to {divided_sum}, expected 1.0"
        )

    test_damage_mod_preserves_probability_mass()
except Exception as e:
    t9_pass = False
    t9_error = str(e)

if t9_pass:
    print("PASS: Property 9 — damage modification preserves probability mass (sum ≈ 1.0)")
    passed += 1
else:
    print(f"FAIL: Property 9 — {t9_error}")
    failed += 1
    errors.append(("Property 9: Preserves probability mass", t9_error))

# ---------------------------------------------------------------------------
# Property 10: Defense pipeline sorting enforces fixed order with stable sub-ordering
# Feature: defense-effects, Property 10: Defense pipeline sorting enforces fixed order
# **Validates: Requirements 6.1, 6.2, 6.3, 6.4**
# For any list of defense effects, sort_defense_pipeline produces
# reroll/cancel first, then reduce, then divide.
# Preserving relative order within groups.
# ---------------------------------------------------------------------------
t10_pass = True
t10_error = None

try:
    @given(effects=defense_effect_lists())
    @settings(max_examples=100)
    def test_defense_pipeline_sorting(effects):
        sorted_effects = sort_defense_pipeline(effects)

        # Verify same length
        assert len(sorted_effects) == len(effects), (
            f"Sorting changed length: {len(effects)} -> {len(sorted_effects)}"
        )

        # Verify ordering: reroll/cancel first, then reduce, then divide
        GROUP_ORDER = {"defense_reroll": 0, "defense_cancel": 0, "reduce_damage": 1, "divide_damage": 2}
        group_values = [GROUP_ORDER[e.type] for e in sorted_effects]
        assert group_values == sorted(group_values), (
            f"Sort order violated: groups={[e.type for e in sorted_effects]}, "
            f"group_values={group_values}"
        )

        # Verify stable sub-ordering within each group
        # Extract original indices for each group
        reroll_cancel_original = [e for e in effects if e.type in ("defense_reroll", "defense_cancel")]
        reduce_original = [e for e in effects if e.type == "reduce_damage"]
        divide_original = [e for e in effects if e.type == "divide_damage"]

        reroll_cancel_sorted = [e for e in sorted_effects if e.type in ("defense_reroll", "defense_cancel")]
        reduce_sorted = [e for e in sorted_effects if e.type == "reduce_damage"]
        divide_sorted = [e for e in sorted_effects if e.type == "divide_damage"]

        # Use id() to verify same objects in same relative order
        assert [id(e) for e in reroll_cancel_sorted] == [id(e) for e in reroll_cancel_original], (
            "Reroll/cancel group relative order not preserved"
        )
        assert [id(e) for e in reduce_sorted] == [id(e) for e in reduce_original], (
            "Reduce group relative order not preserved"
        )
        assert [id(e) for e in divide_sorted] == [id(e) for e in divide_original], (
            "Divide group relative order not preserved"
        )

    test_defense_pipeline_sorting()
except Exception as e:
    t10_pass = False
    t10_error = str(e)

if t10_pass:
    print("PASS: Property 10 — sort_defense_pipeline enforces fixed order with stable sub-ordering")
    passed += 1
else:
    print(f"FAIL: Property 10 — {t10_error}")
    failed += 1
    errors.append(("Property 10: Pipeline sorting", t10_error))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
if failed == 0:
    print("ALL PROPERTY TESTS PASSED")
else:
    print("SOME PROPERTY TESTS FAILED")
    for name, err in errors:
        print(f"  {name}: {err}")
