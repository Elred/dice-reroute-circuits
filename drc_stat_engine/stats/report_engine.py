"""
report_engine.py — Attack effect pipeline executor, statistics, and report generation.

Orchestrates the full report workflow:
  1. Validate inputs (via dice_models)
  2. Build the initial roll distribution (via dice_maths_combinatories)
  3. Resolve strategy pipelines (via strategies)
  4. Execute the pipeline and compute statistics
  5. Format the output as a human-readable string
"""

from typing import List, Tuple

import numpy as np
import pandas as pd

from drc_stat_engine.stats.dice_maths_combinatories import (
    add_dice_to_roll,
    add_set_die_to_roll,
    cancel_dice,
    combine_dice,
    conditional_add_partition,
    color_in_pool_add,
    reroll_dice,
    change_die_face,
)
import drc_stat_engine.stats.dice_monte_carlo as dice_monte_carlo
import drc_stat_engine.stats.dice_maths_combinatories as dice_maths_combinatories
from drc_stat_engine.stats.dice_models import (
    AttackEffect,
    DefenseEffect,
    DicePool,
    validate_attack_effect_pipeline,
    validate_defense_pipeline,
    validate_dice_pool,
)
from drc_stat_engine.stats.strategies import (
    PRIORITY_DEPENDENT_OPS,
    STRATEGY_PRIORITY_LISTS,
    build_defense_pipeline,
    build_strategy_pipeline,
    DEFENSE_PRIORITY_LISTS,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REROLL_COST_LIMIT = 25

# ---------------------------------------------------------------------------
# Backend selector
# ---------------------------------------------------------------------------

def _select_backend(pool: DicePool, pipeline: List[AttackEffect], backend: str):
    """
    Return the backend module to use for dice operations.

    - "auto": combinatorial for total_dice <= 8, MC for total_dice > 8
              total_dice = base pool + all add_dice ops in the pipeline
    - "combinatorial": always use combinatorial engine
    - "montecarlo": always use MC engine

    Raises ValueError for unknown backend strings.
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
    """
    if backend == "auto":
        added = 0
        for op in pipeline:
            if op.type == "add_set_die":
                added += 1
            elif op.type == "add_dice":
                if op.color_in_pool:
                    added += 1
                else:
                    dice = op.dice_to_add or {}
                    added += dice.get("red", 0) + dice.get("blue", 0) + dice.get("black", 0)
        total_dice = pool.red + pool.blue + pool.black + added

        if total_dice > 8:
            return dice_monte_carlo

        # Reroll cost estimation: route to MC if the largest reroll op
        # would cause an expensive combine_two cross-join.
        max_reroll_count = 0
        for op in pipeline:
            if op.type == "reroll":
                effective = min(op.count, total_dice)
                max_reroll_count = max(max_reroll_count, effective)

        if max_reroll_count > 0:
            reroll_cost = total_dice * max_reroll_count
            if reroll_cost > REROLL_COST_LIMIT:
                return dice_monte_carlo

        return dice_maths_combinatories
    elif backend == "combinatorial":
        return dice_maths_combinatories
    elif backend == "montecarlo":
        return dice_monte_carlo
    else:
        raise ValueError(
            f"Unknown backend '{backend}'. Must be 'auto', 'combinatorial', or 'montecarlo'."
        )


# ---------------------------------------------------------------------------
# Pipeline executor
# ---------------------------------------------------------------------------

PROB_TOLERANCE = 1e-9


def apply_attack_effect(roll_df, attack_effect: AttackEffect, type_str: str, backend_mod=None):
    """
    Dispatch a single AttackEffect to the appropriate dice_maths function.

    - reroll   → reroll_dice
    - cancel   → cancel_dice  (merges cancelled + kept rows into a full distribution)
    - add_dice → add_dice_to_roll
    - change_die → change_die_face

    backend_mod: the backend module to use (defaults to dice_maths_combinatories).
    """
    if backend_mod is None:
        backend_mod = dice_maths_combinatories

    if attack_effect.type == "reroll":
        result_df, _ = backend_mod.reroll_dice(
            roll_df,
            results_to_reroll=attack_effect.priority_list,
            reroll_count=attack_effect.count,
            type_str=type_str,
        )
        return result_df

    elif attack_effect.type == "cancel":
        # cancel_dice returns (cancelled_df, kept_df).
        # The full post-cancel distribution requires both parts merged.
        cancelled_df, kept_df = backend_mod.cancel_dice(
            roll_df,
            results_to_cancel=attack_effect.priority_list,
            cancel_count=attack_effect.count,
            type_str=type_str,
        )
        merged = pd.concat([cancelled_df, kept_df]).groupby("value", as_index=False).agg({
            "proba":  "sum",
            "damage": "first",
            "crit":   "first",
            "acc":    "first",
            "blank":  "first",
        })
        # Preserve _mc_state from kept_df (MC backend)
        if hasattr(kept_df, 'attrs') and "_mc_state" in kept_df.attrs:
            merged.attrs["_mc_state"] = kept_df.attrs["_mc_state"]
        return merged

    elif attack_effect.type == "add_dice":
        is_mc = backend_mod is dice_monte_carlo
        fc = attack_effect.face_condition
        cip = attack_effect.color_in_pool

        if fc and cip:
            # face_condition + color_in_pool: partition by face first, then color within match
            if is_mc:
                # MC: conditional add with color_in_pool
                # Evaluate face condition per trial, apply color_in_pool only to matching trials
                state = roll_df.attrs["_mc_state"]
                matrix = state["matrix"]
                profiles = state["profiles"]
                N = state["N"]
                rng = state["rng"]

                match_mask = dice_monte_carlo._evaluate_face_condition_per_trial(
                    matrix, profiles, fc
                )

                if not match_mask.any():
                    return roll_df

                # Build a sub-roll_df for matching trials only
                matching_matrix = matrix[match_mask]
                matching_N = matching_matrix.shape[0]
                matching_df = dice_monte_carlo._samples_to_roll_df(
                    matching_matrix, profiles, type_str, matching_N
                )
                matching_df.attrs["_mc_state"] = {
                    "matrix": matching_matrix,
                    "profiles": profiles,
                    "N": matching_N,
                    "rng": rng,
                }

                # Apply color_in_pool to matching trials
                modified_matching_df = dice_monte_carlo.color_in_pool_add_mc(
                    matching_df, attack_effect.color_priority, type_str=type_str
                )

                # Get the updated matrix from modified matching trials
                mod_state = modified_matching_df.attrs["_mc_state"]
                mod_matrix = mod_state["matrix"]
                mod_profiles = mod_state["profiles"]
                new_D = mod_matrix.shape[1]

                # Build full matrix: non-matching trials get sentinel columns for the new die slots
                old_D = matrix.shape[1]
                extra_cols = new_D - old_D
                non_match_matrix = matrix[~match_mask]
                if extra_cols > 0:
                    sentinel_pad = np.full(
                        (non_match_matrix.shape[0], extra_cols),
                        dice_monte_carlo.SENTINEL, dtype=np.int16
                    )
                    non_match_matrix = np.hstack([non_match_matrix, sentinel_pad])

                # Reassemble full matrix preserving original trial order
                full_matrix = np.empty((N, new_D), dtype=np.int16)
                full_matrix[match_mask] = mod_matrix
                full_matrix[~match_mask] = non_match_matrix

                result_df = dice_monte_carlo._samples_to_roll_df(
                    full_matrix, mod_profiles, type_str, N
                )
                result_df.attrs["_mc_state"] = {
                    "matrix": full_matrix,
                    "profiles": mod_profiles,
                    "N": N,
                    "rng": rng,
                }
                return result_df
            else:
                # Combinatorial: partition by face_condition, then color_in_pool on matching
                return conditional_add_partition(
                    roll_df, fc,
                    color_in_pool_add,
                    color_priority=attack_effect.color_priority,
                    type_str=type_str,
                )

        elif fc:
            # face_condition only (no color_in_pool)
            dice = attack_effect.dice_to_add or {}
            if is_mc:
                return dice_monte_carlo.conditional_add_dice_mc(
                    roll_df, fc,
                    red=dice.get("red", 0),
                    blue=dice.get("blue", 0),
                    black=dice.get("black", 0),
                    type_str=type_str,
                )
            else:
                return conditional_add_partition(
                    roll_df, fc,
                    add_dice_to_roll,
                    red=dice.get("red", 0),
                    blue=dice.get("blue", 0),
                    black=dice.get("black", 0),
                    type_str=type_str,
                )

        elif cip:
            # color_in_pool only (no face_condition)
            if is_mc:
                return dice_monte_carlo.color_in_pool_add_mc(
                    roll_df, attack_effect.color_priority, type_str=type_str,
                )
            else:
                return color_in_pool_add(
                    roll_df, attack_effect.color_priority, type_str=type_str,
                )

        else:
            # Plain add_dice (existing behavior)
            dice = attack_effect.dice_to_add or {}
            return backend_mod.add_dice_to_roll(
                roll_df,
                red=dice.get("red", 0),
                blue=dice.get("blue", 0),
                black=dice.get("black", 0),
                type_str=type_str,
            )

    elif attack_effect.type == "add_set_die":
        is_mc = backend_mod is dice_monte_carlo
        fc = attack_effect.face_condition

        if fc:
            # Conditional add_set_die
            if is_mc:
                return dice_monte_carlo.conditional_add_set_die_mc(
                    roll_df, fc,
                    target_result=attack_effect.target_result,
                    type_str=type_str,
                )
            else:
                return conditional_add_partition(
                    roll_df, fc,
                    add_set_die_to_roll,
                    target_result=attack_effect.target_result,
                    type_str=type_str,
                )
        else:
            # Unconditional add_set_die
            return backend_mod.add_set_die_to_roll(
                roll_df,
                target_result=attack_effect.target_result,
                type_str=type_str,
            )

    elif attack_effect.type == "change_die":
        if not attack_effect.priority_list:
            return roll_df
        if attack_effect.target_result is None:
            raise ValueError(
                "AttackEffect 'change_die' requires a non-None 'target_result'."
            )
        return backend_mod.change_die_face(
            roll_df,
            source_results=attack_effect.priority_list,
            target_result=attack_effect.target_result,
            type_str=type_str,
        )

    elif attack_effect.type == "reroll_all":
        result_df, _ = backend_mod.reroll_all_dice(
            roll_df,
            condition=attack_effect.condition,
            type_str=type_str,
        )
        return result_df

    else:
        raise ValueError(f"Unknown attack effect type '{attack_effect.type}'.")


def _check_probability_integrity(roll_df, attack_effect: AttackEffect, op_index: int) -> None:
    """
    Assert that probabilities in roll_df sum to 1.0 within PROB_TOLERANCE.
    Raises ValueError identifying the offending attack effect if the check fails.
    Requirements: 8.1, 8.2
    """
    total = roll_df["proba"].sum()
    if abs(total - 1.0) > PROB_TOLERANCE:
        raise ValueError(
            f"Probability integrity check failed after attack effect {op_index} "
            f"(type='{attack_effect.type}'): probabilities sum to {total:.15f}, "
            f"expected 1.0 (tolerance {PROB_TOLERANCE})."
        )


def run_pipeline(roll_df, pipeline: List[AttackEffect], type_str: str, backend_mod=None):
    """
    Apply all attack effects in the pipeline sequentially, checking probability
    integrity after each step.

    Returns roll_df unchanged if the pipeline is empty.
    Requirements: 2.1, 2.4, 8.1
    """
    if not pipeline:
        return roll_df

    for idx, attack_effect in enumerate(pipeline):
        roll_df = apply_attack_effect(roll_df, attack_effect, type_str, backend_mod=backend_mod)
        _check_probability_integrity(roll_df, attack_effect, idx)

    return roll_df


# ---------------------------------------------------------------------------
# Cumulative probability computations
# ---------------------------------------------------------------------------

def cumulative_damage(roll_df) -> List[Tuple[int, float]]:
    """
    Return [(x, P(damage >= x)) for x in range(0, max_damage + 1)].
    All integer thresholds are included even if probability is 0.
    Requirements: 3.1, 3.2, 3.3
    """
    max_dmg = int(roll_df["damage"].max())
    return [
        (x, float(roll_df.loc[roll_df["damage"] >= x, "proba"].sum()))
        for x in range(0, max_dmg + 1)
    ]


def cumulative_accuracy(roll_df) -> List[Tuple[int, float]]:
    """
    Return [(x, P(acc >= x)) for x in range(0, max_acc + 1)].
    All integer thresholds are included even if probability is 0.
    Requirements: 4.1, 4.2, 4.3
    """
    max_acc = int(roll_df["acc"].max())
    return [
        (x, float(roll_df.loc[roll_df["acc"] >= x, "proba"].sum()))
        for x in range(0, max_acc + 1)
    ]


def crit_probability(roll_df) -> float:
    """
    Return P(crit >= 1).
    Requirements: 5.1, 5.2
    """
    return float(roll_df.loc[roll_df["crit"] >= 1, "proba"].sum())


def average_damage(roll_df) -> float:
    """Return E[damage] = sum(damage * proba) across all outcomes."""
    return float((roll_df["damage"] * roll_df["proba"]).sum())


def joint_cumulative_damage_accuracy(roll_df: pd.DataFrame) -> dict:
    """
    Compute the joint cumulative probability table P(damage >= X AND accuracy >= Y).

    Uses vectorized numpy broadcasting to avoid per-cell Python iteration.

    Parameters
    ----------
    roll_df : pd.DataFrame
        Roll distribution with columns: value, proba, damage, crit, acc, blank.
        Probabilities must sum to 1.0.

    Returns
    -------
    dict with keys:
        - "damage_thresholds": list[int] — row labels [0, 1, ..., max_damage]
        - "accuracy_thresholds": list[int] — column labels [0, 1, ..., max_accuracy]
        - "matrix": list[list[float]] — matrix[i][j] = P(damage >= i AND acc >= j)

    Requirements: 1.1, 1.2, 1.3, 1.4, 1.6, 3.1, 3.2, 3.3, 4.1
    """
    max_damage = int(roll_df["damage"].max())
    max_acc = int(roll_df["acc"].max())

    damage_thresholds = list(range(0, max_damage + 1))
    accuracy_thresholds = list(range(0, max_acc + 1))

    damage_vals = roll_df["damage"].values
    acc_vals = roll_df["acc"].values
    proba_vals = roll_df["proba"].values

    # Boolean masks via broadcasting: shape (D, N) and (A, N)
    dmg_mask = damage_vals[np.newaxis, :] >= np.array(damage_thresholds)[:, np.newaxis]
    acc_mask = acc_vals[np.newaxis, :] >= np.array(accuracy_thresholds)[:, np.newaxis]

    # Joint probability matrix: shape (D, A)
    # matrix[i][j] = sum of proba where damage >= i AND acc >= j
    matrix = dmg_mask.astype(float) @ (proba_vals[:, np.newaxis] * acc_mask.T.astype(float))

    return {
        "damage_thresholds": damage_thresholds,
        "accuracy_thresholds": accuracy_thresholds,
        "matrix": matrix.tolist(),
    }


# ---------------------------------------------------------------------------
# Defense pipeline functions
# Requirements: 4.1-5.5, 6.1-6.4, 7.2-7.3, 14.1-14.4
# ---------------------------------------------------------------------------


def sort_defense_pipeline(pipeline: List[DefenseEffect]) -> List[DefenseEffect]:
    """Sort defense effects into fixed execution order:
    1. defense_reroll and defense_cancel (preserving user order within group)
    2. reduce_damage (preserving user order within group)
    3. divide_damage (preserving user order within group)
    Requirements: 6.1, 6.2, 6.3, 6.4
    """
    GROUP_ORDER = {"defense_reroll": 0, "defense_cancel": 0, "divide_damage": 1, "reduce_damage": 2}
    return sorted(pipeline, key=lambda e: GROUP_ORDER.get(e.type, 99))


def reduce_damage_df(roll_df: pd.DataFrame, amount: int) -> pd.DataFrame:
    """Subtract amount from damage column, floor at 0. Preserves proba, crit, acc, blank.
    Groups by value to aggregate probabilities for rows that now share the same damage.
    Requirements: 4.1, 4.2, 4.3, 4.4
    """
    df = roll_df.copy()
    df["damage"] = (df["damage"] - amount).clip(lower=0)
    # Group by all non-proba columns to aggregate probabilities
    group_cols = [c for c in df.columns if c != "proba"]
    df = df.groupby(group_cols, as_index=False)["proba"].sum()
    return df


def divide_damage_df(roll_df: pd.DataFrame) -> pd.DataFrame:
    """Replace damage with ceil(damage / 2), i.e. (damage + 1) // 2.
    Zero damage stays zero. Preserves proba, crit, acc, blank.
    Groups by value to aggregate probabilities for rows that now share the same damage.
    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
    """
    df = roll_df.copy()
    df["damage"] = (df["damage"] + 1) // 2
    group_cols = [c for c in df.columns if c != "proba"]
    df = df.groupby(group_cols, as_index=False)["proba"].sum()
    return df


def compute_variant_stats(roll_df: pd.DataFrame) -> dict:
    """Extract damage, accuracy, crit, avg_damage, damage_zero, acc_zero, joint_cumulative from a roll_df.
    Reuses existing cumulative_damage, cumulative_accuracy, crit_probability, average_damage,
    joint_cumulative_damage_accuracy.
    Requirements: 2.1, 2.2, 2.3, 7.2, 7.3, 8.2, 8.3
    """
    return {
        "damage": cumulative_damage(roll_df),
        "damage_zero": float(roll_df.loc[roll_df["damage"] == 0, "proba"].sum()),
        "accuracy": cumulative_accuracy(roll_df),
        "acc_zero": float(roll_df.loc[roll_df["acc"] == 0, "proba"].sum()),
        "crit": crit_probability(roll_df),
        "avg_damage": average_damage(roll_df),
        "joint_cumulative": joint_cumulative_damage_accuracy(roll_df),
    }


def run_defense_pipeline(
    roll_df: pd.DataFrame,
    defense_pipeline: List[DefenseEffect],
    type_str: str,
    backend_mod=None,
) -> pd.DataFrame:
    """Execute the full sorted defense pipeline:
    1. Sort defense effects via sort_defense_pipeline
    2. Build resolved defense pipeline via build_defense_pipeline
    3. Run reroll/cancel effects by converting to AttackEffect equivalents and using run_pipeline
    4. Apply each reduce_damage effect sequentially via reduce_damage_df
    5. Apply each divide_damage effect sequentially via divide_damage_df
    Returns the modified roll_df.
    Requirements: 2.5, 3.4, 6.1, 14.1, 14.2, 14.3, 14.4
    """
    sorted_pipeline = sort_defense_pipeline(defense_pipeline)
    resolved = build_defense_pipeline(sorted_pipeline, type_str)

    # Separate into groups
    reroll_cancel = [e for e in resolved if e.type in ("defense_reroll", "defense_cancel")]
    reduce_effects = [e for e in resolved if e.type == "reduce_damage"]
    divide_effects = [e for e in resolved if e.type == "divide_damage"]

    # Convert defense reroll/cancel to AttackEffect equivalents and run via existing pipeline
    if reroll_cancel:
        attack_equivalents = []
        for e in reroll_cancel:
            if e.type == "defense_reroll":
                attack_equivalents.append(AttackEffect(
                    type="reroll",
                    count=e.count,
                    applicable_results=list(e.applicable_results),
                    priority_list=list(e.priority_list),
                ))
            elif e.type == "defense_cancel":
                attack_equivalents.append(AttackEffect(
                    type="cancel",
                    count=e.count,
                    applicable_results=list(e.applicable_results),
                    priority_list=list(e.priority_list),
                ))
        roll_df = run_pipeline(roll_df, attack_equivalents, type_str, backend_mod=backend_mod)

    # Apply divide_damage effects (halve first — better for defender)
    for e in divide_effects:
        roll_df = divide_damage_df(roll_df)

    # Apply reduce_damage effects
    for e in reduce_effects:
        roll_df = reduce_damage_df(roll_df, e.amount)

    return roll_df


# ---------------------------------------------------------------------------
# Report generator
# Requirements: 6.1, 6.5, 6.6
# ---------------------------------------------------------------------------

def generate_report(
    dice_pool: DicePool,
    pipeline: List[AttackEffect],
    strategies: List[str] = None,
    backend: str = "auto",
    sample_count: int = 10_000,
    seed=None,
    defense_pipeline: List[DefenseEffect] = None,
) -> List[dict]:
    """
    Orchestrate all report variants.

    - Validates pool and pipeline.
    - Selects the backend (combinatorial or MC) via _select_backend.
    - Builds the initial roll_df via backend_mod.combine_dice.
    - Runs once per strategy, labeling each variant.
    - Defaults to ["max_damage"] if no strategies provided.
    - When defense_pipeline is provided, computes pre-defense and post-defense stats.

    Parameters
    ----------
    backend : str
        "auto" (default) — combinatorial for pool_size <= 8, MC for pool_size > 8.
        "combinatorial" — always use the combinatorial engine.
        "montecarlo" — always use the MC engine.
    sample_count : int
        Number of Monte Carlo trials (only used when MC backend is selected).
    seed : optional
        Seed for the MC engine's RNG (only used when MC backend is selected).
    defense_pipeline : List[DefenseEffect], optional
        Defense effects to apply after the attack pipeline.

    Returns a list of variant dicts:
        {"label": str, "damage": [...], "accuracy": [...], "crit": float, ...}
    Requirements: 3.3, 3.6, 4.1, 6.1, 6.5, 6.6, 7.1, 7.2, 7.3, 8.1, 8.2, 8.3, 8.4
    """
    if strategies is None:
        strategies = ["max_damage"]

    validate_dice_pool(dice_pool)
    validate_attack_effect_pipeline(pipeline, dice_pool)

    if defense_pipeline:
        validate_defense_pipeline(defense_pipeline)

    backend_mod = _select_backend(dice_pool, pipeline, backend)
    engine_type = "monte_carlo" if backend_mod is dice_monte_carlo else "combinatories"

    if backend_mod is dice_monte_carlo:
        roll_df = backend_mod.combine_dice(
            dice_pool.red, dice_pool.blue, dice_pool.black, dice_pool.type,
            sample_count=sample_count, seed=seed,
        )
    else:
        roll_df = backend_mod.combine_dice(dice_pool.red, dice_pool.blue, dice_pool.black, dice_pool.type)

    variants = []
    for strategy in strategies:
        if strategy not in STRATEGY_PRIORITY_LISTS[dice_pool.type]:
            raise ValueError(
                f"Unknown strategy '{strategy}' for type '{dice_pool.type}'. "
                f"Valid strategies: {sorted(STRATEGY_PRIORITY_LISTS[dice_pool.type])}."
            )
        strategy_pipeline = build_strategy_pipeline(pipeline, strategy, dice_pool.type)
        roll_copy = roll_df.copy()
        roll_copy.attrs = dict(roll_df.attrs)
        final_df = run_pipeline(roll_copy, strategy_pipeline, dice_pool.type, backend_mod=backend_mod)

        # Collect the resolved priority_list from the first priority-dependent op (if any)
        priority_list = next(
            (op.priority_list for op in strategy_pipeline if op.type in PRIORITY_DEPENDENT_OPS),
            STRATEGY_PRIORITY_LISTS[dice_pool.type][strategy]["reroll"],
        )

        if defense_pipeline:
            pre_defense_stats = compute_variant_stats(final_df)
            defense_copy = final_df.copy()
            defense_copy.attrs = dict(final_df.attrs)
            defense_df = run_defense_pipeline(
                defense_copy, defense_pipeline, dice_pool.type, backend_mod=backend_mod,
            )
            post_defense_stats = compute_variant_stats(defense_df)

            variants.append({
                "label":      strategy,
                "pre_defense": pre_defense_stats,
                "post_defense": post_defense_stats,
                "priority_list": priority_list,
                "engine_type": engine_type,
            })
        else:
            variants.append({
                "label":      strategy,
                "damage":     cumulative_damage(final_df),
                "damage_zero": float(final_df.loc[final_df["damage"] == 0, "proba"].sum()),
                "accuracy":   cumulative_accuracy(final_df),
                "acc_zero":   float(final_df.loc[final_df["acc"] == 0, "proba"].sum()),
                "crit":       crit_probability(final_df),
                "avg_damage": average_damage(final_df),
                "joint_cumulative": joint_cumulative_damage_accuracy(final_df),
                "priority_list": priority_list,
                "engine_type": engine_type,
            })
    return variants


# ---------------------------------------------------------------------------
# Report formatter
# Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
# ---------------------------------------------------------------------------

def _format_pipeline(pipeline: List[AttackEffect]) -> str:
    """Format the attack effect pipeline as a human-readable string."""
    if not pipeline:
        return "(none)"
    parts = []
    for op in pipeline:
        if op.type in ("reroll", "cancel"):
            faces = ", ".join(op.applicable_results)
            parts.append(f"{op.type} x{op.count} [{faces}]")
        elif op.type == "add_dice":
            dice = op.dice_to_add or {}
            r, u, b = dice.get("red", 0), dice.get("blue", 0), dice.get("black", 0)
            desc = f"add_dice [{r}R {u}U {b}B]"
            if op.face_condition:
                desc += f" if {op.face_condition} present"
            if op.color_in_pool:
                desc += f" color_in_pool [{op.color_priority}]"
            parts.append(desc)
        elif op.type == "add_set_die":
            desc = f"add_set_die [{op.target_result}]"
            if op.face_condition:
                desc += f" if {op.face_condition} present"
            parts.append(desc)
        elif op.type == "reroll_all":
            c = op.condition
            parts.append(f"reroll_all [condition: {c.attribute} {c.operator} {c.threshold}]")
        else:
            parts.append(op.type)
    return " | ".join(parts)


def format_report(
    dice_pool: DicePool,
    pipeline: List[AttackEffect],
    variants: List[dict],
) -> str:
    """
    Produce a formatted text report string (does not print directly).

    Header shows dice pool composition and applied pipeline.
    Each variant contains cumulative damage/accuracy tables and crit probability.
    Multiple variants are separated and labeled; single variant still shows its label.

    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
    """
    lines = []

    # Header — req 7.2, 7.7
    lines.append(
        f"Dice Pool: {dice_pool.red}R {dice_pool.blue}U {dice_pool.black}B ({dice_pool.type})"
    )
    lines.append(f"Pipeline:  {_format_pipeline(pipeline)}")

    has_multiple = len(variants) > 1

    for i, variant in enumerate(variants):
        lines.append("")

        # Strategy label — req 7.6
        if variant.get("label"):
            lines.append(f"=== Strategy: {variant['label']} ===")
            lines.append("")

        # Priority list — faces ordered from lowest to highest value
        if variant.get("priority_list"):
            lines.append(f"Priority List: {' > '.join(variant['priority_list'])}")
            lines.append("")

        # Cumulative damage table — req 7.3
        lines.append("Cumulative Damage:")
        for threshold, prob in variant["damage"]:
            lines.append(f"  >= {threshold}:  {prob * 100:.2f}%")

        lines.append("")

        # Cumulative accuracy table — req 7.4
        lines.append("Cumulative Accuracy:")
        for threshold, prob in variant["accuracy"]:
            lines.append(f"  >= {threshold}:  {prob * 100:.2f}%")

        lines.append("")

        # Crit probability — req 7.5
        lines.append(f"Crit Probability: {variant['crit'] * 100:.2f}%")

        # Average damage
        if "avg_damage" in variant:
            lines.append(f"Average Damage:   {variant['avg_damage']:.2f}")

        # Separator between variants — req 7.6
        if has_multiple and i < len(variants) - 1:
            lines.append("")
            lines.append("=" * 30)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scenario runner (kept for direct module execution)
# ---------------------------------------------------------------------------

def main():
    """
    Sample scenario: 1 Blue ship die + add 1 Blue, max_damage strategy.
    """
    pool = DicePool(red=0, blue=1, black=0, type="ship")
    pipeline = [
        AttackEffect(type="add_dice", dice_to_add={"red": 0, "blue": 1, "black": 0}),
    ]
    strategies = ["max_damage"]

    variants = generate_report(pool, pipeline, strategies)
    output = format_report(pool, pipeline, variants)
    print(output)


if __name__ == "__main__":
    main()
