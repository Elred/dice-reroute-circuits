# Project Structure

```
dice-reroute-circuits/
├── drc_stat_engine/
│   ├── stats/
│   │   ├── profiles.py   # Dice face definitions (probabilities + attributes per face)
│   │   ├── dice.py       # Core logic: combine, reroll, cancel, filter, analyze rolls
│   │   └── report.py     # Report generation and strategy pipeline
│   └── tests/
│       └── dice_stat_report/    # Test scripts for the dice_stat_report spec
├── drc_front/
├── requirements.txt
└── README.md
```

## Conventions

- `profiles.py` defines raw dice data as lists of dicts with keys: `value`, `proba`, `damage`, `crit`, `acc`, `blank`
- Die face value strings use color prefix + face name: `R_hit`, `U_crit`, `B_blank`, `R_hit+hit`, etc.
- All Python files use absolute package imports: `from drc_stat_engine.stats.profiles import ...`
- `drc_stat_engine` is installed as an editable package — run `pip install -e .` from the project root once
- Roll state is always a pandas DataFrame with columns: `value`, `proba`, `damage`, `crit`, `acc`, `blank`
- `value` column is a space-separated sorted string of individual die face results (e.g. `"B_hit R_blank U_acc"`)
- Probabilities in a roll DataFrame should always sum to 1.0
- New dice operations should accept and return a roll DataFrame to stay composable
