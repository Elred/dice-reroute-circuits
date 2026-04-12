"""
dice_models.py — Domain data structures and input validation.

Defines the DicePool and AttackEffect dataclasses that describe an attack
scenario, along with the validation functions that enforce their constraints
before any computation takes place.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_TYPES = {"ship", "squad"}
VALID_ATTACK_EFFECT_TYPES = {"reroll", "cancel", "add_dice", "change_die", "reroll_all"}
MAX_DICE = 20

VALID_CONDITION_ATTRIBUTES = {"damage", "crit", "acc", "blank"}
VALID_CONDITION_OPERATORS = {"lte", "lt", "gte", "gt", "eq", "neq"}


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
class Condition:
    """A boolean predicate over roll outcome attributes."""
    attribute: str   # one of "damage", "crit", "acc", "blank"
    operator: str    # one of "lte", "lt", "gte", "gt", "eq", "neq"
    threshold: int

    def __post_init__(self):
        if self.attribute not in VALID_CONDITION_ATTRIBUTES:
            raise ValueError(
                f"Invalid condition attribute '{self.attribute}'. "
                f"Must be one of: {sorted(VALID_CONDITION_ATTRIBUTES)}."
            )
        if self.operator not in VALID_CONDITION_OPERATORS:
            raise ValueError(
                f"Invalid condition operator '{self.operator}'. "
                f"Must be one of: {sorted(VALID_CONDITION_OPERATORS)}."
            )
        if not isinstance(self.threshold, int):
            raise ValueError(
                f"Condition threshold must be an integer, "
                f"got {type(self.threshold).__name__}."
            )


def evaluate_condition(condition: Condition, roll_df: pd.DataFrame) -> pd.Series:
    """Return a boolean Series: True for rows where the condition is satisfied."""
    ops = {
        "lte": lambda col, t: col <= t,
        "lt":  lambda col, t: col < t,
        "gte": lambda col, t: col >= t,
        "gt":  lambda col, t: col > t,
        "eq":  lambda col, t: col == t,
        "neq": lambda col, t: col != t,
    }
    return ops[condition.operator](roll_df[condition.attribute], condition.threshold)


@dataclass
class AttackEffect:
    """A single attack effect in the pipeline."""
    # One of: "reroll", "cancel", "add_dice", "change_die"
    type: str
    # For reroll/cancel: how many dice to affect.
    count: int = 1
    # For reroll/cancel: the whitelist of face value strings this attack effect is allowed to touch.
    # The strategy determines the order; applicable_results gates which faces are eligible.
    applicable_results: List[str] = field(default_factory=list)
    # Resolved priority list — populated by build_strategy_pipeline from the strategy ordering
    # filtered to applicable_results. Used by apply_attack_effect. Never set manually.
    priority_list: List[str] = field(default_factory=list)
    # For add_dice: explicit color counts, e.g. {"red": 0, "blue": 0, "black": 2}.
    # Required when type == "add_dice"; ignored for reroll/cancel/change_die.
    dice_to_add: Optional[Dict[str, int]] = None
    # For change_die: the face value string to set the die to. May be color-agnostic (e.g. "hit")
    # or color-specific (e.g. "R_hit"). Required when type == "change_die".
    target_result: Optional[str] = None
    condition: Optional[Condition] = None  # Required when type == "reroll_all"


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

    # Hard limit
    total = pool.red + pool.blue + pool.black
    if total > MAX_DICE:
        raise ValueError(
            f"DicePool has {total} dice, exceeding the maximum of {MAX_DICE}."
        )


def validate_attack_effect_pipeline(pipeline: List[AttackEffect], pool: DicePool) -> None:
    """
    Validate an attack effect pipeline against a DicePool.

    Raises ValueError for unknown attack effect types (Requirement 2.5).
    Raises ValueError if total dice (base pool + add_dice ops) exceeds MAX_DICE.
    """
    running_size = pool.red + pool.blue + pool.black
    for idx, op in enumerate(pipeline):
        if op.type not in VALID_ATTACK_EFFECT_TYPES:
            raise ValueError(
                f"AttackEffect {idx}: unknown attack effect type '{op.type}'. "
                f"Supported types: {sorted(VALID_ATTACK_EFFECT_TYPES)}."
            )
        if op.type == "change_die" and op.target_result is None:
            raise ValueError(
                f"AttackEffect {idx}: 'change_die' effect requires a 'target_result' field."
            )
        if op.type == "reroll_all":
            if op.condition is None:
                raise ValueError(
                    f"AttackEffect {idx}: 'reroll_all' effect requires a non-None 'condition' field."
                )
        if op.type == "add_dice":
            d = op.dice_to_add or {}
            added = d.get("red", 0) + d.get("blue", 0) + d.get("black", 0)
            running_size += added
            if running_size > MAX_DICE:
                raise ValueError(
                    f"AttackEffect {idx}: total dice count would reach {running_size}, "
                    f"exceeding the maximum of {MAX_DICE}."
                )
