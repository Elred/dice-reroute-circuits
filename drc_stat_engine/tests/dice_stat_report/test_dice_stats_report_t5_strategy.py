"""
Tests for task 5: strategy-based report variants.
Covers STRATEGY_PRIORITY_LISTS, build_strategy_pipeline, and generate_report.
"""
import sys
import os
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from drc_stat_engine.stats.dice_models import DicePool, AttackEffect
from drc_stat_engine.stats.strategies import (
    STRATEGY_PRIORITY_LISTS, PRIORITY_DEPENDENT_OPS,
    build_strategy_pipeline,
)
from drc_stat_engine.stats.report_engine import generate_report

SHIP_STRATEGIES = ("max_damage", "max_doubles", "max_accuracy", "max_crits")
SQUAD_STRATEGIES = ("max_damage", "max_accuracy", "max_crits")


# ---------------------------------------------------------------------------
# 5.1 — Strategy priority lists
# ---------------------------------------------------------------------------

class TestStrategyPriorityLists(unittest.TestCase):

    def test_ship_strategies_defined(self):
        for strategy in SHIP_STRATEGIES:
            pl = STRATEGY_PRIORITY_LISTS["ship"][strategy]["reroll"]
            self.assertIsInstance(pl, list)
            self.assertGreater(len(pl), 0, f"ship[{strategy}] is empty")

    def test_squad_strategies_defined(self):
        for strategy in SQUAD_STRATEGIES:
            pl = STRATEGY_PRIORITY_LISTS["squad"][strategy]["reroll"]
            self.assertIsInstance(pl, list)
            self.assertGreater(len(pl), 0, f"squad[{strategy}] is empty")

    def test_no_duplicates(self):
        for type_str, strategies in (("ship", SHIP_STRATEGIES), ("squad", SQUAD_STRATEGIES)):
            for strategy in strategies:
                pl = STRATEGY_PRIORITY_LISTS[type_str][strategy]["reroll"]
                self.assertEqual(len(pl), len(set(pl)),
                    f"{type_str} {strategy}: duplicate faces {[f for f in pl if pl.count(f) > 1]}")

    # ship max_damage ordering
    def test_ship_max_damage_blank_before_acc(self):
        pl = STRATEGY_PRIORITY_LISTS["ship"]["max_damage"]["reroll"]
        self.assertLess(pl.index("R_blank"), pl.index("R_acc"))
        self.assertLess(pl.index("B_blank"), pl.index("U_acc"))

    def test_ship_max_damage_blue_acc_before_red_acc(self):
        pl = STRATEGY_PRIORITY_LISTS["ship"]["max_damage"]["reroll"]
        self.assertLess(pl.index("U_acc"), pl.index("R_acc"))

    def test_ship_max_damage_hits_not_in_list(self):
        pl = STRATEGY_PRIORITY_LISTS["ship"]["max_damage"]["reroll"]
        self.assertNotIn("R_hit", pl)
        self.assertNotIn("R_hit+hit", pl)
        self.assertNotIn("B_hit+crit", pl)

    # ship max_doubles ordering
    def test_ship_max_doubles_blank_before_hit(self):
        pl = STRATEGY_PRIORITY_LISTS["ship"]["max_doubles"]["reroll"]
        self.assertLess(pl.index("R_blank"), pl.index("R_hit"))
        self.assertLess(pl.index("U_acc"), pl.index("R_hit"))

    def test_ship_max_doubles_hit_before_crit(self):
        pl = STRATEGY_PRIORITY_LISTS["ship"]["max_doubles"]["reroll"]
        self.assertLess(pl.index("R_hit"), pl.index("R_crit"))

    def test_ship_max_doubles_doubles_not_in_list(self):
        pl = STRATEGY_PRIORITY_LISTS["ship"]["max_doubles"]["reroll"]
        self.assertNotIn("R_hit+hit", pl)
        self.assertNotIn("B_hit+crit", pl)

    # ship max_accuracy ordering
    def test_ship_max_accuracy_blank_before_hit(self):
        pl = STRATEGY_PRIORITY_LISTS["ship"]["max_accuracy"]["reroll"]
        self.assertLess(pl.index("R_blank"), pl.index("R_hit"))

    def test_ship_max_accuracy_blue_before_red(self):
        pl = STRATEGY_PRIORITY_LISTS["ship"]["max_accuracy"]["reroll"]
        self.assertLess(pl.index("U_hit"), pl.index("R_hit"))
        self.assertLess(pl.index("U_crit"), pl.index("R_crit"))

    def test_ship_max_accuracy_acc_not_in_list(self):
        pl = STRATEGY_PRIORITY_LISTS["ship"]["max_accuracy"]["reroll"]
        self.assertNotIn("R_acc", pl)
        self.assertNotIn("U_acc", pl)

    def test_ship_max_accuracy_black_not_in_list(self):
        pl = STRATEGY_PRIORITY_LISTS["ship"]["max_accuracy"]["reroll"]
        self.assertNotIn("B_blank", pl)
        self.assertNotIn("B_hit", pl)
        self.assertNotIn("B_hit+crit", pl)

    # ship max_crits ordering
    def test_ship_max_crits_blank_before_hit(self):
        pl = STRATEGY_PRIORITY_LISTS["ship"]["max_crits"]["reroll"]
        self.assertLess(pl.index("R_blank"), pl.index("R_hit"))
        self.assertLess(pl.index("U_acc"), pl.index("R_hit"))

    def test_ship_max_crits_crits_not_in_list(self):
        pl = STRATEGY_PRIORITY_LISTS["ship"]["max_crits"]["reroll"]
        self.assertNotIn("R_crit", pl)
        self.assertNotIn("U_crit", pl)
        self.assertNotIn("R_hit+hit", pl)
        self.assertNotIn("B_hit+crit", pl)

    # squad ordering
    def test_squad_crit_before_hit(self):
        for strategy in SQUAD_STRATEGIES:
            pl = STRATEGY_PRIORITY_LISTS["squad"][strategy]["reroll"]
            if "R_crit" in pl and "R_hit" in pl:
                self.assertLess(pl.index("R_crit"), pl.index("R_hit"),
                    f"squad {strategy}: R_crit should come before R_hit")


