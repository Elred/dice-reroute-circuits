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

## Package Setup

`drc_stat_engine` is installed as an editable package into the virtualenv. This enables clean absolute imports everywhere:

```python
from drc_stat_engine.stats.report import generate_report, DicePool, Operation
from drc_stat_engine.stats.profiles import red_die_ship
```

The project root contains a `pyproject.toml` that declares the package. Install once after cloning:

```bash
source ~/.virtualenvs/drc/bin/activate
pip install -e .
```

All source files use absolute imports — bare relative imports (`from profiles import ...`) are not used.

## Running

Stats scripts are run as modules from the project root:
```bash
python -m drc_stat_engine.stats.dice
python -m drc_stat_engine.stats.report
```

The Flask API is run from the `drc_stat_engine/api/` directory:
```bash
cd drc_stat_engine/api
python app.py
```

## Virtualenv

Before running any Python commands, always activate the project virtualenv:
```
source ~/.virtualenvs/drc/bin/activate
```
