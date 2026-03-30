import sys
sys.path.insert(0, '.')

import numpy as np
import pandas as pd
from drc_stat_engine.stats.dice_monte_carlo import _build_profile_arrays, _samples_to_roll_df, combine_dice, reroll_dice, cancel_dice, add_dice_to_roll, change_die_face
from drc_stat_engine.stats.profiles import (
    red_die_ship, blue_die_ship, black_die_ship,
    red_die_squad, blue_die_squad, black_die_squad,
)
from drc_stat_engine.stats.report_engine import generate_report, _select_backend
import drc_stat_engine.stats.dice_maths_combinatories as comb_mod
import drc_stat_engine.stats.dice_monte_carlo as mc_mod
from drc_stat_engine.stats.dice_models import DicePool, AttackEffect


def test_build_profile_arrays_weights_sum_to_1():
    profiles = {
        "red_die_ship":   red_die_ship,
        "blue_die_ship":  blue_die_ship,
        "black_die_ship": black_die_ship,
        "red_die_squad":  red_die_squad,
        "blue_die_squad": blue_die_squad,
        "black_die_squad": black_die_squad,
    }
    for name, profile in profiles.items():
        arrays = _build_profile_arrays(profile)
        total = arrays["weights"].sum()
        assert abs(total - 1.0) < 1e-9, (
            f"{name}: weights sum to {total}, expected 1.0 within 1e-9"
        )


def test_samples_to_roll_df_single_die_roundtrip():
    profile = red_die_ship
    arrays = _build_profile_arrays(profile)
    n_faces = len(arrays["values"])

    N = 8000
    face_counts = np.round(arrays["weights"] * N).astype(int)
    face_counts[-1] = N - face_counts[:-1].sum()

    rows = []
    for face_idx, count in enumerate(face_counts):
        rows.extend([face_idx] * count)
    matrix = np.array(rows, dtype=np.int16).reshape(N, 1)

    df = _samples_to_roll_df(matrix, [arrays], "ship", N)

    expected_cols = ["value", "proba", "damage", "crit", "acc", "blank"]
    assert list(df.columns) == expected_cols, (
        f"columns mismatch: got {list(df.columns)}, expected {expected_cols}"
    )

    proba_sum = df["proba"].sum()
    assert abs(proba_sum - 1.0) < 1e-9, (
        f"proba sum = {proba_sum}, expected 1.0 within 1e-9"
    )

    for val in df["value"]:
        tokens = val.split(" ")
        assert tokens == sorted(tokens), (
            f"value '{val}' tokens are not sorted: {tokens}"
        )
        for tok in tokens:
            assert tok in arrays["values"], (
                f"unknown token '{tok}' in value '{val}'"
            )


# --- combine_dice unit tests ---

def test_combine_dice_correct_columns_1_die():
    df = combine_dice(1, 0, 0, "ship", sample_count=1000, seed=0)
    expected_cols = ["value", "proba", "damage", "crit", "acc", "blank"]
    assert list(df.columns) == expected_cols, (
        f"columns mismatch: got {list(df.columns)}, expected {expected_cols}"
    )


def test_combine_dice_seed_determinism():
    df1 = combine_dice(1, 1, 0, "ship", sample_count=500, seed=99)
    df2 = combine_dice(1, 1, 0, "ship", sample_count=500, seed=99)
    df1 = df1.sort_values("value").reset_index(drop=True)
    df2 = df2.sort_values("value").reset_index(drop=True)
    assert list(df1["value"]) == list(df2["value"]), "value columns differ"
    assert all(abs(a - b) < 1e-15 for a, b in zip(df1["proba"], df2["proba"])), (
        "proba columns differ"
    )


def test_combine_dice_raises_empty_pool():
    try:
        combine_dice(0, 0, 0, "ship")
        assert False, "expected ValueError for empty pool"
    except ValueError:
        pass


def test_combine_dice_raises_negative_count():
    try:
        combine_dice(-1, 0, 0, "ship")
        assert False, "expected ValueError for negative count"
    except ValueError:
        pass


def test_combine_dice_raises_invalid_type_str():
    try:
        combine_dice(1, 0, 0, "invalid")
        assert False, "expected ValueError for invalid type_str"
    except ValueError:
        pass


# --- Pipeline operation unit tests ---

def test_reroll_dice_empty_results_returns_unchanged():
    roll_df = combine_dice(1, 1, 0, "ship", sample_count=500, seed=7)
    rerolled_df, _ = reroll_dice(roll_df, [], 1, "ship")
    assert rerolled_df is roll_df, "expected same object returned when results_to_reroll is empty"


def test_cancel_dice_no_matching_faces_returns_empty_cancelled():
    roll_df = combine_dice(0, 2, 0, "ship", sample_count=500, seed=7)
    cancelled_df, kept_df = cancel_dice(roll_df, ["R_blank"], 1, "ship")
    assert len(cancelled_df) == 0, f"expected empty cancelled_df, got {len(cancelled_df)} rows"
    assert abs(kept_df["proba"].sum() - 1.0) < 1e-9, (
        f"kept_df proba sum = {kept_df['proba'].sum()}, expected 1.0"
    )


