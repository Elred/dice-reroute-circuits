"""
Tests for the attack effect pipeline executor in report.py.
Covers: apply_attack_effect, run_pipeline, and probability integrity property tests.

Requirements: 2.1, 2.2, 2.4, 2.5, 8.1, 8.2

Run from stats/ directory:
    /home/elred/.virtualenvs/drc/bin/python -m unittest tests.test_dice_stats_report_pipeline
"""
import sys
import os
import unittest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from drc_stat_engine.stats.dice_maths_combinatories import combine_dice
from drc_stat_engine.stats.dice_models import DicePool, AttackEffect
from drc_stat_engine.stats.report_engine import apply_attack_effect, run_pipeline

TOL = 1e-9


# ---------------------------------------------------------------------------
# apply_attack_effect — reroll
# ---------------------------------------------------------------------------

class TestApplyAttackEffectReroll(unittest.TestCase):

    def setUp(self):
        self.roll_2r = combine_dice(2, 0, 0, "ship")

    def test_returns_dataframe(self):
        result = apply_attack_effect(self.roll_2r, AttackEffect(type="reroll", count=1, priority_list=["R_blank"]), "ship")
        self.assertTrue(hasattr(result, "columns"))

    def test_probabilities_sum_to_one(self):
        result = apply_attack_effect(self.roll_2r, AttackEffect(type="reroll", count=1, priority_list=["R_blank"]), "ship")
        self.assertAlmostEqual(result["proba"].sum(), 1.0, delta=TOL)

    def test_reduces_blank_probability(self):
        result = apply_attack_effect(self.roll_2r, AttackEffect(type="reroll", count=1, priority_list=["R_blank"]), "ship")
        before = self.roll_2r[self.roll_2r["blank"] == 0]["proba"].sum()
        after = result[result["blank"] == 0]["proba"].sum()
        self.assertGreater(after, before)


# ---------------------------------------------------------------------------
# apply_attack_effect — cancel
# ---------------------------------------------------------------------------

class TestApplyAttackEffectCancel(unittest.TestCase):

    def setUp(self):
        self.roll = combine_dice(1, 0, 1, "ship")

    def test_returns_dataframe(self):
        result = apply_attack_effect(self.roll, AttackEffect(type="cancel", count=1, priority_list=["R_blank", "B_blank"]), "ship")
        self.assertTrue(hasattr(result, "columns"))

    def test_probabilities_sum_to_one(self):
        result = apply_attack_effect(self.roll, AttackEffect(type="cancel", count=1, priority_list=["R_blank", "B_blank"]), "ship")
        self.assertAlmostEqual(result["proba"].sum(), 1.0, delta=TOL)


# ---------------------------------------------------------------------------
# apply_attack_effect — add_dice
# ---------------------------------------------------------------------------

class TestApplyAttackEffectAddDice(unittest.TestCase):

    def setUp(self):
        self.roll = combine_dice(1, 0, 0, "ship")

    def test_returns_dataframe(self):
        result = apply_attack_effect(self.roll, AttackEffect(type="add_dice", dice_to_add={"black": 2}), "ship")
        self.assertTrue(hasattr(result, "columns"))

    def test_probabilities_sum_to_one(self):
        result = apply_attack_effect(self.roll, AttackEffect(type="add_dice", dice_to_add={"black": 2}), "ship")
        self.assertAlmostEqual(result["proba"].sum(), 1.0, delta=TOL)

    def test_value_has_more_tokens(self):
        result = apply_attack_effect(self.roll, AttackEffect(type="add_dice", dice_to_add={"black": 2}), "ship")
        sample_val = result["value"].iloc[0]
        self.assertGreaterEqual(len(sample_val.split()), 2)


# ---------------------------------------------------------------------------
# apply_attack_effect — unknown type
# ---------------------------------------------------------------------------

class TestApplyAttackEffectUnknownType(unittest.TestCase):

    def test_raises_value_error(self):
        roll = combine_dice(1, 0, 0, "ship")
        with self.assertRaises(ValueError):
            apply_attack_effect(roll, AttackEffect(type="explode"), "ship")


# ---------------------------------------------------------------------------
# run_pipeline
# ---------------------------------------------------------------------------

class TestRunPipeline(unittest.TestCase):

    def test_empty_pipeline_returns_same_df(self):
        roll = combine_dice(2, 1, 0, "ship")
        result = run_pipeline(roll, [], "ship")
        self.assertIs(result, roll)

    def test_multi_step_returns_dataframe(self):
        roll = combine_dice(2, 0, 1, "ship")
        pipeline = [
            AttackEffect(type="reroll", count=1, priority_list=["R_blank", "B_blank"]),
            AttackEffect(type="cancel", count=1, priority_list=["R_blank", "B_blank"]),
        ]
        result = run_pipeline(roll, pipeline, "ship")
        self.assertTrue(hasattr(result, "columns"))

    def test_multi_step_probabilities_sum_to_one(self):
        roll = combine_dice(2, 0, 1, "ship")
        pipeline = [
            AttackEffect(type="reroll", count=1, priority_list=["R_blank", "B_blank"]),
            AttackEffect(type="cancel", count=1, priority_list=["R_blank", "B_blank"]),
        ]
        result = run_pipeline(roll, pipeline, "ship")
        self.assertAlmostEqual(result["proba"].sum(), 1.0, delta=TOL)

    def test_integrity_check_raises_on_bad_proba(self):
        import drc_stat_engine.stats.report_engine as rmod
        _orig = rmod.apply_attack_effect

        def _bad_apply(roll_df, op, type_str, backend_mod=None):
            df = _orig(roll_df, op, type_str, backend_mod=backend_mod).copy()
            df["proba"] = df["proba"] * 2
            return df

        rmod.apply_attack_effect = _bad_apply
        try:
            roll = combine_dice(1, 0, 0, "ship")
            with self.assertRaises(ValueError) as ctx:
                run_pipeline(roll, [AttackEffect(type="reroll", count=1, priority_list=["R_blank"])], "ship")
            self.assertIn("Probability integrity", str(ctx.exception))
        finally:
            rmod.apply_attack_effect = _orig


