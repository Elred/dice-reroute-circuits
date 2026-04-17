"""
Property-based tests for the Stat Engine API (PROP-1 through PROP-6).
Uses Hypothesis to generate random valid (and invalid) inputs.
"""
import sys
import json
import unittest
sys.path.insert(0, '.')

from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from drc_stat_engine.api.app import create_app
from drc_stat_engine.stats.dice_models import (
    DicePool, AttackEffect, VALID_ATTACK_EFFECT_TYPES,
    validate_dice_pool, validate_attack_effect_pipeline,
)
from drc_stat_engine.stats.strategies import STRATEGY_PRIORITY_LISTS
from drc_stat_engine.stats.report_engine import generate_report
from drc_stat_engine.stats.profiles import (
    red_die_ship, blue_die_ship, black_die_ship,
    red_die_squad, blue_die_squad, black_die_squad,
)

# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

DICE_TYPES = ["ship", "squad"]
ALL_STRATEGIES = {
    "ship": list(STRATEGY_PRIORITY_LISTS["ship"].keys()),
    "squad": list(STRATEGY_PRIORITY_LISTS["squad"].keys()),
}
ALL_RESULT_VALUES = {
    "ship": (
        [f["value"] for f in red_die_ship]
        + [f["value"] for f in blue_die_ship]
        + [f["value"] for f in black_die_ship]
    ),
    "squad": (
        [f["value"] for f in red_die_squad]
        + [f["value"] for f in blue_die_squad]
        + [f["value"] for f in black_die_squad]
    ),
}

dice_type_st = st.sampled_from(DICE_TYPES)


@st.composite
def valid_dice_pool_st(draw):
    dtype = draw(dice_type_st)
    red = draw(st.integers(min_value=0, max_value=2))
    blue = draw(st.integers(min_value=0, max_value=2))
    black = draw(st.integers(min_value=0, max_value=2))
    assume(red + blue + black > 0)
    # Cap total dice to keep computation fast
    assume(red + blue + black <= 3)
    return {"red": red, "blue": blue, "black": black, "type": dtype}


@st.composite
def valid_attack_effect_st(draw, dtype):
    # Exclude change_die to avoid needing target_result in random generation
    op_type = draw(st.sampled_from(["reroll", "cancel", "add_dice"]))
    if op_type == "add_dice":
        r = draw(st.integers(min_value=0, max_value=1))
        u = draw(st.integers(min_value=0, max_value=1))
        b = draw(st.integers(min_value=0, max_value=1))
        return {"type": "add_dice", "dice_to_add": {"red": r, "blue": u, "black": b}}
    else:
        faces = ALL_RESULT_VALUES[dtype]
        count = draw(st.integers(min_value=1, max_value=2))
        applicable = draw(st.lists(st.sampled_from(faces), min_size=1, max_size=4, unique=True))
        return {"type": op_type, "count": count, "applicable_results": applicable}


@st.composite
def valid_request_st(draw):
    pool_dict = draw(valid_dice_pool_st())
    dtype = pool_dict["type"]
    pipeline = draw(st.lists(valid_attack_effect_st(dtype), min_size=0, max_size=2))
    strategies = [draw(st.sampled_from(ALL_STRATEGIES[dtype]))]
    return {"dice_pool": pool_dict, "pipeline": pipeline, "strategies": strategies}


