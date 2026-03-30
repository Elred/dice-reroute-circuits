"""
Unit tests for routes.py changes for set-die-result feature.
Feature: set-die-result
"""
import sys
import json
import unittest
sys.path.insert(0, '.')

from drc_stat_engine.api.app import create_app


def post_report(client, body):
    return client.post(
        "/api/v1/report",
        data=json.dumps(body),
        content_type="application/json",
    )


BASE_POOL = {"red": 1, "blue": 0, "black": 1, "type": "ship"}


class TestSetDieAPI(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    # -----------------------------------------------------------------------
    # Test 1: Valid change_die request parses correctly
    # -----------------------------------------------------------------------
    def test_valid_set_die_request(self):
        r = post_report(self.client, {
            "dice_pool": BASE_POOL,
            "pipeline": [{
                "type": "change_die",
                "applicable_results": ["R_blank", "B_blank"],
                "target_result": "R_hit",
            }],
            "strategies": ["max_damage"],
        })
        self.assertEqual(r.status_code, 200, f"Expected 200, got {r.status_code}: {r.get_json()}")
        data = r.get_json()
        self.assertIn("variants", data)
        self.assertEqual(len(data["variants"]), 1)

    # -----------------------------------------------------------------------
    # Test 2: Missing target_result returns HTTP 400
    # -----------------------------------------------------------------------
    def test_missing_target_result_returns_400(self):
        r = post_report(self.client, {
            "dice_pool": BASE_POOL,
            "pipeline": [{
                "type": "set_die",
                "applicable_results": ["R_blank"],
                # target_result intentionally omitted
            }],
            "strategies": ["max_damage"],
        })
        self.assertEqual(r.status_code, 400, f"Expected 400, got {r.status_code}: {r.get_json()}")
        data = r.get_json()
        self.assertIn("error", data)
        self.assertIn("target_result", data["error"])

    # -----------------------------------------------------------------------
    # Test 3: /meta includes "set_die" in attack_effect_types
    # -----------------------------------------------------------------------
    def test_meta_includes_set_die(self):
        r = self.client.get("/api/v1/meta")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("attack_effect_types", data)
        self.assertIn("set_die", data["attack_effect_types"])

    # -----------------------------------------------------------------------
    # Test 4: set_die with color-agnostic target_result works
    # -----------------------------------------------------------------------
    def test_set_die_color_agnostic_target(self):
        r = post_report(self.client, {
            "dice_pool": BASE_POOL,
            "pipeline": [{
                "type": "set_die",
                "applicable_results": ["R_blank", "B_blank"],
                "target_result": "hit",  # color-agnostic
            }],
            "strategies": ["max_damage"],
        })
        self.assertEqual(r.status_code, 200, f"Expected 200, got {r.status_code}: {r.get_json()}")

    # -----------------------------------------------------------------------
    # Test 5: set_die with empty applicable_results is a no-op (valid request)
    # -----------------------------------------------------------------------
    def test_set_die_empty_applicable_results(self):
        r = post_report(self.client, {
            "dice_pool": BASE_POOL,
            "pipeline": [{
                "type": "set_die",
                "applicable_results": [],
                "target_result": "R_hit",
            }],
            "strategies": ["max_damage"],
        })
        self.assertEqual(r.status_code, 200, f"Expected 200, got {r.status_code}: {r.get_json()}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
