# Requirements — Stat Engine API

## Overview

A Flask HTTP API that wraps the existing `drc_stat_engine` probability engine and exposes it to external clients (primarily the Vue.js front-end). The API is stateless: every request carries the full input, and the server returns the computed result.

---

## Functional Requirements

### 1. Report Endpoint

**REQ-1.1** The API MUST expose a `POST /api/v1/report` endpoint that accepts a dice pool, an operation pipeline, and a list of strategies, and returns computed statistics for each strategy variant.

**REQ-1.2** The request body MUST be JSON with the following structure:
```json
{
  "dice_pool": {
    "red":   <int>,
    "blue":  <int>,
    "black": <int>,
    "type":  "ship" | "squad"
  },
  "pipeline": [
    {
      "type": "reroll" | "cancel" | "add_dice",
      "count": <int>,                        // required for reroll / cancel
      "applicable_results": ["<face>", ...], // required for reroll / cancel
      "dice_to_add": {                       // required for add_dice
        "red": <int>, "blue": <int>, "black": <int>
      }
    }
  ],
  "strategies": ["max_damage" | "max_accuracy" | "max_crits" | "max_doubles"]
}
```

**REQ-1.3** `pipeline` MAY be an empty array `[]` (no operations applied).

**REQ-1.4** `strategies` MAY be omitted; the server MUST default to `["max_damage"]` when absent.

**REQ-1.5** The response body MUST be JSON with the following structure:
```json
{
  "variants": [
    {
      "label": "<strategy_name>",
      "avg_damage": <float>,
      "crit": <float>,
      "damage": [[<threshold_int>, <probability_float>], ...],
      "accuracy": [[<threshold_int>, <probability_float>], ...]
    }
  ]
}
```

**REQ-1.6** Each `damage` and `accuracy` array MUST include all integer thresholds from 0 to the maximum observed value, even if the probability at that threshold is 0.

**REQ-1.7** All probability values in the response MUST be in the range [0.0, 1.0] (not percentages).

---

### 2. Metadata Endpoint

**REQ-2.1** The API MUST expose a `GET /api/v1/meta` endpoint that returns static metadata about valid inputs.

**REQ-2.2** The response MUST include:
- `dice_types`: list of valid type strings (`["ship", "squad"]`)
- `strategies`: list of valid strategy names per type
- `operation_types`: list of valid operation type strings
- `face_values`: dict mapping `(type, color)` to the list of valid face value strings for that combination

Example response:
```json
{
  "dice_types": ["ship", "squad"],
  "strategies": {
    "ship":  ["max_damage", "max_accuracy", "max_crits", "max_doubles"],
    "squad": ["max_damage", "max_accuracy", "max_crits"]
  },
  "operation_types": ["reroll", "cancel", "add_dice"],
  "face_values": {
    "ship": {
      "red":   ["R_blank", "R_hit", "R_crit", "R_acc", "R_hit+hit"],
      "blue":  ["U_hit", "U_crit", "U_acc"],
      "black": ["B_blank", "B_hit", "B_hit+crit"]
    },
    "squad": {
      "red":   ["R_blank", "R_hit", "R_crit", "R_acc", "R_hit+hit"],
      "blue":  ["U_hit", "U_crit", "U_acc"],
      "black": ["B_blank", "B_hit", "B_hit+crit"]
    }
  }
}
```

**REQ-2.3** The `/api/v1/meta` response MUST be derived from the actual `profiles.py` and `report.py` constants — it MUST NOT be hardcoded independently.

---

### 3. Input Validation & Error Handling

**REQ-3.1** If the request body is missing or not valid JSON, the API MUST return HTTP 400 with `{"error": "Invalid JSON"}`.

**REQ-3.2** If `dice_pool` validation fails (empty pool, negative counts, invalid type), the API MUST return HTTP 422 with `{"error": "<message from validate_dice_pool>"}`.

**REQ-3.3** If `pipeline` validation fails (unknown operation type), the API MUST return HTTP 422 with `{"error": "<message from validate_operation_pipeline>"}`.

**REQ-3.4** If an unknown strategy name is provided, the API MUST return HTTP 422 with `{"error": "<descriptive message>"}`.

**REQ-3.5** If an unexpected server-side error occurs, the API MUST return HTTP 500 with `{"error": "Internal server error"}` and log the full traceback server-side.

**REQ-3.6** Validation MUST delegate to the existing `validate_dice_pool` and `validate_operation_pipeline` functions in `report.py` — the API layer MUST NOT duplicate validation logic.

---

### 4. CORS

**REQ-4.1** The API MUST allow cross-origin requests from `http://localhost:5173` (Vite dev server) during development.

**REQ-4.2** CORS MUST be implemented via `flask-cors` and MUST NOT be hand-rolled.

---

### 5. Non-Functional Requirements

**REQ-5.1** The API MUST be stateless — no session, no database, no in-memory state between requests.

**REQ-5.2** The API MUST run on `http://localhost:5000` by default.

**REQ-5.3** All route handler functions MUST import and call `report.py` functions directly; no business logic is permitted in `routes.py`.

**REQ-5.4** The API MUST start successfully with `python app.py` from the `drc_stat_engine/api/` directory after activating the `drc` virtualenv.

---

## Correctness Properties

These properties define what it means for the API to be correct and will be validated with property-based tests.

**PROP-1** (Round-trip integrity) For any valid `(dice_pool, pipeline, strategies)` input, the JSON response from `POST /api/v1/report` MUST be numerically equivalent to calling `generate_report(dice_pool, pipeline, strategies)` directly in Python.

**PROP-2** (Probability bounds) Every probability value in `damage` and `accuracy` arrays MUST satisfy `0.0 ≤ p ≤ 1.0`.

**PROP-3** (Monotone cumulative) For each variant, `damage[i][1] ≥ damage[i+1][1]` for all consecutive thresholds (cumulative probability is non-increasing). Same for `accuracy`.

**PROP-4** (Threshold completeness) The `damage` array MUST start at threshold 0 and include every integer up to the maximum, with no gaps.

**PROP-5** (Validation mirror) Any input that causes `validate_dice_pool` or `validate_operation_pipeline` to raise `ValueError` in Python MUST cause the API to return a 4xx status code — never 200.

**PROP-6** (Empty pipeline identity) A request with an empty pipeline MUST return the same statistics as calling `generate_report` with `pipeline=[]`.
