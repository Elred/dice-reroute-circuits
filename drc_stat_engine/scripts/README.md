# Defense Impact Study Script

Compares how different defense tokens and abilities affect the total damage output of a series of attacks. Uses exact combinatorial math (no randomness) to produce precise probability distributions and quantile statistics.

## Quick Start

```bash
source ~/.virtualenvs/drc/bin/activate
python -m drc_stat_engine.scripts.defense_study drc_stat_engine/scripts/example_study.yaml output.csv
```

## Input Format (YAML)

Each attack carries its own attack effects and defense effects. Total damage is the sum across all attacks.

```yaml
name: "My Study"

attacks:
  - label: "Front arc"
    pool: { red: 2, blue: 1, black: 0, type: ship }
    strategy: max_damage
    attack_effects:
      - { type: reroll, count: 2, applicable_results: [R_blank] }
    defense_effects:
      - { type: divide_damage }

  - label: "Side arc"
    pool: { red: 1, blue: 0, black: 1, type: ship }
    strategy: max_damage
    attack_effects: []
    defense_effects:
      - { type: defense_cancel, count: 1 }
```

### Attack Fields

| Field | Required | Description |
|-------|----------|-------------|
| `label` | yes | Human-readable name |
| `pool` | yes | `red`, `blue`, `black` counts + `type` (ship/squad). Max 3 dice total. |
| `strategy` | no | Default: `max_damage`. Options: `max_damage`, `balanced`, `black_doubles`, `max_accuracy_blue` |
| `attack_effects` | no | Attacker's effects (see below). Default: none |
| `defense_effects` | no | Defender's effects (see below). Default: none |

### Attack Effects

| Type | Fields | Example |
|------|--------|---------|
| `reroll` | `count`, `applicable_results` | `{ type: reroll, count: 2, applicable_results: [R_blank] }` |
| `cancel` | `count`, `applicable_results` | `{ type: cancel, count: 1, applicable_results: [R_blank, U_acc] }` |
| `add_dice` | `dice_to_add` | `{ type: add_dice, dice_to_add: { red: 0, blue: 0, black: 1 } }` |
| `change_die` | `applicable_results`, `target_result` | `{ type: change_die, applicable_results: [R_blank], target_result: hit }` |
| `add_set_die` | `target_result` | `{ type: add_set_die, target_result: B_hit+crit }` |

### Defense Effects

| Type | Fields | Example |
|------|--------|---------|
| `divide_damage` | (none) | `{ type: divide_damage }` — Brace: halve damage (round up) |
| `reduce_damage` | `amount` | `{ type: reduce_damage, amount: 2 }` — Reduce by flat N |
| `defense_cancel` | `count` | `{ type: defense_cancel, count: 1 }` — Evade: cancel N dice |
| `defense_reroll` | `count`, `mode` | `{ type: defense_reroll, count: 1, mode: safe }` — Reroll N dice |

Defense reroll modes: `safe` (no risk of blank) or `gamble` (riskier, more targets).

## Output Format (CSV)

One row per attack. Total stats (sum across all attacks) are repeated on each row for easy pivoting.

| Column | Description |
|--------|-------------|
| `total_avg` | Average total damage across all attacks |
| `total_p5` | 5th percentile total (very unlucky) |
| `total_p20` | 20th percentile total (unlucky) |
| `total_p50` | Median total damage |
| `total_p80` | 80th percentile total (lucky) |
| `total_p95` | 95th percentile total (very lucky) |
| `total_p_zero` | Probability of zero total damage |
| `attack` | Individual attack label |
| `attack_avg` through `attack_p95` | Per-attack quantiles |
| `attack_p_zero` | Probability this attack does zero damage |

## Reading the Quantiles

- **P20** = "unlucky": 80% of the time you do at least this much
- **P50** = median: half the time you do this much or more
- **P80** = "lucky": only 20% of the time you do this much or more
- **P5/P95** = extreme scenarios

## Comparing Scenarios

To compare defense strategies, create multiple YAML files (or duplicate attacks with different defense_effects) and run the script on each. Paste the CSVs side by side in Google Sheets.

## Limitations

- Pool size limited to 3 dice per attack (combinatorial backend)
- Attack effects must use supported types: `reroll`, `cancel`, `add_dice`, `change_die`, `add_set_die`
