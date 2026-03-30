import sys
import json
import unittest
sys.path.insert(0, '.')

from drc_stat_engine.api.app import create_app


BASE_POOL = {"red": 2, "blue": 1, "black": 0, "type": "ship"}


def post_report(client, body):
    return client.post(
        "/api/v1/report",
        data=json.dumps(body),
        content_type="application/json",
    )


def assert_variant_structure(tc, variant):
    """Assert a variant dict has the required fields with correct types."""
    tc.assertIn("label", variant)
    tc.assertIn("avg_damage", variant)
    tc.assertIn("crit", variant)
    tc.assertIn("damage", variant)
    tc.assertIn("accuracy", variant)
    tc.assertIsInstance(variant["damage"], list)
    tc.assertIsInstance(variant["accuracy"], list)
    tc.assertIsInstance(variant["avg_damage"], float)
    tc.assertIsInstance(variant["crit"], float)


class TestReportBasic(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_single_strategy_returns_one_variant(self):
        """5.2 — single strategy → one variant with correct structure."""
        r = post_report(self.client, {
            "dice_pool": BASE_POOL,
            "pipeline": [],
            "strategies": ["max_damage"],
        })
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("variants", data)
        self.assertEqual(len(data["variants"]), 1)
        assert_variant_structure(self, data["variants"][0])
        self.assertEqual(data["variants"][0]["label"], "max_damage")

    def test_multiple_strategies_returns_one_variant_each(self):
        """5.3 — multiple strategies → one variant per strategy."""
        strategies = ["max_damage", "max_accuracy", "max_crits"]
        r = post_report(self.client, {
            "dice_pool": BASE_POOL,
            "pipeline": [],
            "strategies": strategies,
        })
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(len(data["variants"]), 3)
        labels = [v["label"] for v in data["variants"]]
        self.assertEqual(labels, strategies)

    def test_empty_pipeline_matches_direct_call(self):
        """5.4 — empty pipeline returns same result as generate_report(pool, [], strategies)."""
        from drc_stat_engine.stats.report_engine import generate_report
        from drc_stat_engine.stats.dice_models import DicePool
        pool = DicePool(red=2, blue=1, black=0, type="ship")
        expected = generate_report(pool, [], ["max_damage"])

        r = post_report(self.client, {
            "dice_pool": BASE_POOL,
            "pipeline": [],
            "strategies": ["max_damage"],
        })
        self.assertEqual(r.status_code, 200)
        variant = r.get_json()["variants"][0]

        self.assertAlmostEqual(variant["avg_damage"], expected[0]["avg_damage"], places=10)
        self.assertAlmostEqual(variant["crit"], expected[0]["crit"], places=10)
        # JSON serializes tuples as lists, so normalize expected for comparison
        self.assertEqual(variant["damage"], [list(t) for t in expected[0]["damage"]])
        self.assertEqual(variant["accuracy"], [list(t) for t in expected[0]["accuracy"]])

    def test_strategies_omitted_defaults_to_max_damage(self):
        """5.5 — omitting strategies defaults to max_damage."""
        r = post_report(self.client, {
            "dice_pool": BASE_POOL,
            "pipeline": [],
        })
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(len(data["variants"]), 1)
        self.assertEqual(data["variants"][0]["label"], "max_damage")


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(unittest.TestLoader().loadTestsFromTestCase(TestReportBasic))
    total = result.testsRun
    failures = len(result.failures) + len(result.errors)
    if failures == 0:
        print(f"\nOVERALL: ALL PASS ({total} tests)")
    else:
        print(f"\nOVERALL: {failures} FAIL / {total} tests")
