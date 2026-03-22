# Design Document: Dice Stats Report

## Overview

`drc_stat_engine/stats/report.py` is a self-contained module that builds on the existing `dice.py` and `profiles.py` infrastructure to produce a formatted probability report for a given dice pool and operation pipeline. It introduces no new dependencies beyond what already exists in the project.

---

## Architecture

The module is structured as a pipeline:

```
DicePool + [Operation] + [Strategy]
        │
        ▼
  validate_dice_pool()
  validate_operation_pipeline()
        │
        ▼
  combine_dice()          ← dice.py
        │
        ▼
  run_pipeline()
    └─ apply_operation()  ← wraps reroll_dice / cancel_dice / add_dice_to_roll
    └─ integrity check (proba sum ≈ 1.0)
        │
        ▼
  generate_report()
    └─ build_strategy_pipeline()  (if priority-dependent ops exist)
    └─ cumulative_damage()
    └─ cumulative_accuracy()
    └─ crit_probability()
        │
        ▼
  format_report()  →  stdout
```

---

## Data Structures

### `DicePool` (dataclass)

```python
@dataclass
class DicePool:
    red:   int = 0
    blue:  int = 0
    black: int = 0
    type:  str = "ship"   # "ship" | "squad"
```

### `Operation` (dataclass)

```python
@dataclass
class Operation:
    type:               str        # "reroll" | "cancel" | "add_dice"
    count:              int = 1    # number of dice to affect (reroll/cancel)
    applicable_results: List[str] = field(default_factory=list)
    # reroll/cancel: user-defined whitelist of face values this op is allowed to target.
    #   Validated against the pool's profile. Never overwritten by strategy resolution.
    priority_list:      List[str] = field(default_factory=list)
    # Resolved at runtime by build_strategy_pipeline: strategy ordering filtered to
    # applicable_results. Used by apply_operation. Not set manually by callers.
    dice_to_add:        Optional[Dict[str, int]] = None
    # add_dice: explicit color counts, e.g. {"red": 0, "blue": 0, "black": 2}.
    # Required when type == "add_dice"; ignored for reroll/cancel.
```

---

## Component Design

### Validation

**`validate_dice_pool(pool: DicePool) -> None`**
- Raises `ValueError` if type is not `"ship"` or `"squad"` (req 1.4)
- Raises `ValueError` if any count is negative or non-integer (req 1.3)
- Raises `ValueError` if all counts are zero (req 1.2)

**`validate_operation_pipeline(pipeline: List[Operation], pool: DicePool) -> None`**
- Raises `ValueError` for unknown operation types (req 2.5)
- Does **not** validate `applicable_results` faces against the pool profile (req 2.3) — faces absent from the pool are silently ignored at runtime (the operation becomes a no-op for those faces)

---

### Operation Pipeline Executor

**`apply_operation(roll_df, op: Operation, type_str: str) -> DataFrame`**

Dispatches to existing `dice.py` functions:

| `op.type`  | `dice.py` function     | Arguments                                           |
|------------|------------------------|-----------------------------------------------------|
| `reroll`   | `reroll_dice()`        | `results_to_reroll=op.priority_list`, `reroll_count=op.count` |
| `cancel`   | `cancel_dice()`        | `results_to_cancel=op.priority_list`, `cancel_count=op.count` |
| `add_dice` | `add_dice_to_roll()`   | `red/blue/black` from `op.dice_to_add`, `type_str` |

`priority_list` is the resolved list produced by `build_strategy_pipeline` — it contains only the faces from `applicable_results`, ordered by the active strategy. `apply_operation` never reads `applicable_results` directly for reroll/cancel.

Both `reroll_dice` and `cancel_dice` return `(result_df, initial_df)` — `apply_operation` returns only `result_df`.

**`run_pipeline(roll_df, pipeline: List[Operation], type_str: str) -> DataFrame`**
- Applies each operation in order via `apply_operation`
- After each step, asserts `roll_df["proba"].sum()` is within `1e-9` of `1.0` (req 8.1, 8.2)
- Returns the final `roll_df`; returns input unchanged if pipeline is empty (req 2.4)

---

### Cumulative Probability Computations

**`cumulative_damage(roll_df) -> List[Tuple[int, float]]`**
- Returns `[(x, P(damage >= x)) for x in range(0, max_damage + 1)]`
- Covers all integers in range, including those with probability 0 (req 3.1, 3.2, 3.3)

**`cumulative_accuracy(roll_df) -> List[Tuple[int, float]]`**
- Returns `[(x, P(acc >= x)) for x in range(0, max_acc + 1)]`
- Same coverage guarantee (req 4.1, 4.2, 4.3)

**`crit_probability(roll_df) -> float`**
- Returns `roll_df[roll_df["crit"] >= 1]["proba"].sum()` (req 5.1)

---

### Strategy System

**Strategy priority lists** are defined per dice type (`ship` / `squad`) since face value strings differ between the two. Each list contains only the faces that are candidates for reroll/cancel — faces not in the list are kept unconditionally.

