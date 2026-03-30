"""
dice_monte_carlo.py — Monte Carlo simulation backend for dice roll statistics.

Approximates dice roll probability distributions via random sampling, solving
the exponential blowup of the combinatorial engine for large dice pools (10+
dice). Simulates N independent trials and aggregates results into an
approximate Roll_DataFrame.

Exposes the same public API as dice_maths_combinatories.py so that
report_engine.py can swap backends transparently.

Internal representation:
    sample_matrix : np.ndarray, shape (N, D), dtype int16
        Each row is one trial. Each column is one die slot.
        Cell value = face index into that die's profile list.

    die_profiles : list[ProfileArrays]
        Length D. die_profiles[d] is the ProfileArrays dict for die slot d.
"""

import numpy as np
import pandas as pd

from drc_stat_engine.stats.profiles import (
    black_die_ship, black_die_squad,
    blue_die_ship, blue_die_squad,
    red_die_ship, red_die_squad,
)
from drc_stat_engine.stats.dice_models import validate_dice_pool, DicePool
from drc_stat_engine.stats.dice_maths_combinatories import _resolve_color_agnostic_result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_profile_arrays(profile):
    """
    Convert a die profile list of dicts into a ProfileArrays dict.

    Parameters
    ----------
    profile : list[dict]
        Each dict has keys: value, proba, damage, crit, acc, blank.

    Returns
    -------
    dict with keys:
        values  : list[str]       — face value strings, indexed by face index
        weights : np.ndarray      — shape (n_faces,), dtype float64, sampling weights
        damage  : np.ndarray      — shape (n_faces,), dtype int16
        crit    : np.ndarray      — shape (n_faces,), dtype int16
        acc     : np.ndarray      — shape (n_faces,), dtype int16
        blank   : np.ndarray      — shape (n_faces,), dtype int16
    """
    values  = [face["value"]  for face in profile]
    weights = np.array([face["proba"]  for face in profile], dtype=np.float64)
    damage  = np.array([face["damage"] for face in profile], dtype=np.int16)
    crit    = np.array([face["crit"]   for face in profile], dtype=np.int16)
    acc     = np.array([face["acc"]    for face in profile], dtype=np.int16)
    blank   = np.array([face["blank"]  for face in profile], dtype=np.int16)
    return {
        "values":  values,
        "weights": weights,
        "damage":  damage,
        "crit":    crit,
        "acc":     acc,
        "blank":   blank,
    }


