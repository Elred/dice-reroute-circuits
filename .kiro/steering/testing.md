# Testing & Python Execution Rules

## Interpreter setup

- Before running any python, activate the drc virtualenvironment:
```
source ~/.virtualenvs/drc/bin/activate
```

## Terminal Python Commands

- Only run **one-liners** directly in the terminal after an import, e.g.:
  ```
  python -c "import sys; sys.path.insert(0, 'stats'); from dice import combine_dice; print(combine_dice(1,0,0,'ship').shape)"
  ```
- Never run multi-line scripts inline in the terminal.

## Test Scripts

- For anything beyond a one-liner, **create a test script** following the naming convention `test_{spec_name}_{feature}.py` where `{feature}` is a short human-readable name for what is being tested (e.g. `test_dice_stats_report_validation.py`, `test_dice_stats_report_pipeline.py`). Use underscores only — hyphens and dots in filenames break Python's module import system.
- Do not use task numbers in test file names — use descriptive names that reflect the functionality being tested.
- Place test scripts in the `tests/{spec-name}/` directory at the project root.
- Keep test scripts — they are archived and used for regression testing.

### Current test files for `dice-stats-report`

| File | What it tests |
|------|---------------|
| `test_dice_stats_report_t1_validation.py` | `DicePool`, `Operation` dataclasses, `validate_dice_pool`, `validate_operation_pipeline` |
| `test_dice_stats_report_t2_pipeline.py` | `apply_operation`, `run_pipeline`, probability integrity property tests |
| `test_dice_stats_report_t3_cumulative_proba.py` | `cumulative_damage`, `cumulative_accuracy`, `crit_probability` |
| `test_dice_stats_report_t4_checkpoint.py` | Runs all of the above as a full regression suite |
| `test_dice_stats_report_t5_strategy.py` | `STRATEGY_PRIORITY_LISTS`, `build_strategy_pipeline`, `generate_report` |

## Running Test Scripts and Reading Output

The terminal environment does not reliably surface stdout. **Always redirect output to a file in the workspace and read it with the file tool.**

Step 1 — run via `controlBashProcess`, redirecting output (run from project root):
```
/home/elred/.virtualenvs/drc/bin/python tests/dice-stats-report/test_dice_stats_report_t2_pipeline.py > tests/dice-stats-report/out.txt 2>&1; echo "EXIT:$?" >> tests/dice-stats-report/out.txt
```

Step 2 — read the result with `readFile`:
```
tests/dice-stats-report/out.txt
```

Step 3 — delete the output file after reading it (it's ephemeral; the test script itself is kept).

Step 4 — stop the background process with `controlBashProcess` action `stop` once you have read the output.

**Never** rely on `getProcessOutput` or direct terminal stdout — they are unreliable in this environment.

## Test Script Conventions

- Each test script should print a clear PASS/FAIL result per case.
- Use `assert` statements with descriptive messages.
- Wrap in a `try/except` to catch unexpected errors and print them clearly.
- Example structure:
  ```python
  import sys
  sys.path.insert(0, '.')

  from report import validate_dice_pool, DicePool

  try:
      validate_dice_pool(DicePool(red=0, blue=0, black=0, type="ship"))
      print("FAIL: expected ValueError for empty pool")
  except ValueError as e:
      print(f"PASS: {e}")
  ```
