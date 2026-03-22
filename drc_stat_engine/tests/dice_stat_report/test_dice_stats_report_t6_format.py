"""
Tests for task 6.2: format_report output.
Covers header content, damage table formatting, strategy labeling, and single-variant behavior.
Requirements: 7.2, 7.3, 7.6
"""
import sys
import os
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'stats'))

from report import DicePool, Operation, format_report

POOL_3R2B = DicePool(red=3, blue=0, black=2, type="ship")

PIPELINE_REROLL = [
    Operation(type="reroll", count=1, applicable_results=["R_blank", "B_blank"]),
    Operation(type="cancel", count=2, applicable_results=["R_blank", "B_blank", "R_hit"]),
]

SINGLE_VARIANT = [
    {
        "label": "max_damage",
        "damage": [(0, 1.0), (1, 0.753), (2, 0.438)],
        "accuracy": [(0, 1.0), (1, 0.188)],
        "crit": 0.438,
    }
]

MULTI_VARIANTS = [
    {
        "label": "max_damage",
        "damage": [(0, 1.0), (1, 0.753), (2, 0.438)],
        "accuracy": [(0, 1.0), (1, 0.188)],
        "crit": 0.438,
    },
    {
        "label": "max_accuracy",
        "damage": [(0, 1.0), (1, 0.600), (2, 0.300)],
        "accuracy": [(0, 1.0), (1, 0.500)],
        "crit": 0.200,
    },
]


class TestFormatReportHeader(unittest.TestCase):
    """7.2 — Header contains dice pool counts and type."""

    def setUp(self):
        self.output = format_report(POOL_3R2B, PIPELINE_REROLL, SINGLE_VARIANT)
        self.header = self.output.splitlines()[0]

    def test_header_contains_red_count(self):
        self.assertIn("3R", self.header)

    def test_header_contains_blue_count(self):
        self.assertIn("0U", self.header)

    def test_header_contains_black_count(self):
        self.assertIn("2B", self.header)

    def test_header_contains_dice_type(self):
        self.assertIn("ship", self.header)

    def test_pipeline_line_present(self):
        pipeline_line = self.output.splitlines()[1]
        self.assertIn("Pipeline:", pipeline_line)

    def test_pipeline_line_contains_op_type(self):
        pipeline_line = self.output.splitlines()[1]
        self.assertIn("reroll", pipeline_line)


class TestFormatReportDamageTable(unittest.TestCase):
    """7.3 — Damage/accuracy table rows formatted as percentages."""

    def setUp(self):
        self.output = format_report(POOL_3R2B, PIPELINE_REROLL, SINGLE_VARIANT)

    def test_damage_threshold_0_shows_100_percent(self):
        self.assertIn("100.00%", self.output)

    def test_damage_threshold_1_shows_75_30_percent(self):
        self.assertIn("75.30%", self.output)

    def test_damage_threshold_2_shows_43_80_percent(self):
        self.assertIn("43.80%", self.output)

    def test_accuracy_threshold_1_shows_18_80_percent(self):
        self.assertIn("18.80%", self.output)

    def test_crit_probability_line(self):
        self.assertIn("Crit Probability: 43.80%", self.output)


class TestFormatReportMultiVariant(unittest.TestCase):
    """7.6 — Multiple variants: strategy sections labeled correctly."""

    def setUp(self):
        self.output = format_report(POOL_3R2B, PIPELINE_REROLL, MULTI_VARIANTS)

    def test_contains_max_damage_label(self):
        self.assertIn("Strategy: max_damage", self.output)

    def test_contains_max_accuracy_label(self):
        self.assertIn("Strategy: max_accuracy", self.output)

    def test_contains_separator(self):
        self.assertIn("=" * 10, self.output)


class TestFormatReportSingleVariant(unittest.TestCase):
    """6.5 / 7.6 — Single variant still shows strategy label."""

    def test_single_variant_shows_strategy_label(self):
        output = format_report(POOL_3R2B, PIPELINE_REROLL, SINGLE_VARIANT)
        self.assertIn("Strategy:", output)


class TestFormatReportEmptyPipeline(unittest.TestCase):
    """Empty pipeline shows '(none)' in pipeline line."""

    def test_empty_pipeline_shows_none(self):
        output = format_report(DicePool(red=1, blue=0, black=0, type="ship"), [], SINGLE_VARIANT)
        self.assertIn("(none)", output)


if __name__ == "__main__":
    unittest.main()
