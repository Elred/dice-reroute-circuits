# dice-reroute-circuits

A probability analysis tool for Star Wars Armada. It computes statistics for attack scenarios — average damage, probability distributions, crit chances — so you can evaluate fleet builds and upgrade combinations and understand expectations or how likely you were to full blank out that one shot.

---

## How the stats engine works

### Dice and faces

Each die has a color (Red, Blue, Black) and a type (ship or squad). Rolling a die produces one of several possible faces, each with a fixed probability:

**Red ship die**
| Face      | Probability | Damage | Crit | Acc |
|-----------|-------------|--------|------|-----|
| Blank     | 25%         | 0      | —    | —   |
| Hit       | 25%         | 1      | —    | —   |
| Crit      | 25%         | 1      | ✓    | —   |
| Accuracy  | 12.5%       | 0      | —    | ✓   |
| Hit+Hit   | 12.5%       | 2      | —    | —   |

**Blue ship die**
| Face      | Probability | Damage | Crit | Acc |
|-----------|-------------|--------|------|-----|
| Hit       | 50%         | 1      | —    | —   |
| Crit      | 25%         | 1      | ✓    | —   |
| Accuracy  | 25%         | 0      | —    | ✓   |

**Black ship die**
| Face      | Probability | Damage | Crit | Acc |
|-----------|-------------|--------|------|-----|
| Blank     | 25%         | 0      | —    | —   |
| Hit       | 50%         | 1      | —    | —   |
| Hit+Crit  | 25%         | 2      | ✓    | —   |

Squad dice use the same colors but different face values (crits are worthless for squads, for example).

---

### The combinatorial engine

When you roll multiple dice, the engine needs to know the probability of every possible combined outcome — e.g. "what's the chance of rolling exactly 3 damage from 2 red + 1 black?"

The **combinatorial engine** answers this by computing the exact joint distribution. It takes every possible face from die A and pairs it with every possible face from die B, multiplying their probabilities. For 2 dice with 5 faces each, that's 25 combinations. For 3 dice it's 125. For 10 dice it's in the millions — and many of those rows are duplicates that need to be collapsed.

This is precise but hits a wall around 10+ dice: the intermediate tables grow exponentially and the computation becomes too slow.

---

### The Monte Carlo engine

The **Monte Carlo engine** takes a different approach: instead of computing every possible outcome mathematically, it just *simulates* a large number of rolls.

Concretely: roll the dice 10,000 times (virtually), record what came up each time, then count how often each outcome occurred. If "3 damage" appeared in 2,847 of the 10,000 trials, the engine reports P(damage = 3) ≈ 28.47%.

This is an approximation — the more trials you run, the closer it gets to the true probability. At 10,000 samples the results are accurate enough for practical use (within ~0.05 of the exact value for most statistics). Crucially, the cost scales linearly with the number of dice, not exponentially, so a 15-die pool is no harder than a 3-die pool.

The engine uses numpy's vectorized random sampling to run all 10,000 trials simultaneously rather than one at a time, keeping it fast.

---

### Auto backend selection

The engine picks the right approach automatically:

- **Pool size ≤ 8 dice** → combinatorial (exact results)
- **Pool size > 8 dice** → Monte Carlo (fast approximation)

You can also force a specific backend explicitly if needed.

---

### The pipeline

A roll doesn't happen in isolation. Upgrades and abilities modify the dice after the initial roll. The engine models this as an ordered **pipeline** of operations applied to the distribution:

- **reroll** — pick up to N dice showing specific faces and re-roll them (e.g. reroll up to 2 blanks)
- **cancel** — remove up to N dice showing specific faces from the pool (e.g. an opponent cancels your accuracy)
- **add_dice** — add fresh dice of a given color to the pool (e.g. Gunnery Team adds a die)
- **change_die** — force one die to show a specific face (e.g. a concentrate fire command)

Each operation takes the current probability distribution and returns a new one. The pipeline runs them in sequence.

---

### Strategies

When you have a reroll or cancel operation, you need to decide *which* dice to target. A **strategy** defines the priority order — which faces to reroll first, which to cancel first — based on your goal:

- **max_damage** — reroll blanks and accuracy tokens, keep all damage faces
- **max_accuracy** — reroll blanks and non-blue damage faces, keep accuracy tokens
- **max_crits** — reroll blanks, accuracy tokens, and plain hits; keep crits
- **max_doubles** — reroll everything below double-damage faces (hit+hit, hit+crit)
- **balanced** — reroll blanks only, keep everything else

The engine runs the full pipeline once per strategy and reports results for each, so you can compare them side by side.

---

### Output statistics

For each strategy variant the engine reports:

- **Cumulative damage distribution** — P(damage ≥ x) for each integer threshold x
- **Cumulative accuracy distribution** — P(acc ≥ x) for each integer threshold x
- **Crit probability** — P(at least one crit)
- **Average damage** — expected damage across all outcomes
