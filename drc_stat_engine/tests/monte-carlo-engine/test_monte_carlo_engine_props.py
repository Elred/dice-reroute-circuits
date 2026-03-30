import sys
sys.path.insert(0, '.')

from hypothesis import given, assume, settings
from hypothesis import strategies as st

from drc_stat_engine.stats.dice_monte_carlo import combine_dice, reroll_dice, cancel_dice, add_dice_to_roll, change_die_face
from drc_stat_engine.stats.report_engine import generate_report
from drc_stat_engine.stats.dice_models import DicePool


# Feature: monte-carlo-engine, Property 1: For any valid DicePool, proba column sums to 1.0 within 1e-9 after combine_dice
@given(
    red=st.integers(min_value=0, max_value=4),
    blue=st.integers(min_value=0, max_value=4),
    black=st.integers(min_value=0, max_value=4),
    type_str=st.sampled_from(["ship", "squad"]),
)
@settings(max_examples=100)
def test_property_1_probability_sum_invariant(red, blue, black, type_str):
    # Validates: Requirements 1.2, 8.1
    assume(red + blue + black > 0)
    roll_df = combine_dice(red, blue, black, type_str, sample_count=1000, seed=42)
    assert abs(roll_df["proba"].sum() - 1.0) < 1e-9


# Feature: monte-carlo-engine, Property 2: For any valid DicePool and seed, combine_dice returns identical Roll_DataFrames
@given(
    red=st.integers(min_value=0, max_value=3),
    blue=st.integers(min_value=0, max_value=3),
    black=st.integers(min_value=0, max_value=3),
    type_str=st.sampled_from(["ship", "squad"]),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
@settings(max_examples=100)
def test_property_2_determinism_with_seed(red, blue, black, type_str, seed):
    # Validates: Requirements 1.6, 8.4
    assume(red + blue + black > 0)
    df1 = combine_dice(red, blue, black, type_str, sample_count=500, seed=seed)
    df2 = combine_dice(red, blue, black, type_str, sample_count=500, seed=seed)
    # Sort both by value for comparison
    df1 = df1.sort_values("value").reset_index(drop=True)
    df2 = df2.sort_values("value").reset_index(drop=True)
    assert list(df1["value"]) == list(df2["value"])
    assert all(abs(a - b) < 1e-15 for a, b in zip(df1["proba"], df2["proba"]))


# Feature: monte-carlo-engine, Property 1 (pipeline variant): Probability sum invariant after each pipeline op
@given(
    red=st.integers(min_value=0, max_value=3),
    blue=st.integers(min_value=0, max_value=3),
    black=st.integers(min_value=0, max_value=3),
    type_str=st.sampled_from(["ship", "squad"]),
)
@settings(max_examples=100)
def test_property_1_pipeline_probability_sum_invariant(red, blue, black, type_str):
    # Validates: Requirements 2.5, 8.2
    assume(red + blue + black > 0)
    roll_df = combine_dice(red, blue, black, type_str, sample_count=500, seed=42)

    # reroll
    rr_df, _ = reroll_dice(roll_df, ["R_blank", "B_blank"], 1, type_str)
    assert abs(rr_df["proba"].sum() - 1.0) < 1e-9

    # cancel (merge cancelled + kept)
    canc_df, kept_df = cancel_dice(roll_df, ["R_blank", "B_blank"], 1, type_str)
    import pandas as pd
    # Clear attrs before concat to avoid numpy array comparison error in pandas
    canc_copy = canc_df.copy()
    canc_copy.attrs = {}
    kept_copy = kept_df.copy()
    kept_copy.attrs = {}
    merged = pd.concat([canc_copy, kept_copy]).groupby("value", as_index=False).agg(
        {"proba": "sum", "damage": "first", "crit": "first", "acc": "first", "blank": "first"}
    )
    assert abs(merged["proba"].sum() - 1.0) < 1e-9

    # add_dice
    added_df = add_dice_to_roll(roll_df, 1, 0, 0, type_str)
    assert abs(added_df["proba"].sum() - 1.0) < 1e-9

    # change_die_face
    changed_df = change_die_face(roll_df, ["R_blank", "B_blank"], "R_hit", type_str)
    assert abs(changed_df["proba"].sum() - 1.0) < 1e-9


# Feature: monte-carlo-engine, Property 3: Auto backend routing by pool size
@given(
    red=st.integers(min_value=0, max_value=5),
    blue=st.integers(min_value=0, max_value=5),
    black=st.integers(min_value=0, max_value=5),
    type_str=st.sampled_from(["ship", "squad"]),
)
@settings(max_examples=100)
def test_property_3_auto_backend_routing(red, blue, black, type_str):
    # Validates: Requirements 3.1, 3.2
    assume(red + blue + black > 0)
    import drc_stat_engine.stats.dice_maths_combinatories as comb
    import drc_stat_engine.stats.dice_monte_carlo as mc
    from drc_stat_engine.stats.report_engine import _select_backend

    pool = DicePool(red=red, blue=blue, black=black, type=type_str)
    pool_size = red + blue + black
    selected = _select_backend(pool, "auto")

    if pool_size <= 8:
        assert selected is comb, f"pool_size={pool_size} should use combinatorial, got {selected}"
    else:
        assert selected is mc, f"pool_size={pool_size} should use MC, got {selected}"


# Feature: monte-carlo-engine, Property 4: Explicit backend override
@given(
    red=st.integers(min_value=0, max_value=5),
    blue=st.integers(min_value=0, max_value=5),
    black=st.integers(min_value=0, max_value=5),
    type_str=st.sampled_from(["ship", "squad"]),
)
@settings(max_examples=100)
def test_property_4_explicit_backend_override(red, blue, black, type_str):
    # Validates: Requirements 3.4, 3.5
    assume(red + blue + black > 0)
    import drc_stat_engine.stats.dice_maths_combinatories as comb
    import drc_stat_engine.stats.dice_monte_carlo as mc
    from drc_stat_engine.stats.report_engine import _select_backend

    pool = DicePool(red=red, blue=blue, black=black, type=type_str)

    assert _select_backend(pool, "combinatorial") is comb
    assert _select_backend(pool, "montecarlo") is mc


# Feature: monte-carlo-engine, Property 5: Output variant dict structure
@given(
    red=st.integers(min_value=0, max_value=3),
    blue=st.integers(min_value=0, max_value=3),
    black=st.integers(min_value=0, max_value=3),
    type_str=st.sampled_from(["ship", "squad"]),
)
@settings(max_examples=100)
def test_property_5_output_variant_dict_structure(red, blue, black, type_str):
    # Validates: Requirements 4.1, 4.2, 4.3
    assume(red + blue + black > 0)
    pool = DicePool(red=red, blue=blue, black=black, type=type_str)
    variants = generate_report(pool, [], backend="montecarlo", sample_count=500, seed=42)

    required_keys = {"label", "damage", "accuracy", "crit", "avg_damage", "priority_list", "damage_zero", "acc_zero"}
    for v in variants:
        assert required_keys.issubset(set(v.keys())), f"missing keys: {required_keys - set(v.keys())}"
        # damage and accuracy must be lists of (threshold, probability) tuples
        assert isinstance(v["damage"], list)
        assert isinstance(v["accuracy"], list)
        for item in v["damage"]:
            assert len(item) == 2, f"damage item not a 2-tuple: {item}"
            threshold, prob = item
            assert isinstance(threshold, int), f"threshold not int: {threshold}"
            assert 0.0 <= prob <= 1.0 + 1e-9, f"prob out of range: {prob}"
        for item in v["accuracy"]:
            assert len(item) == 2
            threshold, prob = item
            assert isinstance(threshold, int)
            assert 0.0 <= prob <= 1.0 + 1e-9
        # damage list covers 0..max_damage
        if v["damage"]:
            thresholds = [t for t, _ in v["damage"]]
            assert thresholds[0] == 0, f"damage list doesn't start at 0: {thresholds[0]}"
            assert thresholds == list(range(len(thresholds))), f"damage thresholds not consecutive: {thresholds}"


# Feature: monte-carlo-engine, Property 6: CDF monotonicity
@given(
    red=st.integers(min_value=0, max_value=3),
    blue=st.integers(min_value=0, max_value=3),
    black=st.integers(min_value=0, max_value=3),
    type_str=st.sampled_from(["ship", "squad"]),
)
@settings(max_examples=100)
def test_property_6_cdf_monotonicity(red, blue, black, type_str):
    # Validates: Requirements 4.4, 4.5, 8.5, 8.6
    assume(red + blue + black > 0)
    pool = DicePool(red=red, blue=blue, black=black, type=type_str)
    variants = generate_report(pool, [], backend="montecarlo", sample_count=500, seed=42)

    for v in variants:
        # damage CDF must be monotonically non-increasing
        damage_probs = [p for _, p in v["damage"]]
        for i in range(len(damage_probs) - 1):
            assert damage_probs[i] >= damage_probs[i+1] - 1e-12, (
                f"damage CDF not monotone at index {i}: {damage_probs[i]} < {damage_probs[i+1]}"
            )
        # accuracy CDF must be monotonically non-increasing
        acc_probs = [p for _, p in v["accuracy"]]
        for i in range(len(acc_probs) - 1):
            assert acc_probs[i] >= acc_probs[i+1] - 1e-12, (
                f"accuracy CDF not monotone at index {i}: {acc_probs[i]} < {acc_probs[i+1]}"
            )


# Feature: monte-carlo-engine, Property 7: Model-based convergence at 10k samples
@given(
    red=st.integers(min_value=0, max_value=3),
    blue=st.integers(min_value=0, max_value=3),
    black=st.integers(min_value=0, max_value=3),
    type_str=st.sampled_from(["ship", "squad"]),
)
@settings(max_examples=50)
def test_property_7_model_based_convergence_10k(red, blue, black, type_str):
    # Validates: Requirements 5.1, 5.2, 5.3, 8.7
    # Pool_Size <= 6 only
    assume(0 < red + blue + black <= 6)
    pool = DicePool(red=red, blue=blue, black=black, type=type_str)

    # Run both engines with no pipeline, max_damage strategy
    comb_variants = generate_report(pool, [], strategies=["max_damage"], backend="combinatorial")
    mc_variants   = generate_report(pool, [], strategies=["max_damage"], backend="montecarlo",
                                    sample_count=10_000, seed=42)

    comb_v = comb_variants[0]
    mc_v   = mc_variants[0]

    # avg_damage within 0.15
    assert abs(mc_v["avg_damage"] - comb_v["avg_damage"]) <= 0.15, (
        f"avg_damage: MC={mc_v['avg_damage']:.4f}, comb={comb_v['avg_damage']:.4f}, "
        f"diff={abs(mc_v['avg_damage'] - comb_v['avg_damage']):.4f}"
    )

    # crit probability within 0.05
    assert abs(mc_v["crit"] - comb_v["crit"]) <= 0.05, (
        f"crit: MC={mc_v['crit']:.4f}, comb={comb_v['crit']:.4f}"
    )

    # P(damage >= x) within 0.05 for each threshold
    comb_dmg = dict(comb_v["damage"])
    mc_dmg   = dict(mc_v["damage"])
    for threshold in comb_dmg:
        if threshold in mc_dmg:
            diff = abs(mc_dmg[threshold] - comb_dmg[threshold])
            assert diff <= 0.05, (
                f"P(damage>={threshold}): MC={mc_dmg[threshold]:.4f}, "
                f"comb={comb_dmg[threshold]:.4f}, diff={diff:.4f}"
            )


# Feature: monte-carlo-engine, Property 8: Convergence improves with sample count
@given(
    red=st.integers(min_value=0, max_value=3),
    blue=st.integers(min_value=0, max_value=3),
    black=st.integers(min_value=0, max_value=3),
    type_str=st.sampled_from(["ship", "squad"]),
)
@settings(max_examples=10, deadline=None)
def test_property_8_convergence_improves_with_sample_count(red, blue, black, type_str):
    # Validates: Requirement 8.3
    assume(0 < red + blue + black <= 6)
    pool = DicePool(red=red, blue=blue, black=black, type=type_str)

    comb_variants = generate_report(pool, [], strategies=["max_damage"], backend="combinatorial")
    comb_avg = comb_variants[0]["avg_damage"]

    mc_low  = generate_report(pool, [], strategies=["max_damage"], backend="montecarlo",
                               sample_count=1_000, seed=42)
    mc_high = generate_report(pool, [], strategies=["max_damage"], backend="montecarlo",
                               sample_count=100_000, seed=42)

    err_low  = abs(mc_low[0]["avg_damage"]  - comb_avg)
    err_high = abs(mc_high[0]["avg_damage"] - comb_avg)

    # Error at 100k should be strictly less than error at 1k
    # Allow a small tolerance for edge cases where both errors are near zero
    assert err_high < err_low + 0.02, (
        f"convergence did not improve: err@1k={err_low:.4f}, err@100k={err_high:.4f}"
    )


if __name__ == "__main__":
    test_property_1_probability_sum_invariant()
    print("PASS: Property 1 — probability sum invariant")
    test_property_2_determinism_with_seed()
    print("PASS: Property 2 — determinism with seed")
    test_property_1_pipeline_probability_sum_invariant()
    print("PASS: Property 1 (pipeline variant) — probability sum invariant after pipeline ops")
    test_property_3_auto_backend_routing()
    print("PASS: Property 3 — auto backend routing by pool size")
    test_property_4_explicit_backend_override()
    print("PASS: Property 4 — explicit backend override")
    test_property_5_output_variant_dict_structure()
    print("PASS: Property 5 — output variant dict structure")
    test_property_6_cdf_monotonicity()
    print("PASS: Property 6 — CDF monotonicity")
    test_property_7_model_based_convergence_10k()
    print("PASS: Property 7 — model-based convergence at 10k samples")
    test_property_8_convergence_improves_with_sample_count()
    print("PASS: Property 8 — convergence improves with sample count")
    print("ALL PROPERTY TESTS PASSED")