# ---------------------------------------------------------------------------
# 5.2 — build_strategy_pipeline
# ---------------------------------------------------------------------------

SHIP_ALL_FACES = [
    "R_blank", "B_blank", "R_acc", "U_acc",
    "R_hit", "U_hit", "B_hit", "R_crit", "U_crit",
    "R_hit+hit", "B_hit+crit",
]

BASE_PIPELINE = [
    AttackEffect(type="reroll", count=2, applicable_results=SHIP_ALL_FACES),
    AttackEffect(type="add_dice", dice_to_add={"black": 1}),
    AttackEffect(type="cancel", count=1, applicable_results=SHIP_ALL_FACES),
]


class TestBuildStrategyPipeline(unittest.TestCase):

    def test_reroll_priority_list_matches_strategy(self):
        result = build_strategy_pipeline(BASE_PIPELINE, "max_damage", "ship")
        self.assertEqual(result[0].priority_list, STRATEGY_PRIORITY_LISTS["ship"]["max_damage"]["reroll"])

    def test_reroll_count_preserved(self):
        result = build_strategy_pipeline(BASE_PIPELINE, "max_damage", "ship")
        self.assertEqual(result[0].count, 2)

    def test_reroll_applicable_results_not_mutated(self):
        result = build_strategy_pipeline(BASE_PIPELINE, "max_damage", "ship")
        self.assertEqual(set(result[0].applicable_results), set(SHIP_ALL_FACES))

    def test_add_dice_unchanged(self):
        result = build_strategy_pipeline(BASE_PIPELINE, "max_damage", "ship")
        self.assertEqual(result[1].dice_to_add, {"black": 1})

    def test_cancel_priority_list_matches_strategy(self):
        result = build_strategy_pipeline(BASE_PIPELINE, "max_damage", "ship")
        self.assertEqual(result[2].priority_list, STRATEGY_PRIORITY_LISTS["ship"]["max_damage"]["cancel"])

    def test_original_pipeline_not_mutated(self):
        build_strategy_pipeline(BASE_PIPELINE, "max_damage", "ship")
        self.assertEqual(set(BASE_PIPELINE[0].applicable_results), set(SHIP_ALL_FACES))

    def test_returns_new_list(self):
        result = build_strategy_pipeline(BASE_PIPELINE, "max_damage", "ship")
        self.assertIsNot(result, BASE_PIPELINE)

    def test_priority_list_filtered_to_applicable_results(self):
        blanks_only = [AttackEffect(type="reroll", count=1, applicable_results=["R_blank", "B_blank"])]
        result = build_strategy_pipeline(blanks_only, "max_damage", "ship")
        self.assertEqual(result[0].priority_list, ["R_blank", "B_blank"])

    def test_faces_not_in_strategy_excluded(self):
        hits_and_blanks = [AttackEffect(type="reroll", count=1, applicable_results=["R_hit", "R_blank", "B_blank"])]
        result = build_strategy_pipeline(hits_and_blanks, "max_damage", "ship")
        self.assertNotIn("R_hit", result[0].priority_list)
        self.assertEqual(set(result[0].priority_list), {"R_blank", "B_blank"})

    def test_strategy_order_preserved_in_filtered_list(self):
        hits_and_blanks = [AttackEffect(type="reroll", count=1, applicable_results=["R_hit", "R_blank", "B_blank"])]
        result = build_strategy_pipeline(hits_and_blanks, "max_doubles", "ship")
        self.assertLess(result[0].priority_list.index("R_blank"), result[0].priority_list.index("R_hit"))

    def test_add_dice_only_pipeline_unchanged(self):
        add_only = [AttackEffect(type="add_dice", count=1, applicable_results=["B_blank"])]
        result = build_strategy_pipeline(add_only, "max_accuracy", "ship")
        self.assertEqual(result[0].applicable_results, ["B_blank"])


