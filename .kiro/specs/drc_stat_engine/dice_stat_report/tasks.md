# Implementation Plan: Dice Stats Report

## Overview

Build a `ReportGenerator` class in `drc_stat_engine/stats/report.py` that accepts a dice pool, an operation pipeline, and optional strategies, then computes and prints cumulative probability distributions for damage, accuracy, and crits.

## Tasks

- [x] 1. Create `drc_stat_engine/stats/report.py` with core data structures and input validation
  - Define `DicePool` dataclass (red, blue, black counts + type)
  - Define `Operation` dataclass (type, count, priority_list)
  - Implement `validate_dice_pool()` — reject empty pools, negative counts, invalid types
  - Implement `validate_operation_pipeline()` — reject unknown face values for the pool's color/type profile
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.3, 2.5_

- [-] 2. Implement the operation pipeline executor
  - [x] 2.1 Implement `apply_operation(roll_df, operation, type_str)` dispatching to existing `reroll_dice`, `cancel_dice`, `add_dice_to_roll`
    - Map `reroll` → `reroll_dice`, `cancel` → `cancel_dice`, `add_dice` → `add_dice_to_roll`
    - _Requirements: 2.1, 2.2, 2.5_

  - [x] 2.2 Implement probability integrity check after each operation
    - After each `apply_operation` call, assert `roll_df["proba"].sum()` is within 1e-9 of 1.0
    - Raise a descriptive error identifying the offending operation if the check fails
    - _Requirements: 8.1, 8.2_

  - [x] 2.3 Write property test for probability integrity
    - **Property: After any single operation applied to a valid roll_df, probabilities sum to 1.0 within 1e-9**
    - **Validates: Requirements 8.1**

  - [x] 2.4 Implement `run_pipeline(roll_df, pipeline, type_str)` applying all operations in order with integrity checks
    - Return the final roll_df; if pipeline is empty return the initial roll_df unchanged
    - _Requirements: 2.1, 2.4, 8.1_

- [x] 3. Implement cumulative probability computations
  - [x] 3.1 Implement `cumulative_damage(roll_df)` returning a list of `(damage_threshold, probability)` tuples
    - Cover all integer values from 0 to max damage inclusive, even if probability is 0
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 3.2 Write property test for cumulative damage
    - **Property: cumulative_damage(roll_df)[0] always equals (0, 1.0) since P(damage >= 0) = 1**
    - **Validates: Requirements 3.1, 3.3**

  - [x] 3.3 Implement `cumulative_accuracy(roll_df)` returning a list of `(acc_threshold, probability)` tuples
    - Cover all integer values from 0 to max acc inclusive
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 3.4 Implement `crit_probability(roll_df)` returning the probability of `crit >= 1`
    - _Requirements: 5.1, 5.2_

- [x] 4. Checkpoint — verify core computations
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement strategy-based report variants
  - [x] 5.1 Define priority lists for each strategy per dice type
    - `max_damage`: blanks first (blue acc before red acc), then acc; hits/crits/doubles kept unconditionally
    - `max_doubles`: blanks → acc → single hits → single crits; double-damage faces kept unconditionally
    - `max_accuracy`: blanks → blue hits/crits → red hits/crits; acc and all black faces kept unconditionally
    - `max_crits`: blanks → acc → single hits; crit faces and doubles kept unconditionally
    - Cover both `ship` and `squad` profiles
    - _Requirements: 6.2, 6.3, 6.4, 6.5_

  - [x] 5.2 Implement `build_strategy_pipeline(pipeline, strategy, type_str)` that substitutes priority lists into priority-dependent operations
    - Detect whether any operation in the pipeline is priority-dependent (`reroll`, `cancel`)
    - _Requirements: 6.1, 6.5_

  - [x] 5.3 Implement `generate_report(dice_pool, pipeline, strategies)` orchestrating all variants
    - If pipeline has no priority-dependent ops, run once with no strategy label
    - Otherwise run once per requested strategy, labeling each variant
    - _Requirements: 6.1, 6.5, 6.6_

- [x] 6. Implement report output formatting
  - [x] 6.1 Implement `format_report(dice_pool, pipeline, variants)` producing formatted text output
    - Header: dice pool composition and applied operation pipeline
    - Cumulative damage table: one row per threshold, probability as `XX.X%`
    - Cumulative accuracy table: same format
    - Crit probability: single `XX.X%` line
    - Multiple strategy variants in clearly separated labeled sections
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [x] 6.2 Write unit tests for format_report output
    - Test that header contains dice pool counts and type
    - Test that damage table rows are formatted to 1 decimal place
    - Test that strategy sections are labeled correctly
    - _Requirements: 7.2, 7.3, 7.6_

- [x] 7. Wire everything together and add CLI entry point
  - [x] 7.1 Add a `main()` function in `stats/report.py` with a sample scenario demonstrating the full pipeline
    - Instantiate a `DicePool`, define an `Operation_Pipeline`, call `generate_report`, print output
    - _Requirements: 7.1, 2.1, 3.1, 4.1, 5.1_

  - [x] 7.2 Verify `report.py` runs standalone from the `drc_stat_engine/stats/` directory (`python report.py`)
    - Confirm imports from `profiles` and `dice` resolve correctly
    - _Requirements: 7.1_

- [x] 8. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- `report.py` imports from `profiles` and `dice` — run from `drc_stat_engine/stats/` directory like existing scripts
- Strategy priority lists must be defined per dice type (`ship` vs `squad`) since face values differ
- Test scripts live in `drc_stat_engine/tests/dice_stat_report/`
