"""
report.py — Dice Stats Report Generator

Run from the stats/ directory:
    python report.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import pandas as pd

from drc_stat_engine.stats.dice import combine_dice, reroll_dice, cancel_dice, add_dice_to_roll
from drc_stat_engine.stats.profiles import (
    red_die_ship, blue_die_ship, black_die_ship,
    red_die_squad, blue_die_squad, black_die_squad,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_TYPES = {"ship", "squad"}
VALID_OPERATION_TYPES = {"reroll", "cancel", "add_dice"}

# Map (color, type) -> profile list
_PROFILES = {
    ("red",   "ship"):  red_die_ship,
    ("blue",  "ship"):  blue_die_ship,
    ("black", "ship"):  black_die_ship,
    ("red",   "squad"): red_die_squad,
    ("blue",  "squad"): blue_die_squad,
    ("black", "squad"): black_die_squad,
}


def _face_values_for_pool(red: int, blue: int, black: int, type_str: str) -> set:
    """Return the set of valid face value strings for the given pool composition."""
    values = set()
    if red > 0:
        values.update(face["value"] for face in _PROFILES[("red", type_str)])
    if blue > 0:
        values.update(face["value"] for face in _PROFILES[("blue", type_str)])
    if black > 0:
        values.update(face["value"] for face in _PROFILES[("black", type_str)])
    return values


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DicePool:
    """Describes the dice pool: counts per color and a type (ship or squad)."""
    red: int = 0
    blue: int = 0
    black: int = 0
    type: str = "ship"


@dataclass
class Operation:
    """A single operation in the pipeline."""
    # One of: "reroll", "cancel", "add_dice"
    type: str
    # For reroll/cancel: how many dice to affect.
    count: int = 1
    # For reroll/cancel: the whitelist of face value strings this operation is allowed to touch.
    # The strategy determines the order; applicable_results gates which faces are eligible.
    applicable_results: List[str] = field(default_factory=list)
    # Resolved priority list — populated by build_strategy_pipeline from the strategy ordering
    # filtered to applicable_results. Used by apply_operation. Never set manually.
    priority_list: List[str] = field(default_factory=list)
    # For add_dice: explicit color counts, e.g. {"red": 0, "blue": 0, "black": 2}.
    # Required when type == "add_dice"; ignored for reroll/cancel.
    dice_to_add: Optional[Dict[str, int]] = None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_dice_pool(pool: DicePool) -> None:
    """
    Validate a DicePool.

    Raises ValueError for:
    - Empty pool (all counts are zero)          — Requirement 1.2
    - Negative or non-integer counts            — Requirement 1.3
    - Unsupported type (not 'ship' or 'squad')  — Requirement 1.4
    """
    # Requirement 1.4 — type check first so the error is clear
    if pool.type not in VALID_TYPES:
        raise ValueError(
            f"Unsupported dice type '{pool.type}'. Must be one of: {sorted(VALID_TYPES)}."
        )

    # Requirement 1.3 — non-integer or negative counts
    for color, count in (("red", pool.red), ("blue", pool.blue), ("black", pool.black)):
        if not isinstance(count, int):
            raise ValueError(
                f"Dice count for '{color}' must be an integer, got {type(count).__name__}."
            )
        if count < 0:
            raise ValueError(
                f"Dice count for '{color}' must be non-negative, got {count}."
            )

    # Requirement 1.2 — empty pool
    if pool.red == 0 and pool.blue == 0 and pool.black == 0:
        raise ValueError("DicePool is empty: all dice counts are zero.")


def validate_operation_pipeline(pipeline: List[Operation], pool: DicePool) -> None:
    """
    Validate an operation pipeline against a DicePool.

    Raises ValueError for unknown operation types (Requirement 2.5).

    Note: applicable_results faces are NOT validated against the pool. An operation
    targeting faces absent from the pool is valid — it simply has no effect at runtime
    (e.g. reroll R_blank on an all-black pool is a no-op).
    """
    for idx, op in enumerate(pipeline):
        if op.type not in VALID_OPERATION_TYPES:
            raise ValueError(
                f"Operation {idx}: unknown operation type '{op.type}'. "
                f"Supported types: {sorted(VALID_OPERATION_TYPES)}."
            )


# ---------------------------------------------------------------------------
# Operation pipeline executor
# ---------------------------------------------------------------------------

PROB_TOLERANCE = 1e-9


def apply_operation(roll_df, operation: "Operation", type_str: str):
    """
    Dispatch a single Operation to the appropriate dice.py function.

    - reroll  → reroll_dice(roll_df, results_to_reroll, reroll_count, type_str)
    - cancel  → cancel_dice(roll_df, results_to_cancel, cancel_count, type_str)
    - add_dice → add_dice_to_roll(roll_df, red, blue, black, type_str)  [from op.dice_to_add]

    Both reroll_dice and cancel_dice return (result_df, initial_df); we keep
    only result_df.  add_dice_to_roll returns a single DataFrame.
    """
    if operation.type == "reroll":
        result_df, _ = reroll_dice(
            roll_df,
            results_to_reroll=operation.priority_list,
            reroll_count=operation.count,
            type_str=type_str,
        )
        return result_df

    elif operation.type == "cancel":
        # cancel_dice returns (cancelled_df, kept_df):
        #   cancelled_df — rows where matching dice were removed (stats adjusted)
        #   kept_df      — rows where no dice matched the cancel list (unchanged)
        # The full post-cancel distribution requires both parts.
        cancelled_df, kept_df = cancel_dice(
            roll_df,
            results_to_cancel=operation.priority_list,
            cancel_count=operation.count,
            type_str=type_str,
        )
        result_df = pd.concat([cancelled_df, kept_df]).groupby("value", as_index=False).agg({
            "proba": "sum",
            "damage": "first",
            "crit": "first",
            "acc": "first",
            "blank": "first",
        })
        return result_df

    elif operation.type == "add_dice":
        d = operation.dice_to_add or {}
        return add_dice_to_roll(
            roll_df,
            red=d.get("red", 0),
            blue=d.get("blue", 0),
            black=d.get("black", 0),
            type_str=type_str,
        )

    else:
        raise ValueError(f"Unknown operation type '{operation.type}'.")


def _check_probability_integrity(roll_df, operation: "Operation", op_index: int) -> None:
    """
    Assert that probabilities in roll_df sum to 1.0 within PROB_TOLERANCE.
    Raises ValueError identifying the offending operation if the check fails.
    Requirements: 8.1, 8.2
    """
    total = roll_df["proba"].sum()
    if abs(total - 1.0) > PROB_TOLERANCE:
        raise ValueError(
            f"Probability integrity check failed after operation {op_index} "
            f"(type='{operation.type}'): probabilities sum to {total:.15f}, "
            f"expected 1.0 (tolerance {PROB_TOLERANCE})."
        )


def run_pipeline(roll_df, pipeline: List["Operation"], type_str: str):
    """
    Apply all operations in the pipeline sequentially, checking probability
    integrity after each step.

    Returns the final roll_df unchanged if the pipeline is empty.
    Requirements: 2.1, 2.4, 8.1
    """
    if not pipeline:
        return roll_df

    for idx, operation in enumerate(pipeline):
        roll_df = apply_operation(roll_df, operation, type_str)
        _check_probability_integrity(roll_df, operation, idx)

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
# Strategy priority lists (per dice type)
# Requirements: 6.2, 6.3, 6.4
# ---------------------------------------------------------------------------
#
# Priority order = reroll/cancel lowest-value faces first.
# Ship face attributes (for reference):
#   R_blank:   damage=0, crit=0, acc=0  (blank)
#   B_blank:   damage=0, crit=0, acc=0  (blank)
#   R_acc:     damage=0, crit=0, acc=1
#   U_acc:     damage=0, crit=0, acc=1
#   R_hit:     damage=1, crit=0, acc=0
#   U_hit:     damage=1, crit=0, acc=0
#   B_hit:     damage=1, crit=0, acc=0
#   R_crit:    damage=1, crit=1, acc=0
#   U_crit:    damage=1, crit=1, acc=0
#   R_hit+hit: damage=2, crit=0, acc=0
#   B_hit+crit:damage=2, crit=1, acc=0
#
# Squad face attributes (key differences):
#   R_crit:    damage=0, crit=0, acc=0  (worthless face for squad)
#   U_crit:    damage=0, crit=0, acc=0  (worthless face for squad)
#   B_hit+crit:damage=1, crit=0, acc=0  (no crit for squad)

STRATEGY_PRIORITY_LISTS = {
    "ship": {
        # max_damage: sacrifice blanks → acc → hits → crits (keep highest damage)
        "max_damage": [
            "R_blank", "B_blank",
            "U_acc", "R_acc"
        ],
        "max_doubles": [
            "R_blank", "B_blank",
            "U_acc", "R_acc", 
            "U_hit", "B_hit", "R_hit",
            "R_crit", "U_crit"
        ],
        # max_accuracy: sacrifice blanks → hits → crits → acc (keep acc faces)
        "max_accuracy": [
            "R_blank",
            "U_hit", "U_crit", 
            "R_hit", "R_crit"
        ],
        # max_crits: sacrifice blanks → acc → hits → crits → multi-damage (keep damage + crits)
        "max_crits": [
            "R_blank", "B_blank",
            "U_acc", "R_acc", 
            "U_hit", "B_hit", "R_hit"
        ],
    },
    "squad": {
        # Squad: R_crit and U_crit are damage=0,crit=0 — treat as near-blanks.
        # max_damage: sacrifice blanks → zero-value crits → acc → hits → multi-damage
        "max_damage": [
            "R_blank", "B_blank",
            "R_crit", "U_crit",
            "R_acc", "U_acc",
            "R_hit", "U_hit", "B_hit",
            "B_hit+crit",
            "R_hit+hit",
        ],
        # max_accuracy: sacrifice blanks → zero-value crits → hits → multi-damage → acc
        "max_accuracy": [
            "R_blank", "B_blank",
            "R_crit", "U_crit",
            "R_hit", "U_hit", "B_hit",
            "B_hit+crit",
            "R_hit+hit",
            "R_acc", "U_acc",
        ],
        # max_crits: squad has no true crit faces (R_crit/U_crit are 0-value),
        # so prioritize keeping any face that has crit=1 — none exist for squad.
        # Fall back to max_damage ordering.
        "max_crits": [
            "R_blank", "B_blank",
            "R_crit", "U_crit",
            "R_acc", "U_acc",
            "R_hit", "U_hit", "B_hit",
            "B_hit+crit",
            "R_hit+hit",
        ],
    },
}

PRIORITY_DEPENDENT_OPS = {"reroll", "cancel"}


# ---------------------------------------------------------------------------
# Strategy pipeline builder
# Requirements: 6.1, 6.5
# ---------------------------------------------------------------------------

def build_strategy_pipeline(
    pipeline: List[Operation], strategy: str, type_str: str
) -> List[Operation]:
    """
    Return a copy of the pipeline with priority_list resolved on all
    priority-dependent operations (reroll, cancel).

    The resolved priority_list = strategy ordering filtered to faces in applicable_results,
    preserving the strategy's order. applicable_results is never modified.

    Non-priority-dependent operations (add_dice) are passed through unchanged.
    Requirements: 6.1, 6.5
    """
    strategy_ordering = STRATEGY_PRIORITY_LISTS[type_str][strategy]
    result = []
    for op in pipeline:
        if op.type in PRIORITY_DEPENDENT_OPS:
            applicable_set = set(op.applicable_results)
            resolved = [face for face in strategy_ordering if face in applicable_set]
            result.append(Operation(
                type=op.type,
                count=op.count,
                applicable_results=list(op.applicable_results),
                priority_list=resolved,
            ))
        else:
            result.append(Operation(
                type=op.type,
                count=op.count,
                applicable_results=list(op.applicable_results),
                priority_list=list(op.priority_list),
                dice_to_add=dict(op.dice_to_add) if op.dice_to_add is not None else None,
            ))
    return result


# ---------------------------------------------------------------------------
# Report generator
# Requirements: 6.1, 6.5, 6.6
# ---------------------------------------------------------------------------

def generate_report(
    dice_pool: DicePool,
    pipeline: List[Operation],
    strategies: List[str] = None,
) -> List[dict]:
    """
    Orchestrate all report variants.

    - Validates pool and pipeline.
    - Builds the initial roll_df via combine_dice.
    - Runs once per strategy, labeling each variant.
    - Defaults to ["max_damage"] if no strategies provided.

    Returns a list of variant dicts:
        {"label": str, "damage": [...], "accuracy": [...], "crit": float}
    Requirements: 6.1, 6.5, 6.6
    """
    if strategies is None:
        strategies = ["max_damage"]

    validate_dice_pool(dice_pool)
    validate_operation_pipeline(pipeline, dice_pool)

    roll_df = combine_dice(dice_pool.red, dice_pool.blue, dice_pool.black, dice_pool.type)

    variants = []
    for strategy in strategies:
        if strategy not in STRATEGY_PRIORITY_LISTS[dice_pool.type]:
            raise ValueError(
                f"Unknown strategy '{strategy}' for type '{dice_pool.type}'. "
                f"Valid strategies: {sorted(STRATEGY_PRIORITY_LISTS[dice_pool.type])}."
            )
        strategy_pipeline = build_strategy_pipeline(pipeline, strategy, dice_pool.type)
        final_df = run_pipeline(roll_df.copy(), strategy_pipeline, dice_pool.type)
        # Collect the resolved priority_list from the first priority-dependent op (if any)
        priority_list = next(
            (op.priority_list for op in strategy_pipeline if op.type in PRIORITY_DEPENDENT_OPS),
            STRATEGY_PRIORITY_LISTS[dice_pool.type][strategy],
        )
        variants.append({
            "label": strategy,
            "damage": cumulative_damage(final_df),
            "accuracy": cumulative_accuracy(final_df),
            "crit": crit_probability(final_df),
            "avg_damage": average_damage(final_df),
            "priority_list": priority_list,
        })
    return variants


# ---------------------------------------------------------------------------
# Report output formatter
# Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
# ---------------------------------------------------------------------------

def _format_pipeline(pipeline: List[Operation]) -> str:
    """Format the operation pipeline as a human-readable string."""
    if not pipeline:
        return "(none)"
    parts = []
    for op in pipeline:
        if op.type in ("reroll", "cancel"):
            faces = ", ".join(op.applicable_results)
            parts.append(f"{op.type} x{op.count} [{faces}]")
        elif op.type == "add_dice":
            d = op.dice_to_add or {}
            r, u, b = d.get("red", 0), d.get("blue", 0), d.get("black", 0)
            parts.append(f"add_dice [{r}R {u}U {b}B]")
        else:
            parts.append(op.type)
    return " | ".join(parts)


def format_report(
    dice_pool: DicePool,
    pipeline: List[Operation],
    variants: List[dict],
) -> str:
    """
    Produce a formatted text report string (does not print directly).

    Header shows dice pool composition and applied pipeline.
    Each variant contains cumulative damage/accuracy tables and crit probability.
    Multiple variants are separated and labeled; single variant omits label/separator.

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

        # Priority list — faces ordered from lowest to highest value (reroll/cancel order)
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


def main():
    """
    Sample scenario: 3 Red + 2 Blue ship dice, reroll up to 2 blanks, with all strategies.
    applicable_results scopes the reroll to blanks only; strategy determines order within that set.
    """
    pool = DicePool(red=0, blue=1, black=0, type="ship")

    pipeline = [
        Operation(type="add_dice", dice_to_add={"red": 0, "blue": 1, "black": 0}),
    ]
    strategies = ["max_damage"]

    variants = generate_report(pool, pipeline, strategies)
    output = format_report(pool, pipeline, variants)
    print(output)


if __name__ == "__main__":
    main()
