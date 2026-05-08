### Joint Cumulative Probability Display
- Click any bar in the damage or accuracy chart to see joint probabilities in the opposite chart
- Clicking a damage bar shows "Cumulative Accuracy for damage ≥ X" in the accuracy chart area
- Clicking an accuracy bar shows "Cumulative Damage for acc ≥ Y" in the damage chart area
- Close button (✕) on the top-right of the joint chart to return to normal view
- Clicking the anchor bar also returns to normal view

### Shareable Report URLs
- Report configurations encoded in URL query parameters for sharing
- Multiple reports supported via repeated `r` params
- Reports restored on page load from URL

### Load Config from Report
- New ⇐ button on each report card to load its configuration into the left panel
- Sets dice pool, attack effects, defense effects, strategy, and precision
- Useful for tweaking an existing setup or restoring from a shared URL

### UI Improvements
- Bar labels now include dimension prefix: P(dmg=0), P(dmg≥1), P(acc=0), P(acc≥1)
- Color legend removed from single-dataset charts (redundant with labeled bars)
- Hover highlight with opposite-dimension border color (blue on damage bars, gold on accuracy bars)
- Gold border on hover for dismiss and load-config buttons
- "Add at least one die" error hidden when results are already displayed (e.g. from shared URL)
- Cancel attack effect now defaults to all applicable results selected

---

## 0.2.2

### Bug Fixes
- Fix cancel operation bug causing dice results to disappear

---

## 0.2.1

### Bug Fixes
- Fix halve/reduce defense priority ordering

---

## 0.2.0

### Defense Effects
- New defense pipeline: model what happens after the attacker rolls
- Defensive reroll with two modes: Safe (no risk of worsening the roll) and Gamble (risking the double)
- Defensive cancel 
- Reduce damage: subtract a flat amount from total damage
- Halve damage: divide total damage by two, rounded up (brace token)
- Ship and squadron dice use different defense priority lists (squad crits are ignored)
- Pre-defense and post-defense damage charts overlaid on the same graph (how much does PDIC actually hurt you)
- Post-defense average damage and crit % displayed below pre-defense stats

### Conditional Reroll All
- New "reroll_all" attack effect: reroll all dice when a condition is met (Veteran Gunners)
- Conditions based on roll attributes (damage, crit, acc, blank) with comparison operators

### Add+Set Die
- New "add_set_die" attack effect: add a die locked to a specific face value (Plo Koon, etc)
- Conditional add_set_die: only triggers when a specific face is present in the roll (Quad Turbolaser Cannons)
- Color-in-pool dynamic die addition: add a die matching a color already in the pool (Concentrate Fire dial and other effects)

### UI Improvements
- Attack pipeline and strategy selector merged into a single card
- Dice pool buttons renamed to "Ship" and "Squadron"
- Bomber mode for Squadron dice (cleaner UX)
- Pool summary shows "Ship", "Squadron", or "Bomber" label
- Defense pipeline card with green accent theme
- Info panel on defense reroll modes explaining Safe vs Gamble strategies
- Colored borders on dice pool, attack, and defense cards
- Striped pattern on =0 damage/accuracy bars to distinguish them
- Dismiss button on result cards to clear individual results
- Changelog modal accessible from the header
