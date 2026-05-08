import sys
import unittest
sys.path.insert(0, '.')

from drc_stat_engine.api.app import create_app
from drc_stat_engine.stats.profiles import (
    red_die_ship, blue_die_ship, black_die_ship,
    red_die_squad, blue_die_squad, black_die_squad,
)


class TestMetaEndpoint(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_status_200(self):
        r = self.client.get("/api/v1/meta")
        self.assertEqual(r.status_code, 200)

    def test_contains_required_keys(self):
        r = self.client.get("/api/v1/meta")
        data = r.get_json()
        for key in ("dice_types", "strategies", "attack_effect_types", "result_values"):
            self.assertIn(key, data, f"Missing key: {key}")

    def test_dice_types(self):
        data = self.client.get("/api/v1/meta").get_json()
        self.assertEqual(sorted(data["dice_types"]), ["ship", "squad"])

    def test_strategies_keys(self):
        data = self.client.get("/api/v1/meta").get_json()
        self.assertIn("ship", data["strategies"])
        self.assertIn("squad", data["strategies"])

    def test_attack_effect_types(self):
        data = self.client.get("/api/v1/meta").get_json()
        self.assertEqual(sorted(data["attack_effect_types"]), ["add_dice", "add_set_die", "cancel", "change_die", "reroll", "reroll_all"])

    def test_result_values_structure(self):
        data = self.client.get("/api/v1/meta").get_json()
        fv = data["result_values"]
        for dice_type in ("ship", "squad"):
            self.assertIn(dice_type, fv)
            for color in ("red", "blue", "black"):
                self.assertIn(color, fv[dice_type])
                self.assertIsInstance(fv[dice_type][color], list)
                self.assertGreater(len(fv[dice_type][color]), 0)

    def test_result_values_match_profiles(self):
        """REQ-2.3: result_values must be derived from actual profiles."""
        data = self.client.get("/api/v1/meta").get_json()
        fv = data["result_values"]
        self.assertEqual(fv["ship"]["red"],   [f["value"] for f in red_die_ship])
        self.assertEqual(fv["ship"]["blue"],  [f["value"] for f in blue_die_ship])
        self.assertEqual(fv["ship"]["black"], [f["value"] for f in black_die_ship])
        self.assertEqual(fv["squad"]["red"],   [f["value"] for f in red_die_squad])
        self.assertEqual(fv["squad"]["blue"],  [f["value"] for f in blue_die_squad])
        self.assertEqual(fv["squad"]["black"], [f["value"] for f in black_die_squad])


if __name__ == "__main__":
    import unittest
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(unittest.TestLoader().loadTestsFromTestCase(TestMetaEndpoint))
    total = result.testsRun
    failures = len(result.failures) + len(result.errors)
    if failures == 0:
        print(f"\nOVERALL: ALL PASS ({total} tests)")
    else:
        print(f"\nOVERALL: {failures} FAIL / {total} tests")