# ---------------------------------------------------------------------------
# 5.3 — generate_report
# ---------------------------------------------------------------------------

class TestGenerateReport(unittest.TestCase):

    def setUp(self):
        self.pool = DicePool(red=2, blue=1, black=0, type="ship")
        self.pool_rb = DicePool(red=2, blue=1, black=1, type="ship")
        self.prio_pipeline = [AttackEffect(
            type="reroll", count=1,
            applicable_results=["R_blank", "B_blank", "R_acc", "U_acc",
                                "R_hit", "U_hit", "B_hit", "R_crit", "U_crit"],
        )]

    def test_single_strategy_returns_one_variant(self):
        variants = generate_report(self.pool, [], ["max_damage"])
        self.assertEqual(len(variants), 1)

    def test_variant_label_is_strategy_name(self):
        variants = generate_report(self.pool, [], ["max_damage"])
        self.assertEqual(variants[0]["label"], "max_damage")

    def test_variant_has_required_keys(self):
        variants = generate_report(self.pool, [], ["max_damage"])
        for key in ("damage", "accuracy", "crit"):
            self.assertIn(key, variants[0])

    def test_cumulative_damage_starts_at_zero(self):
        variants = generate_report(self.pool, [], ["max_damage"])
        self.assertEqual(variants[0]["damage"][0], (0, 1.0))

    def test_four_ship_strategies(self):
        strategies = ["max_damage", "max_doubles", "max_accuracy", "max_crits"]
        variants = generate_report(self.pool_rb, self.prio_pipeline, strategies)
        self.assertEqual(len(variants), 4)
        self.assertEqual([v["label"] for v in variants], strategies)

    def test_all_variants_damage_starts_at_zero(self):
        strategies = ["max_damage", "max_doubles", "max_accuracy", "max_crits"]
        variants = generate_report(self.pool_rb, self.prio_pipeline, strategies)
        for v in variants:
            self.assertEqual(v["damage"][0], (0, 1.0))

    def test_all_variants_crit_in_range(self):
        strategies = ["max_damage", "max_doubles", "max_accuracy", "max_crits"]
        variants = generate_report(self.pool_rb, self.prio_pipeline, strategies)
        for v in variants:
            self.assertGreaterEqual(v["crit"], 0.0)
            self.assertLessEqual(v["crit"], 1.0)

    def test_max_damage_ge_max_accuracy_at_threshold_1(self):
        pool = DicePool(red=2, blue=1, black=0, type="ship")
        pipeline = [AttackEffect(type="reroll", count=1,
            applicable_results=["R_blank", "R_acc", "U_acc", "R_hit", "U_hit", "U_crit"])]
        variants = generate_report(pool, pipeline, ["max_damage", "max_accuracy"])
        self.assertGreaterEqual(variants[0]["damage"][1][1], variants[1]["damage"][1][1])

    def test_max_doubles_max_damage_threshold(self):
        pool = DicePool(red=3, blue=0, black=0, type="ship")
        pipeline = [AttackEffect(type="reroll", count=2,
            applicable_results=["R_blank", "R_acc", "R_hit", "R_crit"])]
        variants = generate_report(pool, pipeline, ["max_damage", "max_doubles"])
        self.assertGreaterEqual(variants[1]["damage"][-1][0], variants[0]["damage"][-1][0])

    def test_unknown_strategy_raises(self):
        with self.assertRaises(ValueError):
            generate_report(self.pool_rb, self.prio_pipeline, ["unknown_strategy"])

    def test_default_strategy_is_max_damage(self):
        variants = generate_report(self.pool_rb, self.prio_pipeline)
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0]["label"], "max_damage")

    def test_empty_pipeline(self):
        variants = generate_report(self.pool_rb, [], ["max_damage"])
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0]["label"], "max_damage")


if __name__ == "__main__":
    unittest.main()