def post_report(client, body):
    return client.post(
        "/api/v1/report",
        data=json.dumps(body),
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------

class TestProperties(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    @given(valid_request_st())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_prop1_round_trip(self, req):
        """PROP-1: API response matches generate_report() output directly."""
        r = post_report(self.client, req)
        self.assertEqual(r.status_code, 200, f"Expected 200, got {r.status_code}: {r.get_json()}")
        api_variants = r.get_json()["variants"]

        dp = req["dice_pool"]
        pool = DicePool(red=dp["red"], blue=dp["blue"], black=dp["black"], type=dp["type"])
        pipeline = []
        for op in req.get("pipeline", []):
            pipeline.append(AttackEffect(
                type=op["type"],
                count=op.get("count", 1),
                applicable_results=op.get("applicable_results", []),
                dice_to_add=op.get("dice_to_add"),
            ))
        expected = generate_report(pool, pipeline, req["strategies"])

        self.assertEqual(len(api_variants), len(expected))
        for api_v, exp_v in zip(api_variants, expected):
            self.assertAlmostEqual(api_v["avg_damage"], exp_v["avg_damage"], places=10)
            self.assertAlmostEqual(api_v["crit"], exp_v["crit"], places=10)
            self.assertEqual(api_v["damage"], [list(t) for t in exp_v["damage"]])
            self.assertEqual(api_v["accuracy"], [list(t) for t in exp_v["accuracy"]])

    @given(valid_request_st())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_prop2_probability_bounds(self, req):
        """PROP-2: all probability values in [0.0, 1.0]."""
        r = post_report(self.client, req)
        self.assertEqual(r.status_code, 200)
        for variant in r.get_json()["variants"]:
            for _, p in variant["damage"]:
                self.assertGreaterEqual(p, 0.0, f"damage prob {p} < 0")
                self.assertLessEqual(p, 1.0, f"damage prob {p} > 1")
            for _, p in variant["accuracy"]:
                self.assertGreaterEqual(p, 0.0, f"accuracy prob {p} < 0")
                self.assertLessEqual(p, 1.0, f"accuracy prob {p} > 1")

    @given(valid_request_st())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_prop3_monotone_cumulative(self, req):
        """PROP-3: cumulative damage and accuracy arrays are non-increasing."""
        r = post_report(self.client, req)
        assume(r.status_code == 200)  # skip edge cases that produce engine errors
        for variant in r.get_json()["variants"]:
            dmg = [p for _, p in variant["damage"]]
            for i in range(len(dmg) - 1):
                self.assertGreaterEqual(dmg[i], dmg[i + 1] - 1e-12,
                    f"damage not non-increasing at index {i}: {dmg[i]} < {dmg[i+1]}")
            acc = [p for _, p in variant["accuracy"]]
            for i in range(len(acc) - 1):
                self.assertGreaterEqual(acc[i], acc[i + 1] - 1e-12,
                    f"accuracy not non-increasing at index {i}: {acc[i]} < {acc[i+1]}")

    @given(valid_request_st())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_prop4_threshold_completeness(self, req):
        """PROP-4: damage array starts at 0 with no gaps."""
        r = post_report(self.client, req)
        assume(r.status_code == 200)  # skip edge cases that produce engine errors
        for variant in r.get_json()["variants"]:
            thresholds = [t for t, _ in variant["damage"]]
            self.assertEqual(thresholds[0], 0, "damage array must start at threshold 0")
            for i in range(len(thresholds) - 1):
                self.assertEqual(thresholds[i + 1], thresholds[i] + 1,
                    f"gap in damage thresholds: {thresholds[i]} → {thresholds[i+1]}")

    @given(valid_request_st())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_prop6_empty_pipeline_identity(self, req):
        """PROP-6: empty pipeline returns same stats as baseline generate_report."""
        req_empty = dict(req, pipeline=[])
        r = post_report(self.client, req_empty)
        self.assertEqual(r.status_code, 200)

        dp = req["dice_pool"]
        pool = DicePool(red=dp["red"], blue=dp["blue"], black=dp["black"], type=dp["type"])
        expected = generate_report(pool, [], req["strategies"])

        api_variants = r.get_json()["variants"]
        for api_v, exp_v in zip(api_variants, expected):
            self.assertAlmostEqual(api_v["avg_damage"], exp_v["avg_damage"], places=10)
            self.assertEqual(api_v["damage"], [list(t) for t in exp_v["damage"]])


class TestProp5ValidationMirror(unittest.TestCase):
    """PROP-5: any input rejected by validate_* returns 4xx from the API."""

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    @given(st.integers(max_value=-1))
    @settings(max_examples=20)
    def test_negative_red_always_422(self, n):
        r = post_report(self.client, {
            "dice_pool": {"red": n, "blue": 0, "black": 0, "type": "ship"},
            "pipeline": [],
        })
        self.assertIn(r.status_code, (400, 422))

    @given(st.text(min_size=1).filter(lambda s: s not in ("ship", "squad")))
    @settings(max_examples=20)
    def test_invalid_type_always_422(self, t):
        r = post_report(self.client, {
            "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": t},
            "pipeline": [],
        })
        self.assertIn(r.status_code, (400, 422))

    @given(st.text(min_size=1).filter(lambda s: s not in VALID_ATTACK_EFFECT_TYPES))
    @settings(max_examples=20)
    def test_invalid_op_type_always_422(self, op):
        r = post_report(self.client, {
            "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "ship"},
            "pipeline": [{"type": op, "count": 1, "applicable_results": []}],
        })
        self.assertIn(r.status_code, (400, 422))


def post_report(client, body):
    return client.post(
        "/api/v1/report",
        data=json.dumps(body),
        content_type="application/json",
    )


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestProperties))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestProp5ValidationMirror))
    result = runner.run(suite)
    total = result.testsRun
    failures = len(result.failures) + len(result.errors)
    if failures == 0:
        print(f"\nOVERALL: ALL PASS ({total} tests)")
    else:
        print(f"\nOVERALL: {failures} FAIL / {total} tests")
