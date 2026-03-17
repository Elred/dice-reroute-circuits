# Tech Stack

- **Language**: Python 3
- **Key libraries**:
  - `pandas` — dice roll combinations stored and manipulated as DataFrames
  - `numpy` — used for NaN handling and numeric operations

## Dependencies

Install via:
```
pip install -r requirements.txt
```

`requirements.txt` includes: `numpy`, `pandas`, `python-dateutil`, `pytz`, `six`

## Running

Scripts are run directly from the `stats/` directory (imports are relative):
```
cd stats
python dice.py
```

No build system, test framework, or package setup currently exists.

## Virtualenv

Before running any Python commands, always activate the project virtualenv:
```
source ~/.virtualenvs/drc/bin/activate
```
