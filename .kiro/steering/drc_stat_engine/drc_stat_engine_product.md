# Product

`dice-reroute-circuits` is a probability analysis tool for the Star Wars Armada tabletop game.

It models dice roll outcomes and computes statistics (average damage, probability distributions) for various attack scenarios. The tool supports ship and squadron dice pools, and simulates game mechanics like rerolls, cancels, and adding/removing dice — enabling players to evaluate the effectiveness of different fleet builds and upgrade combinations.

Key concepts:
- **Dice colors**: Red (R), Blue (U), Black (B) — each with distinct face distributions
- **Dice types**: Ship vs. Squad dice have different face values for the same color
- **Die faces**: blank, hit, crit, acc (accuracy), hit+hit, hit+crit
- **Roll operations**: combine pools, reroll, cancel, add/remove dice, filter by outcome
