# Design — Stat Engine API

## Overview

A thin Flask wrapper around the existing `report.py` engine. The design principle is minimal surface area: route handlers translate JSON ↔ Python dataclasses and delegate all computation to the existing engine. No business logic lives in the API layer.

---

## File Structure

```
drc_stat_engine/
└── api/
    ├── app.py       # Flask app factory, CORS setup, blueprint registration
    └── routes.py    # Route handlers for /api/v1/report and /api/v1/meta
```

The `api/` directory is a sibling of `stats/`. Both import from `drc_stat_engine.stats` using absolute package imports — `drc_stat_engine` must be installed as an editable package (`pip install -e .`) before running.

---

## app.py

```python
from flask import Flask
from flask_cors import CORS
from drc_stat_engine.api.routes import api_bp

def create_app():
    app = Flask(__name__)
    CORS(app, origins=["http://localhost:5173"])
    app.register_blueprint(api_bp)
    return app

if __name__ == "__main__":
    create_app().run(port=5000, debug=True)
```

Key decisions:
- Clean absolute imports — no `sys.path` manipulation
- `drc_stat_engine` must be installed via `pip install -e .` before running
- CORS restricted to the Vite dev origin; production origin added later via config
- `debug=True` only in `__main__` block — never in production

---

## routes.py

### Blueprint

```python
from flask import Blueprint, request, jsonify
from drc_stat_engine.stats.report import (
    generate_report, validate_dice_pool, validate_operation_pipeline,
    DicePool, Operation, STRATEGY_PRIORITY_LISTS, VALID_OPERATION_TYPES,
)
from drc_stat_engine.stats.profiles import (
    red_die_ship, blue_die_ship, black_die_ship,
    red_die_squad, blue_die_squad, black_die_squad,
)
api_bp = Blueprint("api", __name__, url_prefix="/api/v1")
```

### POST /api/v1/report

**Flow:**

```
Request JSON
    │
    ▼
parse_report_request(data)
    │  builds DicePool + List[Operation]
    ▼
validate_dice_pool(pool)          ← raises ValueError → 422
validate_operation_pipeline(...)  ← raises ValueError → 422
    │
    ▼
generate_report(pool, pipeline, strategies)
    │
    ▼
serialize_variants(variants)
    │
    ▼
{"variants": [...]}
```

**Request parsing — `parse_report_request(data)`:**

```python
def parse_report_request(data: dict):
    dp = data["dice_pool"]
    pool = DicePool(
        red=dp.get("red", 0),
        blue=dp.get("blue", 0),
        black=dp.get("black", 0),
        type=dp.get("type", "ship"),
    )
    pipeline = []
    for op in data.get("pipeline", []):
        pipeline.append(Operation(
            type=op["type"],
            count=op.get("count", 1),
            applicable_results=op.get("applicable_results", []),
            dice_to_add=op.get("dice_to_add"),
        ))
    strategies = data.get("strategies", ["max_damage"])
    return pool, pipeline, strategies
```

**Error handling:**

| Condition | HTTP status | Body |
|---|---|---|
| Body not JSON | 400 | `{"error": "Invalid JSON"}` |
| Missing required key | 400 | `{"error": "Missing field: <key>"}` |
| `validate_dice_pool` raises `ValueError` | 422 | `{"error": "<message>"}` |
| `validate_operation_pipeline` raises `ValueError` | 422 | `{"error": "<message>"}` |
| `generate_report` raises `ValueError` (bad strategy) | 422 | `{"error": "<message>"}` |
| Any other exception | 500 | `{"error": "Internal server error"}` |

**Response serialization:**

`generate_report` returns a list of variant dicts. The route serializes them directly — the structure already matches the API contract (label, avg_damage, crit, damage list, accuracy list).

```python
return jsonify({"variants": variants}), 200
```

---

### GET /api/v1/meta

Derives all metadata from live imports — never hardcoded.

```python
from drc_stat_engine.stats.profiles import (
    red_die_ship, blue_die_ship, black_die_ship,
    red_die_squad, blue_die_squad, black_die_squad,
)
from drc_stat_engine.stats.report import STRATEGY_PRIORITY_LISTS, VALID_OPERATION_TYPES

@api_bp.route("/meta", methods=["GET"])
def meta():
    face_values = {
        "ship": {
            "red":   [f["value"] for f in red_die_ship],
            "blue":  [f["value"] for f in blue_die_ship],
            "black": [f["value"] for f in black_die_ship],
        },
        "squad": {
            "red":   [f["value"] for f in red_die_squad],
            "blue":  [f["value"] for f in blue_die_squad],
            "black": [f["value"] for f in black_die_squad],
        },
    }
    return jsonify({
        "dice_types": ["ship", "squad"],
        "strategies": {k: list(v.keys()) for k, v in STRATEGY_PRIORITY_LISTS.items()},
        "operation_types": sorted(VALID_OPERATION_TYPES),
        "face_values": face_values,
    }), 200
```

---

## Error Handler Registration

Global handlers registered on the app (not the blueprint) to catch unhandled exceptions:

```python
@app.errorhandler(Exception)
def handle_unexpected(e):
    app.logger.exception("Unhandled exception")
    return jsonify({"error": "Internal server error"}), 500
```

---

## Data Flow Diagram

```
Vue front-end
    │  POST /api/v1/report  (JSON)
    ▼
routes.py — parse_report_request()
    │
    ▼
report.py — validate_dice_pool()
report.py — validate_operation_pipeline()
report.py — generate_report()
    │  returns List[variant dict]
    ▼
routes.py — jsonify({"variants": [...]})
    │
    ▼
Vue front-end  (JSON response)
```

---

## Testing Strategy

Tests live in `drc_stat_engine/tests/stat_engine_api/`.

| File | What it tests |
|---|---|
| `test_stat_engine_api_t1_meta.py` | `/api/v1/meta` response structure and content |
| `test_stat_engine_api_t2_report_basic.py` | Valid requests return correct variant structure |
| `test_stat_engine_api_t3_validation.py` | Invalid inputs return correct 4xx codes |
| `test_stat_engine_api_t4_properties.py` | Property-based tests for PROP-1 through PROP-6 |

Flask's built-in test client (`app.test_client()`) is used — no external test runner required.

---

## Dependencies to Add

```
flask
flask-cors
```

Add both to `requirements.txt`.
