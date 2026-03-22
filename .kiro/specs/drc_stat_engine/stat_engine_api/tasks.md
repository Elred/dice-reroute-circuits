# Tasks — Stat Engine API

## Task List

- [x] 1. Project setup
  - [x] 1.1 Add `pyproject.toml` at the project root declaring `drc_stat_engine` as an installable package
  - [x] 1.2 Run `pip install -e .` in the `drc` virtualenv to install the package in editable mode
  - [x] 1.3 Update imports in `drc_stat_engine/stats/dice.py` — replace bare `from profiles import ...` with `from drc_stat_engine.stats.profiles import ...`
  - [x] 1.4 Update imports in `drc_stat_engine/stats/report.py` — replace bare `from dice import ...` / `from profiles import ...` with absolute package imports
  - [x] 1.5 Verify existing tests still pass after import migration
  - [x] 1.6 Add `flask` and `flask-cors` to `requirements.txt`
  - [x] 1.7 Create `drc_stat_engine/api/` directory with empty `__init__.py`

- [x] 2. Flask app factory (`app.py`)
  - [x] 2.1 Implement `create_app()` with `sys.path` insert, CORS config, and blueprint registration
  - [x] 2.2 Add `if __name__ == "__main__"` block to run on port 5000

- [x] 3. Routes (`routes.py`)
  - [x] 3.1 Implement `parse_report_request(data)` — JSON → `DicePool` + `List[Operation]` + strategies
  - [x] 3.2 Implement `POST /api/v1/report` handler with full error handling (400 / 422 / 500)
  - [x] 3.3 Implement `GET /api/v1/meta` handler deriving all values from live imports

- [x] 4. Tests — meta endpoint
  - [x] 4.1 Create `drc_stat_engine/tests/stat_engine_api/test_stat_engine_api_t1_meta.py`
  - [x] 4.2 Verify response contains `dice_types`, `strategies`, `operation_types`, `face_values`
  - [x] 4.3 Verify `face_values` keys match actual profile face value strings

- [x] 5. Tests — report endpoint basic
  - [x] 5.1 Create `drc_stat_engine/tests/stat_engine_api/test_stat_engine_api_t2_report_basic.py`
  - [x] 5.2 Test single strategy request returns correct variant structure
  - [x] 5.3 Test multiple strategies request returns one variant per strategy
  - [x] 5.4 Test empty pipeline request returns same result as `generate_report(pool, [], strategies)`
  - [x] 5.5 Test `strategies` field omitted defaults to `max_damage`

- [x] 6. Tests — validation
  - [x] 6.1 Create `drc_stat_engine/tests/stat_engine_api/test_stat_engine_api_t3_validation.py`
  - [x] 6.2 Test empty dice pool → 422
  - [x] 6.3 Test invalid dice type → 422
  - [x] 6.4 Test negative dice count → 422
  - [x] 6.5 Test unknown operation type → 422
  - [x] 6.6 Test unknown strategy name → 422
  - [x] 6.7 Test malformed JSON body → 400

- [x] 7. Tests — property-based
  - [x] 7.1 Create `drc_stat_engine/tests/stat_engine_api/test_stat_engine_api_t4_properties.py`
  - [x] 7.2 PROP-1: round-trip — API response matches `generate_report()` output directly
  - [x] 7.3 PROP-2: all probability values in [0.0, 1.0]
  - [x] 7.4 PROP-3: cumulative damage and accuracy arrays are non-increasing
  - [x] 7.5 PROP-4: damage threshold array starts at 0 with no gaps
  - [x] 7.6 PROP-5: any input rejected by `validate_*` returns 4xx from the API
  - [x] 7.7 PROP-6: empty pipeline returns same stats as baseline `generate_report`