def _samples_to_roll_df(matrix, die_profiles, type_str, N):
    """
    Convert a (N, D) sample matrix of face indices into a Roll_DataFrame.

    Parameters
    ----------
    matrix : np.ndarray, shape (N, D), dtype int16
        Each cell is a face index into the corresponding die's profile.
    die_profiles : list[dict]
        Length D. Each element is a ProfileArrays dict (from _build_profile_arrays).
    type_str : str
        "ship" or "squad" — not used for decoding but kept for API consistency.
    N : int
        Number of trials (rows in matrix).

    Returns
    -------
    pd.DataFrame with columns: value, proba, damage, crit, acc, blank
    """
    D = matrix.shape[1]

    # --- Decode face indices to value strings ---
    # Build a (N, D) object array of face value strings.
    str_matrix = np.empty((N, D), dtype=object)
    for d in range(D):
        face_values = np.array(die_profiles[d]["values"], dtype=object)
        str_matrix[:, d] = face_values[matrix[:, d]]

    # Sort each row lexicographically so value strings are canonical.
    str_matrix.sort(axis=1)

    # Join each row into a space-separated string.
    value_strings = np.array(
        [" ".join(row) for row in str_matrix],
        dtype=object,
    )

    # --- Compute per-row stat totals ---
    damage_total = np.zeros(N, dtype=np.int32)
    crit_total   = np.zeros(N, dtype=np.int32)
    acc_total    = np.zeros(N, dtype=np.int32)
    blank_total  = np.zeros(N, dtype=np.int32)

    for d in range(D):
        face_indices = matrix[:, d]
        damage_total += die_profiles[d]["damage"][face_indices].astype(np.int32)
        crit_total   += die_profiles[d]["crit"][face_indices].astype(np.int32)
        acc_total    += die_profiles[d]["acc"][face_indices].astype(np.int32)
        blank_total  += die_profiles[d]["blank"][face_indices].astype(np.int32)

    # --- Group by value string ---
    unique_values, inverse_indices, counts = np.unique(
        value_strings, return_inverse=True, return_counts=True
    )
    proba = counts / N

    # For each unique value string, take the stat totals from the first matching row.
    # All rows with the same value string have identical stat totals by construction.
    n_unique = len(unique_values)
    damage_agg = np.zeros(n_unique, dtype=np.int64)
    crit_agg   = np.zeros(n_unique, dtype=np.int64)
    acc_agg    = np.zeros(n_unique, dtype=np.int64)
    blank_agg  = np.zeros(n_unique, dtype=np.int64)

    # Use first-occurrence assignment: iterate unique indices once.
    first_seen = np.full(n_unique, -1, dtype=np.int64)
    for i in range(N):
        uid = inverse_indices[i]
        if first_seen[uid] == -1:
            first_seen[uid] = i
            damage_agg[uid] = damage_total[i]
            crit_agg[uid]   = crit_total[i]
            acc_agg[uid]    = acc_total[i]
            blank_agg[uid]  = blank_total[i]

    return pd.DataFrame({
        "value":  unique_values,
        "proba":  proba,
        "damage": damage_agg,
        "crit":   crit_agg,
        "acc":    acc_agg,
        "blank":  blank_agg,
    })


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def combine_dice(
    red_dice: int = 0,
    blue_dice: int = 0,
    black_dice: int = 0,
    type_str: str = "ship",
    *,
    sample_count: int = 10_000,
    seed=None,
) -> pd.DataFrame:
    """
    Simulate sample_count independent rolls of the given dice pool.

    Parameters
    ----------
    red_dice, blue_dice, black_dice : int
        Number of dice of each color.
    type_str : str
        "ship" or "squad".
    sample_count : int
        Number of Monte Carlo trials.
    seed : optional
        Seed for numpy random generator (makes output deterministic).

    Returns
    -------
    pd.DataFrame
        Roll_DataFrame with columns: value, proba, damage, crit, acc, blank.
        proba column sums to 1.0 within 1e-9.
    """
    # 1. Validate inputs
    validate_dice_pool(DicePool(red=red_dice, blue=blue_dice, black=black_dice, type=type_str))

    # 2. Build RNG
    rng = np.random.default_rng(seed)

    # 3. Select die profiles based on type_str
    if type_str == "ship":
        red_profile   = red_die_ship
        blue_profile  = blue_die_ship
        black_profile = black_die_ship
    else:  # "squad"
        red_profile   = red_die_squad
        blue_profile  = blue_die_squad
        black_profile = black_die_squad

    # 4. Build ProfileArrays for each die slot
    die_profiles_list = []
    for _ in range(red_dice):
        die_profiles_list.append(_build_profile_arrays(red_profile))
    for _ in range(blue_dice):
        die_profiles_list.append(_build_profile_arrays(blue_profile))
    for _ in range(black_dice):
        die_profiles_list.append(_build_profile_arrays(black_profile))

    D = red_dice + blue_dice + black_dice

    # 5. Build sample_matrix of shape (sample_count, D) dtype int16
    sample_matrix = np.empty((sample_count, D), dtype=np.int16)
    for d, profile_arrays in enumerate(die_profiles_list):
        weights = profile_arrays["weights"]
        n_faces = len(weights)
        sample_matrix[:, d] = rng.choice(n_faces, size=sample_count, p=weights)

    # 6. Convert to Roll_DataFrame
    roll_df = _samples_to_roll_df(sample_matrix, die_profiles_list, type_str, sample_count)

    # 7. Attach _mc_state
    roll_df.attrs["_mc_state"] = {
        "matrix":   sample_matrix,
        "profiles": die_profiles_list,
        "N":        sample_count,
        "rng":      rng,
    }

    # 8. Return
    return roll_df


# ---------------------------------------------------------------------------
# Pipeline operations
# ---------------------------------------------------------------------------

def reroll_dice(roll_df, results_to_reroll="blanks", reroll_count=1, type_str="ship"):
    """
    Re-sample up to reroll_count eligible dice per trial.
    Returns (rerolled_df, initial_roll_df).
    """
    if results_to_reroll == "blanks":
        results_to_reroll = ["B_blank", "R_blank"]
    if not results_to_reroll:
        return (roll_df, roll_df)

    state = roll_df.attrs["_mc_state"]
    matrix   = state["matrix"].copy()
    profiles = state["profiles"]
    N        = state["N"]
    rng      = state["rng"]
    D        = matrix.shape[1]

    # Build eligible_mask (N, D)
    eligible_mask = np.zeros((N, D), dtype=bool)
    for d in range(D):
        face_strs = np.array(profiles[d]["values"], dtype=object)[matrix[:, d]]
        eligible_mask[:, d] = np.isin(face_strs, results_to_reroll)

    # Cap per-row eligible count to reroll_count
    running = np.zeros(N, dtype=np.int32)
    for d in range(D):
        col_eligible = eligible_mask[:, d]
        over_limit = col_eligible & (running >= reroll_count)
        eligible_mask[over_limit, d] = False
        running += eligible_mask[:, d].astype(np.int32)

    # Resample eligible cells column-by-column
    for d in range(D):
        rows_to_resample = np.where(eligible_mask[:, d])[0]
        if len(rows_to_resample) == 0:
            continue
        n_faces = len(profiles[d]["weights"])
        new_faces = rng.choice(n_faces, size=len(rows_to_resample), p=profiles[d]["weights"])
        matrix[rows_to_resample, d] = new_faces

    rerolled_df = _samples_to_roll_df(matrix, profiles, type_str, N)
    rerolled_df.attrs["_mc_state"] = {
        "matrix":   matrix,
        "profiles": profiles,
        "N":        N,
        "rng":      rng,
    }
    return (rerolled_df, roll_df)