| Strategy       | Faces kept unconditionally                          | Sacrifice order (lowest-value first)                        |
|----------------|-----------------------------------------------------|-------------------------------------------------------------|
| `max_damage`   | hits, crits, multi-damage                           | blanks → acc (blue before red)                              |
| `max_doubles`  | multi-damage (`R_hit+hit`, `B_hit+crit`)            | blanks → acc → single hits → single crits                  |
| `max_accuracy` | acc, all black faces                                | blanks → blue hits/crits → red hits/crits                  |
| `max_crits`    | crits, multi-damage                                 | blanks → acc → single hits                                  |

Ship face orderings (faces listed = candidates for reroll/cancel; unlisted = kept):
- `max_damage`:   `["R_blank", "B_blank", "U_acc", "R_acc"]`
- `max_doubles`:  `["R_blank", "B_blank", "U_acc", "R_acc", "U_hit", "B_hit", "R_hit", "R_crit", "U_crit"]`
- `max_accuracy`: `["R_blank", "U_hit", "U_crit", "R_hit", "R_crit"]`
- `max_crits`:    `["R_blank", "B_blank", "U_acc", "R_acc", "U_hit", "B_hit", "R_hit"]`

Squad differences: `R_crit` and `U_crit` are `damage=0, crit=0` for squad, so they are treated as near-blanks and appear early in all squad strategy lists. `B_hit+crit` has `damage=1, crit=0` for squad (no crit value).

**`build_strategy_pipeline(pipeline: List[Operation], strategy: str, type_str: str) -> List[Operation]`**
- Returns a copy of the pipeline with `priority_list` resolved on all `reroll`/`cancel` operations
- Resolution: `priority_list = [face for face in strategy_ordering if face in op.applicable_results]` — preserves strategy order, gates on `applicable_results`
- `applicable_results` is copied unchanged onto the new operation; it is never modified
- `add_dice` operations are passed through with `applicable_results` copied and `priority_list` left empty

**`generate_report(dice_pool: DicePool, pipeline: List[Operation], strategies: List[str] = None) -> List[dict]`**
- Validates pool and pipeline
- Builds initial `roll_df` via `combine_dice()`
- Defaults to `["max_damage"]` if no strategies provided
- Valid ship strategies: `max_damage`, `max_doubles`, `max_accuracy`, `max_crits`
- Valid squad strategies: `max_damage`, `max_accuracy`, `max_crits`
- Runs once per strategy: calls `build_strategy_pipeline`, then `run_pipeline`, then computes stats
- Each variant dict: `{"label": str, "damage": [...], "accuracy": [...], "crit": float, "avg_damage": float, "priority_list": [...]}`

---

### Output Formatting

**`format_report(dice_pool: DicePool, pipeline: List[Operation], variants: List[dict]) -> str`**
```
Dice Pool: 3R 0U 2B (ship)
Pipeline:  reroll x1 [R_blank, B_blank] | cancel x2 [R_blank, B_blank, R_hit]

=== Strategy: max_damage ===

Priority List: R_blank > B_blank > U_acc > R_acc

Cumulative Damage:
  >= 0:  100.00%
  >= 1:   75.30%
  ...

Cumulative Accuracy:
  >= 0:  100.00%
  >= 1:   18.80%
  ...

Crit Probability: 43.80%
Average Damage:   1.23

==============================

=== Strategy: max_doubles ===
...
```

- Percentages rounded to 2 decimal places (req 7.3, 7.4, 7.5)
- Header shows pool composition and pipeline `applicable_results` (req 7.2, 7.7)
- Every variant is labeled with its strategy name (req 6.7)
- Multiple variants are separated by a divider line (req 7.6)

---

## Key Design Decisions

**Reuse `dice.py` functions directly** — `reroll_dice`, `cancel_dice`, and `add_dice_to_roll` already implement the core mechanics correctly. `apply_operation` is a thin dispatch layer, not a reimplementation.

**`reroll_dice` / `cancel_dice` return tuples** — both return `(result_df, initial_df)`. `apply_operation` unpacks and discards the second element.

**`applicable_results` and `priority_list` are separate concerns** — `applicable_results` is the user-facing whitelist (what the operation is *allowed* to touch); `priority_list` is the runtime-resolved ordered list (what it *will* touch, in what order). Strategy resolution fills `priority_list` by intersecting the strategy's full ordering with `applicable_results`. This means a face that ranks high in the strategy ordering but isn't in `applicable_results` is simply skipped.

**Strategy is always required** — there is no "no-strategy" path. `generate_report` defaults to `["max_damage"]` if no strategies are passed. Every variant is labeled.

**Strategy priority lists are hardcoded per type** — face value strings are type-specific (`R_crit` has `damage=1` for ship but `damage=0` for squad), so strategies must be defined separately for each type rather than derived dynamically.

**`max_crits` keeps damage** — the `max_crits` ordering sacrifices blanks, then acc, then hits, then crits, keeping multi-damage faces last. This preserves damage output while maximising crit retention.

**Probability integrity check after each op** — not just at the end, so the offending operation can be identified precisely (req 8.2).

**`generate_report` returns structured data; `format_report` handles presentation** — keeps computation and formatting separate and independently testable.

---

## File Layout

All code lives in `drc_stat_engine/stats/report.py`. Run from the `drc_stat_engine/stats/` directory:

```
cd drc_stat_engine/stats && python report.py
```

Imports used:
```python
from dice import combine_dice, reroll_dice, cancel_dice, add_dice_to_roll
from profiles import red_die_ship, blue_die_ship, ...  # for validation helpers
```
