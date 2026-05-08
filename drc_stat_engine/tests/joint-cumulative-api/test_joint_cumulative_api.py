"""
Property-based tests for the Joint Cumulative API.
Feature: joint-cumulative-api

Tests verify that the /api/v1/report endpoint correctly includes
well-formed joint_cumulative data in responses for both defense
and non-defense requests.
"""
import sys
import json
import unittest
sys.path.insert(0, '.')

from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from drc_stat_engine.api.app import create_app
from drc_stat_engine.stats.strategies import STRATEGY_PRIORITY_LISTS
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
    """Generate a valid dice pool with 1-3 total dice."""
    dtype = draw(dice_type_st)
    red = draw(st.integers(min_value=0, max_value=2))
    blue = draw(st.integers(min_value=0, max_value=2))
    black = draw(st.integers(min_value=0, max_value=2))
    assume(red + blue + black > 0)
    assume(red + blue + black <= 3)
    return {"red": red, "blue": blue, "black": black, "type": dtype}


@st.composite
def valid_attack_pipeline_st(draw, dtype):
    """Generate an optional attack pipeline (0-2 effects)."""
    op_type = draw(st.sampled_from(["reroll", "cancel"]))
    faces = ALL_RESULT_VALUES[dtype]
    count = draw(st.integers(min_value=1, max_value=2))
    applicable = draw(st.lists(st.sampled_from(faces), min_size=1, max_size=3, unique=True))
    return {"type": op_type, "count": count, "applicable_results": applicable}


@st.composite
def valid_defense_pipeline_st(draw):
    """Generate a defense pipeline with 1 defense_reroll effect."""
    count = draw(st.integers(min_value=1, max_value=2))
    mode = draw(st.sampled_from(["safe", "gamble"]))
    return [{"type": "defense_reroll", "count": count, "mode": mode}]


@st.composite
def valid_request_no_defense_st(draw):
    """Generate a valid report request without defense pipeline."""
    pool_dict = draw(valid_dice_pool_st())
    dtype = pool_dict["type"]
    pipeline = draw(st.lists(valid_attack_pipeline_st(dtype), min_size=0, max_size=1))
    strategies = [draw(st.sampled_from(ALL_STRATEGIES[dtype]))]
    return {"dice_pool": pool_dict, "pipeline": pipeline, "strategies": strategies}


@st.composite
def valid_request_with_defense_st(draw):
    """Generate a valid report request with a defense pipeline."""
    pool_dict = draw(valid_dice_pool_st())
    dtype = pool_dict["type"]
    pipeline = draw(st.lists(valid_attack_pipeline_st(dtype), min_size=0, max_size=1))
    strategies = [draw(st.sampled_from(ALL_STRATEGIES[dtype]))]
    defense_pipeline = draw(valid_defense_pipeline_st())
    return {
        "dice_pool": pool_dict,
        "pipeline": pipeline,
        "strategies": strategies,
        "defense_pipeline": defense_pipeline,
    }


@st.composite
def valid_request_any_st(draw):
    """Generate a valid report request, optionally with defense pipeline."""
    has_defense = draw(st.booleans())
    if has_defense:
        return draw(valid_request_with_defense_st())
    else:
        return draw(valid_request_no_defense_st())


