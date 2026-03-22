# Product — drc_front

`drc_front` is the Vue.js single-page application (SPA) that provides a visual interface for the `drc_stat_engine` probability analysis tool.

## Purpose

Players of Star Wars Armada use this UI to:
- Configure a dice pool (Red / Blue / Black dice counts, ship or squad type)
- Build an operation pipeline (reroll, cancel, add dice — in any order)
- Select one or more strategies (max_damage, max_accuracy, max_crits, max_doubles)
- Instantly see probability charts and statistics for each strategy variant

## Target User

A Star Wars Armada player who wants to evaluate attack scenarios without writing code. The interface should feel intuitive to a non-technical user while exposing the full power of the stat engine.

## Key Concepts (from the game)

- **Dice colors**: Red (R), Blue (U), Black (B) — each has a distinct face distribution
- **Dice types**: Ship vs. Squad — same colors, different face values
- **Die faces**: blank, hit, crit, acc (accuracy), hit+hit, hit+crit
- **Operations**:
  - `reroll` — pick up to N dice showing specific faces and re-roll them
  - `cancel` — remove up to N dice showing specific faces from the pool
  - `add_dice` — add fresh dice of a given color to the pool
- **Strategies**: determine which faces are prioritized when rerolling or cancelling
  - `max_damage` — maximize total damage output
  - `max_accuracy` — maximize accuracy tokens
  - `max_crits` — maximize critical hits
  - `max_doubles` — maximize double-damage faces (hit+hit, hit+crit)

## Output Statistics

For each strategy variant the engine returns:
- Cumulative damage distribution: P(damage ≥ x) for each integer threshold
- Cumulative accuracy distribution: P(acc ≥ x) for each integer threshold
- Crit probability: P(crit ≥ 1)
- Average damage: E[damage]
