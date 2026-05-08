
**Dice Reroute Circuits (DRC)** is a probability analysis tool for the *Star Wars: Armada* tabletop miniatures game. It models attack dice roll outcomes and computes statistics — average damage, probability distributions, crit chances — for any attack scenario you configure.

Use it to evaluate fleet builds, compare upgrade combinations, and understand how the odds behind your attack rolls actually work.

## Basic Usage

1. **Configure your dice pool** — select the number of Red, Blue, and Black dice and choose Ship or Squadron type.
2. **Add attack effects** — optionally add reroll, cancel, add dice, or change die effects to your pipeline.
3. **Select strategies** — choose one strategy for picking which dice to reroll, cancel, or change when given a choice.
4. **Calculate** — the engine computes probability distributions and statistics for each selected strategy.

**Note**: Currently, this tool use either combinatories or Monte Carlo simulation to produce results. This means that for large dice pools & attack effects stacks (anything over 8 dice total, or with enough dice and rerolls that combinatories get very heavy), the result will not be exact probabilities, but approximated over 100 thousand simulated rolls.

(yes, DRC is just brute forcing maths in various ways)

Dice limit of initial pool + add effects is 20. Until such times one can do better than the 18 dice from a Kuat with External Racks, Concentrate Fire dial, Romodi, Devastator and Opening Salvo, don't break my stuff.

---

## Attack Effects

Attack effects modify the dice pool during an attack. They are applied in pipeline order:

- **`reroll`** — pick up to N dice showing specific results and re-roll
- **`cancel`** — remove up to N dice showing specific results from the pool
- **`add die`** — add fresh dice of a given color to the pool
- **`change die`** — set a die showing the selected result to display a specific result (e.g. turn a blank into a hit)

**Notes:**
* Reroll and Change die effects will only occur on dice rolls where they are relevant to the selected strategy (for instance, a reroll effect on a pool that turned up all damage will never get rerolled in the current implementation)
* Cancel is currently considered mandatory and will always occur.

---

## Strategies

Strategies determine which dice are prioritized when applying reroll, cancel or change attack effects:

| Strategy | Dice Type | Description |
|----------|-----------|-------------|
| `max_damage` | Ship & Squad | Reroll blanks and accuracies to maximize total damage output |
| `balanced` | Ship & Squad | Reroll blanks only — keeps accuracies and damage results |
| `max_accuracy_blue` | Ship & Squad | Reroll blue hits and crits to fish for accuracy results |
| `black_doubles` | Ship only | Reroll blanks and black hits to maximize double-damage results |

**Note:** This is currently work in progress and might be working differently in the future.

---

## Output Statistics

For each strategy variant, DRC reports:

- **Cumulative damage distribution** — P(damage ≥ x) for each integer threshold
- **Cumulative accuracy distribution** — P(acc ≥ x) for each integer threshold
- For both cumulative distribution, clicking the graph show the cumulated distribution of the other metric (ex P(damage = 5 AND acc ≥ x))
- **Crit probability** — P(crit ≥ 1)
- **Average damage** — E[damage]

# Future ideas

This will probably make it in the tool at some point.

* **Cover all existing content**: The tools covers most dice manipulation effects, but some are missing, or the logic to apply them or not is not refined enough.
* **Custom strategy**: Currently I have a few presets defined, but user should be able to set their own.
* **Defense tokens**: Improve defense effects setting up to better reflect in game mechanics. (such as disabling effects when accuracies are present)
* **Conditional effect strategy**: For example, set a desired amount of accuracy to ignore rerolls or change effects on dice rolls that already fit the requirements
* **Comparison between reports**: Make it easier to visualize the difference between 2 setups
* **Upgrade picker**: Not yet sure how to make it easy to navigate, but eventually I'd like to make it possible to select upgrades directly

# Contact and info

* If finding any bug or otherwise strange behaviours on the current features, please contact me at dicereroutecircuits+support@gmail.com    
Elred

*This project is a fan-made creation and is not officially associated with Star Wars: Armada or its publishers.*