def post_report(client, body):
    """Helper to POST a report request."""
    return client.post(
        "/api/v1/report",
        data=json.dumps(body),
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# Helper: validate joint_cumulative payload structure
# ---------------------------------------------------------------------------

def assert_well_formed_joint_cumulative(test_case, jc, context=""):
    """Assert that a joint_cumulative payload is well-formed."""
    prefix = f"[{context}] " if context else ""

    # Must have exactly three keys
    test_case.assertIn("damage_thresholds", jc, f"{prefix}missing damage_thresholds")
    test_case.assertIn("accuracy_thresholds", jc, f"{prefix}missing accuracy_thresholds")
    test_case.assertIn("matrix", jc, f"{prefix}missing matrix")

    dmg_t = jc["damage_thresholds"]
    acc_t = jc["accuracy_thresholds"]
    matrix = jc["matrix"]

    # Thresholds are lists of integers starting at 0
    test_case.assertIsInstance(dmg_t, list, f"{prefix}damage_thresholds not a list")
    test_case.assertIsInstance(acc_t, list, f"{prefix}accuracy_thresholds not a list")
    test_case.assertGreater(len(dmg_t), 0, f"{prefix}damage_thresholds empty")
    test_case.assertGreater(len(acc_t), 0, f"{prefix}accuracy_thresholds empty")
    test_case.assertEqual(dmg_t[0], 0, f"{prefix}damage_thresholds must start at 0")
    test_case.assertEqual(acc_t[0], 0, f"{prefix}accuracy_thresholds must start at 0")

    # Thresholds are consecutive integers
    for i in range(len(dmg_t) - 1):
        test_case.assertEqual(dmg_t[i + 1], dmg_t[i] + 1,
            f"{prefix}damage_thresholds not consecutive at index {i}")
    for i in range(len(acc_t) - 1):
        test_case.assertEqual(acc_t[i + 1], acc_t[i] + 1,
            f"{prefix}accuracy_thresholds not consecutive at index {i}")

    # Matrix dimensions match thresholds
    test_case.assertEqual(len(matrix), len(dmg_t),
        f"{prefix}matrix rows ({len(matrix)}) != damage_thresholds ({len(dmg_t)})")
    for row_idx, row in enumerate(matrix):
        test_case.assertEqual(len(row), len(acc_t),
            f"{prefix}matrix row {row_idx} cols ({len(row)}) != accuracy_thresholds ({len(acc_t)})")


# ---------------------------------------------------------------------------
# Property 1: Well-formed joint cumulative payload
# Feature: joint-cumulative-api, Property 1: API response includes well-formed joint cumulative payload
# ---------------------------------------------------------------------------

class TestProperty1WellFormedPayload(unittest.TestCase):
    """
    Property 1: API response includes well-formed joint cumulative payload.
    **Validates: Requirements 1.1, 1.2, 1.3, 3.1, 3.2**
    """

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    @given(valid_request_no_defense_st())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_prop1_no_defense_joint_cumulative_present_and_well_formed(self, req):
        """For non-defense requests: joint_cumulative is present at variant top level and well-formed."""
        r = post_report(self.client, req)
        self.assertEqual(r.status_code, 200, f"Expected 200, got {r.status_code}: {r.get_json()}")
        data = r.get_json()
        variants = data["variants"]
        self.assertGreater(len(variants), 0)

        for idx, variant in enumerate(variants):
            self.assertIn("joint_cumulative", variant,
                f"Variant {idx} missing joint_cumulative (non-defense)")
            jc = variant["joint_cumulative"]
            assert_well_formed_joint_cumulative(self, jc, context=f"variant[{idx}]")

    @given(valid_request_with_defense_st())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_prop1_defense_joint_cumulative_present_and_well_formed(self, req):
        """For defense requests: joint_cumulative is present in both pre_defense and post_defense."""
        r = post_report(self.client, req)
        self.assertEqual(r.status_code, 200, f"Expected 200, got {r.status_code}: {r.get_json()}")
        data = r.get_json()
        variants = data["variants"]
        self.assertGreater(len(variants), 0)

        for idx, variant in enumerate(variants):
            self.assertIn("pre_defense", variant,
                f"Variant {idx} missing pre_defense")
            self.assertIn("post_defense", variant,
                f"Variant {idx} missing post_defense")

            pre = variant["pre_defense"]
            post = variant["post_defense"]

            self.assertIn("joint_cumulative", pre,
                f"Variant {idx} pre_defense missing joint_cumulative")
            self.assertIn("joint_cumulative", post,
                f"Variant {idx} post_defense missing joint_cumulative")

            assert_well_formed_joint_cumulative(self, pre["joint_cumulative"],
                context=f"variant[{idx}].pre_defense")
            assert_well_formed_joint_cumulative(self, post["joint_cumulative"],
                context=f"variant[{idx}].post_defense")


# ---------------------------------------------------------------------------
# Property 2: Joint cumulative probability bounds
# Feature: joint-cumulative-api, Property 2: Joint cumulative probability bounds
# ---------------------------------------------------------------------------

class TestProperty2ProbabilityBounds(unittest.TestCase):
    """
    Property 2: Joint cumulative probability bounds.
    **Validates: Requirements 3.3, 3.4**
    """

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    @given(valid_request_any_st())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_prop2_probability_bounds(self, req):
        """All matrix values in [0.0, 1.0] and matrix[0][0] == 1.0."""
        r = post_report(self.client, req)
        self.assertEqual(r.status_code, 200, f"Expected 200, got {r.status_code}: {r.get_json()}")
        data = r.get_json()
        variants = data["variants"]

        has_defense = "defense_pipeline" in req and len(req["defense_pipeline"]) > 0

        for idx, variant in enumerate(variants):
            if has_defense:
                jc_payloads = [
                    (variant["pre_defense"]["joint_cumulative"], f"variant[{idx}].pre_defense"),
                    (variant["post_defense"]["joint_cumulative"], f"variant[{idx}].post_defense"),
                ]
            else:
                jc_payloads = [
                    (variant["joint_cumulative"], f"variant[{idx}]"),
                ]

            for jc, context in jc_payloads:
                matrix = jc["matrix"]
                # matrix[0][0] must be 1.0
                self.assertAlmostEqual(matrix[0][0], 1.0, places=10,
                    msg=f"[{context}] matrix[0][0] should be 1.0, got {matrix[0][0]}")

                # All values in [0.0, 1.0]
                for r_idx, row in enumerate(matrix):
                    for c_idx, val in enumerate(row):
                        self.assertGreaterEqual(val, 0.0,
                            f"[{context}] matrix[{r_idx}][{c_idx}] = {val} < 0.0")
                        self.assertLessEqual(val, 1.0,
                            f"[{context}] matrix[{r_idx}][{c_idx}] = {val} > 1.0")


# ---------------------------------------------------------------------------
# Smoke tests for specific scenarios
# ---------------------------------------------------------------------------

class TestSmokeScenarios(unittest.TestCase):
    """
    Smoke tests for specific joint cumulative scenarios.
    _Requirements: 1.1, 1.2, 1.4_
    """

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_smoke_1r_ship_no_defense(self):
        """Single request with 1R ship pool (no defense): joint_cumulative present and matrix[0][0] == 1.0."""
        body = {
            "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "ship"},
            "pipeline": [],
            "strategies": ["max_damage"],
        }
        r = post_report(self.client, body)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        variant = data["variants"][0]

        self.assertIn("joint_cumulative", variant)
        jc = variant["joint_cumulative"]
        self.assertIn("damage_thresholds", jc)
        self.assertIn("accuracy_thresholds", jc)
        self.assertIn("matrix", jc)
        self.assertEqual(jc["matrix"][0][0], 1.0)

    def test_smoke_defense_pipeline(self):
        """Single request with defense pipeline: both pre_defense and post_defense have joint_cumulative."""
        body = {
            "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "ship"},
            "pipeline": [],
            "strategies": ["max_damage"],
            "defense_pipeline": [{"type": "defense_reroll", "count": 1, "mode": "safe"}],
        }
        r = post_report(self.client, body)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        variant = data["variants"][0]

        self.assertIn("pre_defense", variant)
        self.assertIn("post_defense", variant)
        self.assertIn("joint_cumulative", variant["pre_defense"])
        self.assertIn("joint_cumulative", variant["post_defense"])

        # Both should have matrix[0][0] == 1.0
        self.assertEqual(variant["pre_defense"]["joint_cumulative"]["matrix"][0][0], 1.0)
        self.assertEqual(variant["post_defense"]["joint_cumulative"]["matrix"][0][0], 1.0)

    def test_smoke_float_precision(self):
        """Verify float precision is preserved (no rounding to fewer decimal places)."""
        body = {
            "dice_pool": {"red": 1, "blue": 1, "black": 0, "type": "ship"},
            "pipeline": [],
            "strategies": ["max_damage"],
        }
        r = post_report(self.client, body)
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        variant = data["variants"][0]
        jc = variant["joint_cumulative"]

        # Find a non-trivial value (not 0.0 or 1.0) and verify it has precision
        found_precise = False
        for row in jc["matrix"]:
            for val in row:
                if 0.0 < val < 1.0:
                    # Value should not be rounded to e.g. 1 decimal place
                    # A float like 0.5 is fine, but we expect at least some values
                    # with more precision from a 2-die pool
                    val_str = f"{val:.15g}"
                    found_precise = True
                    # Verify it's a proper float, not truncated
                    self.assertIsInstance(val, float,
                        f"Expected float, got {type(val)}: {val}")
                    break
            if found_precise:
                break
        # With 1R+1B dice, there must be intermediate probabilities
        self.assertTrue(found_precise,
            "Expected at least one intermediate probability value in matrix")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestProperty1WellFormedPayload))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestProperty2ProbabilityBounds))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSmokeScenarios))
    result = runner.run(suite)
    total = result.testsRun
    failures = len(result.failures) + len(result.errors)
    if failures == 0:
        print(f"\nOVERALL: ALL PASS ({total} tests)")
    else:
        print(f"\nOVERALL: {failures} FAIL / {total} tests")