# ---------------------------------------------------------------------------
# Property test: probabilities sum to 1.0 after any single operation
# Requirement 8.1
# ---------------------------------------------------------------------------

# (description, (red, blue, black, type_str), attack_effect)
_INTEGRITY_CASES = [
    # reroll
    ("reroll 1 blank, 2R ship",       (2, 0, 0, "ship"),  AttackEffect(type="reroll", count=1, priority_list=["R_blank"])),
    ("reroll 2 blanks, 3R ship",      (3, 0, 0, "ship"),  AttackEffect(type="reroll", count=2, priority_list=["R_blank"])),
    ("reroll 1 blank, 1R1U ship",     (1, 1, 0, "ship"),  AttackEffect(type="reroll", count=1, priority_list=["R_blank"])),
    ("reroll 1 blank, 1R1B ship",     (1, 0, 1, "ship"),  AttackEffect(type="reroll", count=1, priority_list=["R_blank", "B_blank"])),
    ("reroll 1 blank, 1R1U1B ship",   (1, 1, 1, "ship"),  AttackEffect(type="reroll", count=1, priority_list=["R_blank", "B_blank"])),
    ("reroll 1 blank, 2R squad",      (2, 0, 0, "squad"), AttackEffect(type="reroll", count=1, priority_list=["R_blank"])),
    ("reroll 1 blank, 1R1B squad",    (1, 0, 1, "squad"), AttackEffect(type="reroll", count=1, priority_list=["R_blank", "B_blank"])),
    ("reroll 2 blanks, 2R1B ship",    (2, 0, 1, "ship"),  AttackEffect(type="reroll", count=2, priority_list=["R_blank", "B_blank"])),
    # cancel
    ("cancel 1 blank, 2R ship",       (2, 0, 0, "ship"),  AttackEffect(type="cancel", count=1, priority_list=["R_blank"])),
    ("cancel 1 blank, 1R1B ship",     (1, 0, 1, "ship"),  AttackEffect(type="cancel", count=1, priority_list=["R_blank", "B_blank"])),
    ("cancel 2 blanks, 3R ship",      (3, 0, 0, "ship"),  AttackEffect(type="cancel", count=2, priority_list=["R_blank"])),
    ("cancel 1 blank, 1R1U1B ship",   (1, 1, 1, "ship"),  AttackEffect(type="cancel", count=1, priority_list=["R_blank", "B_blank"])),
    ("cancel 1 blank, 2R squad",      (2, 0, 0, "squad"), AttackEffect(type="cancel", count=1, priority_list=["R_blank"])),
    ("cancel 1 blank, 1R1B squad",    (1, 0, 1, "squad"), AttackEffect(type="cancel", count=1, priority_list=["R_blank", "B_blank"])),
    # add_dice
    ("add_dice 1B, 1R ship",          (1, 0, 0, "ship"),  AttackEffect(type="add_dice", dice_to_add={"black": 1})),
    ("add_dice 1R, 1U ship",          (0, 1, 0, "ship"),  AttackEffect(type="add_dice", dice_to_add={"red": 1})),
    ("add_dice 2B, 2R ship",          (2, 0, 0, "ship"),  AttackEffect(type="add_dice", dice_to_add={"black": 2})),
    ("add_dice 1R, 1B squad",         (0, 0, 1, "squad"), AttackEffect(type="add_dice", dice_to_add={"red": 1})),
    ("add_dice 1U, 1R1B ship",        (1, 0, 1, "ship"),  AttackEffect(type="add_dice", dice_to_add={"blue": 1})),
]


def _make_integrity_test(desc, pool_args, attack_effect):
    def test(self):
        red, blue, black, type_str = pool_args
        roll_df = combine_dice(red, blue, black, type_str)
        result = apply_attack_effect(roll_df, attack_effect, type_str)
        total = result["proba"].sum()
        self.assertAlmostEqual(
            total, 1.0, delta=TOL,
            msg=f"[{attack_effect.type}] {desc}: proba sum={total:.15f}"
        )
    return test


class TestProbabilityIntegrityAfterSingleOp(unittest.TestCase):
    pass


for _desc, _pool, _op in _INTEGRITY_CASES:
    _name = "test_" + _desc.replace(" ", "_").replace(",", "").replace("+", "plus")
    setattr(TestProbabilityIntegrityAfterSingleOp, _name, _make_integrity_test(_desc, _pool, _op))


if __name__ == "__main__":
    unittest.main()
