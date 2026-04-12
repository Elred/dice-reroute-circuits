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

import pandas as pd

from drc_stat_engine.stats.dice_maths_combinatories import (
    add_dice_to_roll,
    cancel_dice,
    combine_dice,
    reroll_dice,
    change_die_face,
)
import drc_stat_engine.stats.dice_monte_carlo as dice_monte_carlo
import drc_stat_engine.stats.dice_maths_combinatories as dice_maths_combinatories
from drc_stat_engine.stats.dice_models import (
    AttackEffect,
    DicePool,
    validate_attack_effect_pipeline,
    validate_dice_pool,
)
from drc_stat_engine.stats.strategies import (
    PRIORITY_DEPENDENT_OPS,
    STRATEGY_PRIORITY_LISTS,
    build_strategy_pipeline,
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
        added = sum(
            (op.dice_to_add or {}).get("red", 0)
            + (op.dice_to_add or {}).get("blue", 0)
            + (op.dice_to_add or {}).get("black", 0)
            for op in pipeline if op.type == "add_dice"
        )
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
        return pd.concat([cancelled_df, kept_df]).groupby("value", as_index=False).agg({
            "proba":  "sum",
            "damage": "first",
            "crit":   "first",
            "acc":    "first",
            "blank":  "first",
        })

    elif attack_effect.type == "add_dice":
        dice = attack_effect.dice_to_add or {}
        return backend_mod.add_dice_to_roll(
            roll_df,
            red=dice.get("red", 0),
            blue=dice.get("blue", 0),
            black=dice.get("black", 0),
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
) -> List[dict]:
    """
    Orchestrate all report variants.

    - Validates pool and pipeline.
    - Selects the backend (combinatorial or MC) via _select_backend.
    - Builds the initial roll_df via backend_mod.combine_dice.
    - Runs once per strategy, labeling each variant.
    - Defaults to ["max_damage"] if no strategies provided.

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

    Returns a list of variant dicts:
        {"label": str, "damage": [...], "accuracy": [...], "crit": float, ...}
    Requirements: 3.3, 3.6, 4.1, 6.1, 6.5, 6.6
    """
    if strategies is None:
        strategies = ["max_damage"]

    validate_dice_pool(dice_pool)
    validate_attack_effect_pipeline(pipeline, dice_pool)

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
        final_df = run_pipeline(roll_df.copy(), strategy_pipeline, dice_pool.type, backend_mod=backend_mod)

        # Collect the resolved priority_list from the first priority-dependent op (if any)
        priority_list = next(
            (op.priority_list for op in strategy_pipeline if op.type in PRIORITY_DEPENDENT_OPS),
            STRATEGY_PRIORITY_LISTS[dice_pool.type][strategy]["reroll"],
        )
        variants.append({
            "label":      strategy,
            "damage":     cumulative_damage(final_df),
            "damage_zero": float(final_df.loc[final_df["damage"] == 0, "proba"].sum()),
            "accuracy":   cumulative_accuracy(final_df),
            "acc_zero":   float(final_df.loc[final_df["acc"] == 0, "proba"].sum()),
            "crit":       crit_probability(final_df),
            "avg_damage": average_damage(final_df),
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
            parts.append(f"add_dice [{r}R {u}U {b}B]")
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
