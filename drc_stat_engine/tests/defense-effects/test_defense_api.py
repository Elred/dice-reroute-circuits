"""
Unit tests for API defense pipeline parsing and response format.
Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 9.3, 9.4, 9.5
"""
import sys
sys.path.insert(0, '.')

import json
from drc_stat_engine.api.app import create_app

app = create_app()
client = app.test_client()

passed = 0
failed = 0

BASE_REQUEST = {
    "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "ship"},
    "pipeline": [],
    "strategies": ["max_damage"],
}


def check(label, condition, detail=""):
    global passed, failed
    if condition:
        print(f"PASS: {label}")
        passed += 1
    else:
        print(f"FAIL: {label} — {detail}")
        failed += 1


# ---------------------------------------------------------------------------
# 1. Request parsing with valid defense_pipeline — 200 with pre/post keys
# ---------------------------------------------------------------------------
try:
    data = {**BASE_REQUEST, "defense_pipeline": [
        {"type": "defense_reroll", "count": 1, "mode": "safe"},
    ]}
    resp = client.post("/api/v1/report", data=json.dumps(data),
                       content_type="application/json")
    check("valid defense_pipeline returns 200", resp.status_code == 200,
          f"got {resp.status_code}")
    body = resp.get_json()
    variant = body["variants"][0]
    check("response has pre_defense key", "pre_defense" in variant,
          f"keys: {list(variant.keys())}")
    check("response has post_defense key", "post_defense" in variant,
          f"keys: {list(variant.keys())}")
except Exception as e:
    check("valid defense_pipeline request", False, f"{type(e).__name__}: {e}")

# ---------------------------------------------------------------------------
# 2. HTTP 422 for unknown defense type
# ---------------------------------------------------------------------------
try:
    data = {**BASE_REQUEST, "defense_pipeline": [
        {"type": "unknown_type", "count": 1},
    ]}
    resp = client.post("/api/v1/report", data=json.dumps(data),
                       content_type="application/json")
    check("unknown defense type returns 422", resp.status_code == 422,
          f"got {resp.status_code}")
    body = resp.get_json()
    check("unknown type error message mentions type",
          "unknown_type" in body.get("error", "").lower() or "unknown" in body.get("error", "").lower(),
          f"error: {body.get('error')}")
except Exception as e:
    check("unknown defense type", False, f"{type(e).__name__}: {e}")

# ---------------------------------------------------------------------------
# 3. HTTP 422 for missing mode on defense_reroll
# ---------------------------------------------------------------------------
try:
    data = {**BASE_REQUEST, "defense_pipeline": [
        {"type": "defense_reroll", "count": 1},
    ]}
    resp = client.post("/api/v1/report", data=json.dumps(data),
                       content_type="application/json")
    check("missing mode on defense_reroll returns 422", resp.status_code == 422,
          f"got {resp.status_code}")
    body = resp.get_json()
    check("missing mode error mentions mode",
          "mode" in body.get("error", "").lower(),
          f"error: {body.get('error')}")
except Exception as e:
    check("missing mode on defense_reroll", False, f"{type(e).__name__}: {e}")

# ---------------------------------------------------------------------------
# 4. HTTP 422 for bad count (defense_cancel count=0)
# ---------------------------------------------------------------------------
try:
    data = {**BASE_REQUEST, "defense_pipeline": [
        {"type": "defense_cancel", "count": 0},
    ]}
    resp = client.post("/api/v1/report", data=json.dumps(data),
                       content_type="application/json")
    check("defense_cancel count=0 returns 422", resp.status_code == 422,
          f"got {resp.status_code}")
    body = resp.get_json()
    check("bad count error mentions count or positive",
          "count" in body.get("error", "").lower() or "positive" in body.get("error", "").lower(),
          f"error: {body.get('error')}")
except Exception as e:
    check("bad count on defense_cancel", False, f"{type(e).__name__}: {e}")

# ---------------------------------------------------------------------------
# 5. HTTP 422 for bad amount (reduce_damage amount=0)
# ---------------------------------------------------------------------------
try:
    data = {**BASE_REQUEST, "defense_pipeline": [
        {"type": "reduce_damage", "amount": 0},
    ]}
    resp = client.post("/api/v1/report", data=json.dumps(data),
                       content_type="application/json")
    check("reduce_damage amount=0 returns 422", resp.status_code == 422,
          f"got {resp.status_code}")
    body = resp.get_json()
    check("bad amount error mentions amount or positive",
          "amount" in body.get("error", "").lower() or "positive" in body.get("error", "").lower(),
          f"error: {body.get('error')}")
except Exception as e:
    check("bad amount on reduce_damage", False, f"{type(e).__name__}: {e}")

# ---------------------------------------------------------------------------
# 6. Response includes pre_defense/post_defense structure when defense present
# ---------------------------------------------------------------------------
try:
    data = {**BASE_REQUEST, "defense_pipeline": [
        {"type": "reduce_damage", "amount": 1},
    ]}
    resp = client.post("/api/v1/report", data=json.dumps(data),
                       content_type="application/json")
    check("reduce_damage request returns 200", resp.status_code == 200,
          f"got {resp.status_code}")
    body = resp.get_json()
    variant = body["variants"][0]

    # Check pre_defense structure
    pre = variant.get("pre_defense", {})
    for key in ("avg_damage", "crit", "damage_zero", "acc_zero", "damage", "accuracy"):
        check(f"pre_defense has '{key}'", key in pre,
              f"pre_defense keys: {list(pre.keys())}")

    # Check post_defense structure
    post = variant.get("post_defense", {})
    for key in ("avg_damage", "crit", "damage_zero", "acc_zero", "damage", "accuracy"):
        check(f"post_defense has '{key}'", key in post,
              f"post_defense keys: {list(post.keys())}")

    # Post-defense avg_damage should be <= pre-defense avg_damage (reduce_damage lowers it)
    check("post avg_damage <= pre avg_damage after reduce",
          post["avg_damage"] <= pre["avg_damage"] + 1e-9,
          f"pre={pre['avg_damage']}, post={post['avg_damage']}")
except Exception as e:
    check("pre/post defense structure", False, f"{type(e).__name__}: {e}")

# ---------------------------------------------------------------------------
# 7. Response uses existing flat format when no defense pipeline
# ---------------------------------------------------------------------------
try:
    data = {**BASE_REQUEST}  # no defense_pipeline key
    resp = client.post("/api/v1/report", data=json.dumps(data),
                       content_type="application/json")
    check("no defense_pipeline returns 200", resp.status_code == 200,
          f"got {resp.status_code}")
    body = resp.get_json()
    variant = body["variants"][0]

    # Flat format: top-level keys, no pre_defense/post_defense
    check("flat format has 'avg_damage'", "avg_damage" in variant,
          f"keys: {list(variant.keys())}")
    check("flat format has 'damage'", "damage" in variant,
          f"keys: {list(variant.keys())}")
    check("flat format has 'accuracy'", "accuracy" in variant,
          f"keys: {list(variant.keys())}")
    check("flat format has 'crit'", "crit" in variant,
          f"keys: {list(variant.keys())}")
    check("flat format has no 'pre_defense'", "pre_defense" not in variant,
          f"keys: {list(variant.keys())}")
    check("flat format has no 'post_defense'", "post_defense" not in variant,
          f"keys: {list(variant.keys())}")
except Exception as e:
    check("flat format without defense", False, f"{type(e).__name__}: {e}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