def test_add_dice_to_roll_increases_die_count():
    roll_df = combine_dice(1, 1, 0, "ship", sample_count=500, seed=7)
    original_D = roll_df.attrs["_mc_state"]["matrix"].shape[1]
    added_df = add_dice_to_roll(roll_df, 0, 0, 1, "ship")
    new_D = added_df.attrs["_mc_state"]["matrix"].shape[1]
    assert new_D == original_D + 1, f"expected {original_D + 1} dice, got {new_D}"


# --- Task 5.4: Backend selection unit tests ---

REQUIRED_KEYS = {"label", "damage", "accuracy", "crit", "avg_damage", "priority_list", "damage_zero", "acc_zero"}


def test_select_backend_auto_small_pool():
    pool = DicePool(red=2, blue=1, black=0, type="ship")  # pool_size=3
    result = _select_backend(pool, "auto")
    assert result is comb_mod, f"expected comb_mod, got {result}"


def test_select_backend_auto_large_pool():
    pool = DicePool(red=5, blue=2, black=2, type="ship")  # pool_size=9
    result = _select_backend(pool, "auto")
    assert result is mc_mod, f"expected mc_mod, got {result}"


def test_select_backend_explicit_combinatorial():
    pool = DicePool(red=1, blue=0, black=0, type="ship")
    result = _select_backend(pool, "combinatorial")
    assert result is comb_mod, f"expected comb_mod, got {result}"


def test_select_backend_explicit_montecarlo():
    pool = DicePool(red=1, blue=0, black=0, type="ship")
    result = _select_backend(pool, "montecarlo")
    assert result is mc_mod, f"expected mc_mod, got {result}"


def test_select_backend_raises_unknown():
    pool = DicePool(red=1, blue=0, black=0, type="ship")
    try:
        _select_backend(pool, "unknown")
        assert False, "expected ValueError for unknown backend"
    except ValueError:
        pass


def test_generate_report_auto_uses_combinatorial_for_small_pool():
    pool = DicePool(red=2, blue=1, black=0, type="ship")  # pool_size=3
    variants = generate_report(pool, [], backend="auto")
    assert len(variants) > 0
    for v in variants:
        missing = REQUIRED_KEYS - set(v.keys())
        assert not missing, f"missing keys: {missing}"


def test_generate_report_auto_uses_mc_for_large_pool():
    pool = DicePool(red=5, blue=2, black=2, type="ship")  # pool_size=9
    variants = generate_report(pool, [], backend="auto", sample_count=500, seed=42)
    assert len(variants) > 0
    for v in variants:
        missing = REQUIRED_KEYS - set(v.keys())
        assert not missing, f"missing keys: {missing}"


def test_generate_report_montecarlo_returns_required_keys():
    pool = DicePool(red=2, blue=1, black=0, type="ship")
    variants = generate_report(pool, [], backend="montecarlo", sample_count=500, seed=42)
    assert len(variants) > 0
    for v in variants:
        missing = REQUIRED_KEYS - set(v.keys())
        assert not missing, f"missing keys: {missing}"


if __name__ == "__main__":
    test_build_profile_arrays_weights_sum_to_1()
    print("PASS: test_build_profile_arrays_weights_sum_to_1")
    test_samples_to_roll_df_single_die_roundtrip()
    print("PASS: test_samples_to_roll_df_single_die_roundtrip")
    test_combine_dice_correct_columns_1_die()
    print("PASS: test_combine_dice_correct_columns_1_die")
    test_combine_dice_seed_determinism()
    print("PASS: test_combine_dice_seed_determinism")
    test_combine_dice_raises_empty_pool()
    print("PASS: test_combine_dice_raises_empty_pool")
    test_combine_dice_raises_negative_count()
    print("PASS: test_combine_dice_raises_negative_count")
    test_combine_dice_raises_invalid_type_str()
    print("PASS: test_combine_dice_raises_invalid_type_str")
    test_reroll_dice_empty_results_returns_unchanged()
    print("PASS: test_reroll_dice_empty_results_returns_unchanged")
    test_cancel_dice_no_matching_faces_returns_empty_cancelled()
    print("PASS: test_cancel_dice_no_matching_faces_returns_empty_cancelled")
    test_add_dice_to_roll_increases_die_count()
    print("PASS: test_add_dice_to_roll_increases_die_count")
    test_select_backend_auto_small_pool()
    print("PASS: test_select_backend_auto_small_pool")
    test_select_backend_auto_large_pool()
    print("PASS: test_select_backend_auto_large_pool")
    test_select_backend_explicit_combinatorial()
    print("PASS: test_select_backend_explicit_combinatorial")
    test_select_backend_explicit_montecarlo()
    print("PASS: test_select_backend_explicit_montecarlo")
    test_select_backend_raises_unknown()
    print("PASS: test_select_backend_raises_unknown")
    test_generate_report_auto_uses_combinatorial_for_small_pool()
    print("PASS: test_generate_report_auto_uses_combinatorial_for_small_pool")
    test_generate_report_auto_uses_mc_for_large_pool()
    print("PASS: test_generate_report_auto_uses_mc_for_large_pool")
    test_generate_report_montecarlo_returns_required_keys()
    print("PASS: test_generate_report_montecarlo_returns_required_keys")
    print("ALL UNIT TESTS PASSED")
