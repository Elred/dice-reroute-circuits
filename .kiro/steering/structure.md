# Project Structure

```
dice-reroute-circuits/
├── stats/
│   ├── profiles.py   # Dice face definitions (probabilities + attributes per face)
│   └── dice.py       # Core logic: combine, reroll, cancel, filter, analyze rolls
├── docs/             # Empty — intended for documentation
├── requirements.txt
└── README.md
```

## Conventions

- `profiles.py` defines raw dice data as lists of dicts with keys: `value`, `proba`, `damage`, `crit`, `acc`, `blank`
- Die face value strings use color prefix + face name: `R_hit`, `U_crit`, `B_blank`, `R_hit+hit`, etc.
- `dice.py` imports directly from `profiles` (no package — run from `stats/` directory)
- Roll state is always a pandas DataFrame with columns: `value`, `proba`, `damage`, `crit`, `acc`, `blank`
- `value` column is a space-separated sorted string of individual die face results (e.g. `"B_hit R_blank U_acc"`)
- Probabilities in a roll DataFrame should always sum to 1.0
- New dice operations should accept and return a roll DataFrame to stay composable
