"""
dice_models.py — Domain data structures and input validation.

Defines the DicePool and AttackEffect dataclasses that describe an attack
scenario, along with the validation functions that enforce their constraints
before any computation takes place.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import pandas as pd

from drc_stat_engine.stats.profiles import (
    red_die_ship, blue_die_ship, black_die_ship,
    red_die_squad, blue_die_squad, black_die_squad,
)


def _build_valid_faces() -> Dict[str, Set[str]]:
    """Build sets of valid face value strings per pool type."""
    ship_faces = set()
    for profile in (red_die_ship, blue_die_ship, black_die_ship):
        for face in profile:
            ship_faces.add(face["value"])
    squad_faces = set()
    for profile in (red_die_squad, blue_die_squad, black_die_squad):
        for face in profile:
            squad_faces.add(face["value"])
    return {"ship": ship_faces, "squad": squad_faces}


VALID_FACES_BY_TYPE = _build_valid_faces()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_TYPES = {"ship", "squad"}
VALID_ATTACK_EFFECT_TYPES = {"reroll", "cancel", "add_dice", "change_die", "reroll_all", "add_set_die"}
VALID_DEFENSE_EFFECT_TYPES = {"defense_reroll", "defense_cancel", "reduce_damage", "divide_damage"}
MAX_DICE = 20

VALID_CONDITION_ATTRIBUTES = {"damage", "crit", "acc", "blank"}
VALID_CONDITION_OPERATORS = {"lte", "lt", "gte", "gt", "eq", "neq"}

COLOR_PREFIXES = {"red": "R", "blue": "U", "black": "B"}


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
    face_condition: Optional[str] = None       # Face string for presence check (add_dice/add_set_die only)
    color_in_pool: bool = False                 # Dynamic color selection (add_dice only)
    color_priority: Optional[List[str]] = None  # Color priority permutation (when color_in_pool=True)


@dataclass
class DefenseEffect:
    """A single defense effect in the pipeline."""
    # One of: "defense_reroll", "defense_cancel", "reduce_damage", "divide_damage"
    type: str
    # For defense_reroll/defense_cancel: how many dice to affect.
    count: int = 1
    # For defense_reroll: "safe" or "could_be_blank"
    mode: Optional[str] = None
    # For reduce_damage: flat damage reduction value N.
    amount: int = 0
    # Optional filter restricting which faces reroll/cancel can target.
    applicable_results: List[str] = field(default_factory=list)
    # Resolved priority list — populated by build_defense_pipeline. Never set manually.
    priority_list: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Face-presence and color-selection helpers
# ---------------------------------------------------------------------------

def evaluate_face_condition(face_condition: str, value_str: str) -> bool:
    """Return True if result_condition token appears in the space-separated value_str."""
    return face_condition in value_str.split(" ")


def select_color_from_pool(color_priority: List[str], value_str: str) -> str:
    """Return the first color in color_priority whose prefix appears in value_str tokens."""
    tokens = value_str.split(" ")
    for color in color_priority:
        prefix = COLOR_PREFIXES[color]
        if any(t.startswith(prefix + "_") for t in tokens):
            return color
    # Fallback — should not happen if pool is non-empty and priority is complete
    return color_priority[0]


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
    valid_faces = VALID_FACES_BY_TYPE.get(pool.type, set())
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

        # --- add_set_die validation (Req 1.2, 1.3, 1.4, 1.6) ---
        if op.type == "add_set_die":
            if op.target_result is None:
                raise ValueError(
                    f"AttackEffect {idx}: 'add_set_die' effect requires a 'target_result' field."
                )
            if op.target_result not in valid_faces:
                raise ValueError(
                    f"AttackEffect {idx}: 'add_set_die' target_result '{op.target_result}' "
                    f"is not a valid face for pool type '{pool.type}'."
                )
            running_size += 1
            if running_size > MAX_DICE:
                raise ValueError(
                    f"AttackEffect {idx}: total dice count would reach {running_size}, "
                    f"exceeding the maximum of {MAX_DICE}."
                )

        # --- face_condition validation (Req 4.4, 14.4) ---
        if op.face_condition is not None:
            if op.type not in ("add_dice", "add_set_die"):
                raise ValueError(
                    f"AttackEffect {idx}: 'face_condition' is only valid on "
                    f"'add_dice' and 'add_set_die' types, not '{op.type}'."
                )
            if not isinstance(op.face_condition, str) or op.face_condition == "":
                raise ValueError(
                    f"AttackEffect {idx}: 'face_condition' must be a non-empty string."
                )

        # --- color_in_pool validation (Req 14.5) ---
        if op.color_in_pool:
            if op.type != "add_dice":
                raise ValueError(
                    f"AttackEffect {idx}: 'color_in_pool' is only valid on "
                    f"'add_dice' type, not '{op.type}'."
                )

        # --- color_priority validation (Req 8.3, 9.4, 9.5, 14.3) ---
        if op.color_in_pool and op.color_priority is not None:
            if sorted(op.color_priority) != ["black", "blue", "red"]:
                raise ValueError(
                    f"AttackEffect {idx}: 'color_priority' must be a permutation of "
                    f"['red', 'blue', 'black'], got {op.color_priority}."
                )


def validate_defense_pipeline(pipeline: List[DefenseEffect]) -> None:
    """
    Validate a defense effect pipeline.

    Raises ValueError for:
    - Unknown defense effect types                          — Requirement 1.6, 9.1
    - Missing or invalid mode on defense_reroll             — Requirement 9.2, 9.3
    - Non-positive count on defense_reroll/defense_cancel   — Requirement 9.5
    - Non-positive amount on reduce_damage                  — Requirement 9.4
    """
    for idx, effect in enumerate(pipeline):
        if effect.type not in VALID_DEFENSE_EFFECT_TYPES:
            raise ValueError(
                f"DefenseEffect {idx}: unknown defense effect type '{effect.type}'. "
                f"Valid types: {sorted(VALID_DEFENSE_EFFECT_TYPES)}."
            )

        if effect.type == "defense_reroll":
            if effect.mode is None:
                raise ValueError(
                    f"DefenseEffect {idx}: 'defense_reroll' requires a 'mode' field."
                )
            if effect.mode not in ("safe", "could_be_blank"):
                raise ValueError(
                    f"DefenseEffect {idx}: defense_reroll mode must be "
                    f"'safe' or 'could_be_blank', got '{effect.mode}'."
                )
            if effect.count <= 0:
                raise ValueError(
                    f"DefenseEffect {idx}: defense_reroll/cancel count must be "
                    f"positive, got {effect.count}."
                )

        if effect.type == "defense_cancel":
            if effect.count <= 0:
                raise ValueError(
                    f"DefenseEffect {idx}: defense_reroll/cancel count must be "
                    f"positive, got {effect.count}."
                )

        if effect.type == "reduce_damage":
            if effect.amount <= 0:
                raise ValueError(
                    f"DefenseEffect {idx}: reduce_damage amount must be "
                    f"positive, got {effect.amount}."
                )
