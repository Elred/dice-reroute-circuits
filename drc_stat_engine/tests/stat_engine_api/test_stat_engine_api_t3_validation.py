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


class TestValidation(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_empty_dice_pool_returns_422(self):
        """6.2 — empty pool (all zeros) → 422."""
        r = post_report(self.client, {
            "dice_pool": {"red": 0, "blue": 0, "black": 0, "type": "ship"},
            "pipeline": [],
        })
        self.assertEqual(r.status_code, 422)
        self.assertIn("error", r.get_json())

    def test_invalid_dice_type_returns_422(self):
        """6.3 — invalid type string → 422."""
        r = post_report(self.client, {
            "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "destroyer"},
            "pipeline": [],
        })
        self.assertEqual(r.status_code, 422)
        self.assertIn("error", r.get_json())

    def test_negative_dice_count_returns_422(self):
        """6.4 — negative count → 422."""
        r = post_report(self.client, {
            "dice_pool": {"red": -1, "blue": 0, "black": 0, "type": "ship"},
            "pipeline": [],
        })
        self.assertEqual(r.status_code, 422)
        self.assertIn("error", r.get_json())

    def test_unknown_attack_effect_type_returns_422(self):
        """6.5 — unknown op type → 422."""
        r = post_report(self.client, {
            "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "ship"},
            "pipeline": [{"type": "explode", "count": 1, "applicable_results": ["R_blank"]}],
        })
        self.assertEqual(r.status_code, 422)
        self.assertIn("error", r.get_json())

    def test_unknown_strategy_returns_422(self):
        """6.6 — unknown strategy → 422."""
        r = post_report(self.client, {
            "dice_pool": {"red": 1, "blue": 0, "black": 0, "type": "ship"},
            "pipeline": [],
            "strategies": ["max_luck"],
        })
        self.assertEqual(r.status_code, 422)
        self.assertIn("error", r.get_json())

    def test_malformed_json_returns_400(self):
        """6.7 — malformed JSON body → 400."""
        r = self.client.post(
            "/api/v1/report",
            data="not json at all {{{",
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("error", r.get_json())

    def test_missing_dice_pool_returns_400(self):
        """Missing dice_pool key → 400."""
        r = post_report(self.client, {"pipeline": []})
        self.assertEqual(r.status_code, 400)
        self.assertIn("error", r.get_json())

    def test_non_json_content_type_returns_400(self):
        """Non-JSON content-type → 400."""
        r = self.client.post(
            "/api/v1/report",
            data='{"dice_pool": {"red": 1}}',
            content_type="text/plain",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("error", r.get_json())


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(unittest.TestLoader().loadTestsFromTestCase(TestValidation))
    total = result.testsRun
    failures = len(result.failures) + len(result.errors)
    if failures == 0:
        print(f"\nOVERALL: ALL PASS ({total} tests)")
    else:
        print(f"\nOVERALL: {failures} FAIL / {total} tests")
