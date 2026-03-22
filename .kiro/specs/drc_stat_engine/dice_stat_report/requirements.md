# Requirements Document

## Introduction

The dice stats report feature enables players to generate a comprehensive probability report for a given dice pool and sequence of dice operations. The report shows the cumulative probability distribution for damage and accuracy outcomes, the probability of rolling at least one crit, and strategy recommendations for operations that depend on reroll/cancel priorities (e.g. maximizing damage vs. accuracy vs. crits).

## Glossary

- **Dice_Pool**: A collection of dice defined by counts of Red (R), Blue (U), and Black (B) dice and a type (ship or squad).
- **Operation**: A transformation applied to a roll DataFrame — e.g. reroll, cancel, add dice. Each operation defines an `applicable_results` whitelist and a resolved `priority_list`.
- **Applicable_Results**: The user-defined whitelist of die face values an operation is allowed to target. Validated against the pool's color/type profile. Never modified by strategy resolution.
- **Priority_List**: The resolved ordered list of face values passed to the underlying dice function at execution time. Derived by filtering the Strategy's full ordering to only faces present in `applicable_results`.
- **Strategy**: A named optimization goal — one of `max_damage`, `max_doubles`, `max_accuracy`, or `max_crits` — that defines a full face ordering used to resolve `Priority_List` for priority-dependent operations. A strategy is always required; the default is `max_damage`.
- **Roll_DataFrame**: A pandas DataFrame with columns `value`, `proba`, `damage`, `crit`, `acc`, `blank` representing the full probability distribution of a roll state.
- **Report**: The final output produced by the Report_Generator for a given Dice_Pool, operation sequence, and set of Strategies.
- **Cumulative_Probability**: The probability of achieving at least X of a given outcome (damage, accuracy, or crits).
- **Report_Generator**: The system component responsible for computing and formatting the Report.
- **Operation_Pipeline**: The ordered sequence of Operations applied to the initial Roll_DataFrame.

---

## Requirements

### Requirement 1: Dice Pool Specification

**User Story:** As a player, I want to specify a dice pool by color and type, so that the report reflects the correct starting distribution.

#### Acceptance Criteria

1. THE Report_Generator SHALL accept a Dice_Pool defined by non-negative integer counts of Red, Blue, and Black dice and a type of either `ship` or `squad`.
2. IF the Dice_Pool contains zero dice of all colors, THEN THE Report_Generator SHALL return an error indicating the pool is empty.
3. IF a dice count is negative or a non-integer value is provided, THEN THE Report_Generator SHALL return an error indicating invalid input.
4. IF the type is not `ship` or `squad`, THEN THE Report_Generator SHALL return an error indicating an unsupported dice type.

---

### Requirement 2: Operation Pipeline Specification

**User Story:** As a player, I want to specify an ordered sequence of dice operations, so that the report reflects the outcome after all game mechanics are applied.

#### Acceptance Criteria

1. THE Report_Generator SHALL accept an Operation_Pipeline as an ordered list of Operations to apply sequentially to the Roll_DataFrame.
2. WHEN an Operation is priority-dependent (reroll, cancel), THE Report_Generator SHALL accept an `applicable_results` list as part of that Operation's configuration, defining which face values the operation is allowed to target.
3. IF an Operation's `applicable_results` contains face values not present in the current roll, those faces are silently ignored — the operation acts only on faces that actually appear in the roll. No error is raised.
4. IF the Operation_Pipeline is empty, THE Report_Generator SHALL produce a Report based on the raw initial roll with no operations applied.
5. THE Report_Generator SHALL support the following Operation types: `reroll`, `cancel`, `add_dice`.

---

### Requirement 3: Cumulative Damage Probability

**User Story:** As a player, I want to see the probability of dealing at least X damage for every possible damage value, so that I can evaluate the offensive output of my dice pool.

#### Acceptance Criteria

1. THE Report_Generator SHALL compute, for each integer damage value from 0 to the maximum possible damage in the Roll_DataFrame, the Cumulative_Probability of achieving at least that damage value.
2. THE Report_Generator SHALL include all damage values in the range even if their exact probability is 0.
3. WHEN the Cumulative_Probability for a damage value is computed, THE Report_Generator SHALL sum the probabilities of all Roll_DataFrame rows where `damage >= X`.

---

### Requirement 4: Cumulative Accuracy Probability