def cancel_dice(roll_df, results_to_cancel="blanks", cancel_count=1, type_str="ship"):
    """
    Remove up to cancel_count eligible dice per trial.
    Returns (cancelled_df, kept_df).
    """
    if results_to_cancel == "blanks":
        results_to_cancel = ["B_blank", "R_blank"]

    state = roll_df.attrs["_mc_state"]
    matrix   = state["matrix"]
    profiles = state["profiles"]
    N        = state["N"]
    rng      = state["rng"]
    D        = matrix.shape[1]

    # Build eligible_mask (N, D)
    eligible_mask = np.zeros((N, D), dtype=bool)
    for d in range(D):
        face_strs = np.array(profiles[d]["values"], dtype=object)[matrix[:, d]]
        eligible_mask[:, d] = np.isin(face_strs, results_to_cancel)

    # Cap per-row eligible count to cancel_count
    running = np.zeros(N, dtype=np.int32)
    for d in range(D):
        col_eligible = eligible_mask[:, d]
        over_limit = col_eligible & (running >= cancel_count)
        eligible_mask[over_limit, d] = False
        running += eligible_mask[:, d].astype(np.int32)

    any_eligible = eligible_mask.any(axis=1)  # shape (N,)

    if any_eligible.sum() == 0:
        empty_df = roll_df.iloc[0:0].copy()
        return (empty_df, roll_df)

    cancelled_rows = np.where(any_eligible)[0]
    kept_rows      = np.where(~any_eligible)[0]

    # --- kept_df: trials with no eligible dice ---
    if len(kept_rows) > 0:
        kept_matrix = matrix[kept_rows]
        kept_df = _samples_to_roll_df(kept_matrix, profiles, type_str, len(kept_rows))
        # Normalize proba by total N so probabilities sum correctly when merged
        kept_df["proba"] = kept_df["proba"] * len(kept_rows) / N
        kept_df.attrs["_mc_state"] = {
            "matrix":   kept_matrix.copy(),
            "profiles": profiles,
            "N":        N,
            "rng":      rng,
        }
    else:
        kept_df = roll_df.iloc[0:0].copy()

    # --- cancelled_df: trials where eligible dice are removed ---
    n_cancelled = len(cancelled_rows)
    c_matrix   = matrix[cancelled_rows].copy()       # (n_cancelled, D)
    c_eligible = eligible_mask[cancelled_rows]        # (n_cancelled, D)

    # Compute per-trial stats for all dice, then subtract cancelled dice
    damage_total = np.zeros(n_cancelled, dtype=np.int32)
    crit_total   = np.zeros(n_cancelled, dtype=np.int32)
    acc_total    = np.zeros(n_cancelled, dtype=np.int32)
    blank_total  = np.zeros(n_cancelled, dtype=np.int32)
    for d in range(D):
        damage_total += profiles[d]["damage"][c_matrix[:, d]].astype(np.int32)
        crit_total   += profiles[d]["crit"][c_matrix[:, d]].astype(np.int32)
        acc_total    += profiles[d]["acc"][c_matrix[:, d]].astype(np.int32)
        blank_total  += profiles[d]["blank"][c_matrix[:, d]].astype(np.int32)

    for d in range(D):
        cancelled_col = c_eligible[:, d]
        if cancelled_col.any():
            damage_total -= np.where(cancelled_col, profiles[d]["damage"][c_matrix[:, d]].astype(np.int32), 0)
            crit_total   -= np.where(cancelled_col, profiles[d]["crit"][c_matrix[:, d]].astype(np.int32), 0)
            acc_total    -= np.where(cancelled_col, profiles[d]["acc"][c_matrix[:, d]].astype(np.int32), 0)
            blank_total  -= np.where(cancelled_col, profiles[d]["blank"][c_matrix[:, d]].astype(np.int32), 0)

    # Build remaining value strings (exclude cancelled columns per trial)
    str_matrix = np.empty((n_cancelled, D), dtype=object)
    for d in range(D):
        face_values = np.array(profiles[d]["values"], dtype=object)
        str_matrix[:, d] = face_values[c_matrix[:, d]]

    remaining_strs = np.array([
        " ".join(sorted(str_matrix[i, d] for d in range(D) if not c_eligible[i, d]))
        if any(not c_eligible[i, d] for d in range(D)) else ""
        for i in range(n_cancelled)
    ], dtype=object)

    unique_vals, inv_idx, counts = np.unique(remaining_strs, return_inverse=True, return_counts=True)
    proba = counts / N  # normalize by total N

    n_unique = len(unique_vals)
    dmg_agg   = np.zeros(n_unique, dtype=np.int64)
    crit_agg  = np.zeros(n_unique, dtype=np.int64)
    acc_agg   = np.zeros(n_unique, dtype=np.int64)
    blank_agg = np.zeros(n_unique, dtype=np.int64)
    first_seen = np.full(n_unique, -1, dtype=np.int64)
    for i in range(n_cancelled):
        uid = inv_idx[i]
        if first_seen[uid] == -1:
            first_seen[uid] = i
            dmg_agg[uid]   = damage_total[i]
            crit_agg[uid]  = crit_total[i]
            acc_agg[uid]   = acc_total[i]
            blank_agg[uid] = blank_total[i]

    cancelled_df = pd.DataFrame({
        "value":  unique_vals,
        "proba":  proba,
        "damage": dmg_agg,
        "crit":   crit_agg,
        "acc":    acc_agg,
        "blank":  blank_agg,
    })

    return (cancelled_df, kept_df)