**User Story:** As a player, I want to see the probability of rolling at least X accuracy for every possible accuracy value, so that I can evaluate how reliably I can lock down enemy ships.

#### Acceptance Criteria

1. THE Report_Generator SHALL compute, for each integer accuracy value from 0 to the maximum possible accuracy in the Roll_DataFrame, the Cumulative_Probability of achieving at least that accuracy value.
2. THE Report_Generator SHALL include all accuracy values in the range even if their exact probability is 0.
3. WHEN the Cumulative_Probability for an accuracy value is computed, THE Report_Generator SHALL sum the probabilities of all Roll_DataFrame rows where `acc >= X`.

---

### Requirement 5: Crit Probability

**User Story:** As a player, I want to see the probability of rolling at least one crit, so that I can assess the likelihood of triggering crit-dependent upgrade effects.

#### Acceptance Criteria

1. THE Report_Generator SHALL compute the probability of rolling at least 1 crit by summing the probabilities of all Roll_DataFrame rows where `crit >= 1`.
2. THE Report_Generator SHALL include this value as a single named entry in the Report.

---

### Requirement 6: Strategy-Based Report Variants

**User Story:** As a player, I want to see separate report variants for each optimization strategy (max damage, max accuracy, max crits), so that I can compare the trade-offs of different reroll/cancel priorities.

#### Acceptance Criteria

1. THE Report_Generator SHALL always produce one Report variant per requested Strategy. A strategy is always required; the default is `max_damage`.
2. WHEN computing the `max_damage` Strategy variant, THE Report_Generator SHALL use a Priority_List that prioritizes rerolling/cancelling blanks first, then accuracy faces (blue before red), keeping hits, crits, and multi-damage faces unconditionally.
3. WHEN computing the `max_doubles` Strategy variant, THE Report_Generator SHALL use a Priority_List that prioritizes rerolling/cancelling blanks, then accuracy faces, then single hits, then single crits, keeping double-damage faces (`R_hit+hit`, `B_hit+crit`) unconditionally.
4. WHEN computing the `max_accuracy` Strategy variant, THE Report_Generator SHALL use a Priority_List that prioritizes rerolling/cancelling blanks, then blue hits/crits, then red hits/crits, keeping accuracy faces and all black faces unconditionally.
5. WHEN computing the `max_crits` Strategy variant, THE Report_Generator SHALL use a Priority_List that prioritizes rerolling/cancelling blanks, then accuracy faces, then single hits, keeping crit faces and multi-damage faces unconditionally.
6. THE Report_Generator SHALL resolve the effective Priority_List for each priority-dependent Operation by filtering the Strategy's full face ordering to only the faces present in that Operation's `applicable_results`. The `applicable_results` field is never modified.
7. THE Report_Generator SHALL label each Report variant clearly with its Strategy name in the output.

---

### Requirement 7: Report Output Format

**User Story:** As a player, I want the report to be printed in a clear, readable format, so that I can quickly interpret the probability distributions.

#### Acceptance Criteria

1. THE Report_Generator SHALL output the Report as formatted text to standard output.
2. THE Report_Generator SHALL display the Dice_Pool composition (counts per color and type) in the Report header.
3. THE Report_Generator SHALL display the cumulative damage probability table with one row per damage value, showing the damage threshold and its Cumulative_Probability as a percentage rounded to 2 decimal places.
4. THE Report_Generator SHALL display the cumulative accuracy probability table with one row per accuracy value, showing the accuracy threshold and its Cumulative_Probability as a percentage rounded to 2 decimal places.
5. THE Report_Generator SHALL display the crit probability as a single percentage value rounded to 2 decimal places.
6. WHERE Strategy variants are present, THE Report_Generator SHALL display each variant in a clearly separated section labeled with the Strategy name.
7. THE Report_Generator SHALL display the applied Operation_Pipeline in the Report header so the user can verify the scenario.

---

### Requirement 8: Round-Trip Probability Integrity

**User Story:** As a developer, I want the probabilities in the Roll_DataFrame to always sum to 1.0 after each operation, so that the report values are statistically valid.

#### Acceptance Criteria

1. THE Report_Generator SHALL verify that the probabilities in the Roll_DataFrame sum to 1.0 (within a tolerance of 1e-9) after each Operation in the Operation_Pipeline is applied.
2. IF the probability sum deviates from 1.0 beyond the tolerance after any Operation, THEN THE Report_Generator SHALL raise an error identifying which Operation caused the deviation.