def add_dice_to_roll(roll_df, red=0, blue=0, black=0, type_str="ship"):
    """
    Sample new dice and merge them into the existing sample matrix.
    Returns a Roll_DataFrame.
    """
    if red == 0 and blue == 0 and black == 0:
        return roll_df

    state = roll_df.attrs["_mc_state"]
    matrix   = state["matrix"]
    profiles = state["profiles"]
    N        = state["N"]
    rng      = state["rng"]

    # Select profiles for new dice
    if type_str == "ship":
        red_profile   = red_die_ship
        blue_profile  = blue_die_ship
        black_profile = black_die_ship
    else:
        red_profile   = red_die_squad
        blue_profile  = blue_die_squad
        black_profile = black_die_squad

    # Build ProfileArrays for new dice
    new_die_profiles = []
    for _ in range(red):
        new_die_profiles.append(_build_profile_arrays(red_profile))
    for _ in range(blue):
        new_die_profiles.append(_build_profile_arrays(blue_profile))
    for _ in range(black):
        new_die_profiles.append(_build_profile_arrays(black_profile))

    new_D = red + blue + black
    new_cols = np.empty((N, new_D), dtype=np.int16)
    for i, pa in enumerate(new_die_profiles):
        n_faces = len(pa["weights"])
        new_cols[:, i] = rng.choice(n_faces, size=N, p=pa["weights"])

    new_matrix   = np.hstack([matrix, new_cols])
    new_profiles = profiles + new_die_profiles

    result_df = _samples_to_roll_df(new_matrix, new_profiles, type_str, N)
    result_df.attrs["_mc_state"] = {
        "matrix":   new_matrix,
        "profiles": new_profiles,
        "N":        N,
        "rng":      rng,
    }
    return result_df


def change_die_face(roll_df, source_results, target_result, type_str="ship"):
    """
    For each trial, replace the highest-priority source face with target_result.
    Returns a Roll_DataFrame.
    """
    if not source_results:
        return roll_df

    if "_" not in target_result:
        target_result = _resolve_color_agnostic_result(target_result, type_str)

    state = roll_df.attrs["_mc_state"]
    matrix   = state["matrix"].copy()
    profiles = state["profiles"]
    N        = state["N"]
    rng      = state["rng"]
    D        = matrix.shape[1]

    changed = np.zeros(N, dtype=bool)

    for source in source_results:
        if changed.all():
            break
        for d in range(D):
            if source not in profiles[d]["values"]:
                continue
            source_idx = profiles[d]["values"].index(source)
            if target_result not in profiles[d]["values"]:
                continue
            target_idx = profiles[d]["values"].index(target_result)

            eligible = (matrix[:, d] == source_idx) & ~changed
            if not eligible.any():
                continue
            matrix[:, d] = np.where(eligible, target_idx, matrix[:, d])
            changed |= eligible

    result_df = _samples_to_roll_df(matrix, profiles, type_str, N)
    result_df.attrs["_mc_state"] = {
        "matrix":   matrix,
        "profiles": profiles,
        "N":        N,
        "rng":      rng,
    }
    return result_df
