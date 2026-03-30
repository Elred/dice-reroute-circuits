"""
Tests for Task 1 — core data structures and input validation in report.py.
Covers: DicePool, AttackEffect, validate_dice_pool, validate_attack_effect_pipeline

Requirements: 1.1, 1.2, 1.3, 1.4, 2.3, 2.5

Run from stats/ directory:
    /home/elred/.virtualenvs/drc/bin/python -m unittest tests.test_dice_stats_report_validation
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from drc_stat_engine.stats.dice_models import DicePool, AttackEffect, validate_dice_pool, validate_attack_effect_pipeline


# ---------------------------------------------------------------------------
# DicePool dataclass
# ---------------------------------------------------------------------------

class TestDicePool(unittest.TestCase):

    def test_defaults(self):
        p = DicePool()
        self.assertEqual(p.red, 0)
        self.assertEqual(p.blue, 0)
        self.assertEqual(p.black, 0)
        self.assertEqual(p.type, "ship")

    def test_stores_fields(self):
        p = DicePool(red=2, blue=1, black=3, type="squad")
        self.assertEqual(p.red, 2)
        self.assertEqual(p.blue, 1)
        self.assertEqual(p.black, 3)
        self.assertEqual(p.type, "squad")


# ---------------------------------------------------------------------------
# AttackEffect dataclass
# ---------------------------------------------------------------------------

class TestAttackEffect(unittest.TestCase):

    def test_defaults(self):
        op = AttackEffect(type="reroll")
        self.assertEqual(op.count, 1)
        self.assertEqual(op.applicable_results, [])
        self.assertEqual(op.priority_list, [])

    def test_stores_fields(self):
        op = AttackEffect(type="cancel", count=3, applicable_results=["R_blank", "B_blank"])
        self.assertEqual(op.type, "cancel")
        self.assertEqual(op.count, 3)
        self.assertEqual(op.applicable_results, ["R_blank", "B_blank"])

    def test_applicable_results_not_shared(self):
        # Mutable default must not be shared between instances
        op1 = AttackEffect(type="reroll")
        op2 = AttackEffect(type="cancel")
        op1.applicable_results.append("R_blank")
        self.assertEqual(op2.applicable_results, [], "applicable_results default is shared — use field(default_factory=list)")


# ---------------------------------------------------------------------------
# validate_dice_pool — Requirement 1.1: valid pools accepted
# ---------------------------------------------------------------------------

class TestValidateDicePoolValid(unittest.TestCase):

    def test_valid_ship_pool(self):
        validate_dice_pool(DicePool(red=1, blue=0, black=0, type="ship"))

    def test_valid_squad_pool(self):
        validate_dice_pool(DicePool(red=0, blue=2, black=1, type="squad"))

    def test_valid_all_colors(self):
        validate_dice_pool(DicePool(red=3, blue=2, black=1, type="ship"))


# ---------------------------------------------------------------------------
# validate_dice_pool — Requirement 1.2: empty pool rejected
# ---------------------------------------------------------------------------

class TestValidateDicePoolEmpty(unittest.TestCase):

    def test_empty_pool_raises(self):
        with self.assertRaises(ValueError) as ctx:
            validate_dice_pool(DicePool(red=0, blue=0, black=0, type="ship"))
        self.assertIn("empty", str(ctx.exception).lower())


# ---------------------------------------------------------------------------
# validate_dice_pool — Requirement 1.3: negative / non-integer counts rejected
# ---------------------------------------------------------------------------

class TestValidateDicePoolCounts(unittest.TestCase):

    def test_negative_red(self):
        with self.assertRaises(ValueError):
            validate_dice_pool(DicePool(red=-1, blue=0, black=1, type="ship"))

    def test_negative_blue(self):
        with self.assertRaises(ValueError):
            validate_dice_pool(DicePool(red=1, blue=-2, black=0, type="ship"))

    def test_negative_black(self):
        with self.assertRaises(ValueError):
            validate_dice_pool(DicePool(red=1, blue=0, black=-1, type="ship"))

    def test_float_count(self):
        with self.assertRaises(ValueError):
            validate_dice_pool(DicePool(red=1.5, blue=0, black=0, type="ship"))

    def test_string_count(self):
        with self.assertRaises((ValueError, TypeError)):
            validate_dice_pool(DicePool(red="two", blue=0, black=0, type="ship"))


# ---------------------------------------------------------------------------
# validate_dice_pool — Requirement 1.4: invalid type rejected
# ---------------------------------------------------------------------------

class TestValidateDicePoolType(unittest.TestCase):

    def test_invalid_type(self):
        with self.assertRaises(ValueError) as ctx:
            validate_dice_pool(DicePool(red=1, blue=0, black=0, type="fighter"))
        self.assertTrue(
            "fighter" in str(ctx.exception) or "type" in str(ctx.exception).lower()
        )

    def test_empty_type(self):
        with self.assertRaises(ValueError):
            validate_dice_pool(DicePool(red=1, blue=0, black=0, type=""))

    def test_type_case_sensitive(self):
        with self.assertRaises(ValueError):
            validate_dice_pool(DicePool(red=1, blue=0, black=0, type="Ship"))


# ---------------------------------------------------------------------------
# validate_attack_effect_pipeline — Requirement 2.5: unknown op types rejected
# ---------------------------------------------------------------------------

class TestValidatePipelineOpTypes(unittest.TestCase):

    def test_unknown_op_raises(self):
        pool = DicePool(red=2, blue=0, black=0, type="ship")
        with self.assertRaises(ValueError) as ctx:
            validate_attack_effect_pipeline([AttackEffect(type="explode")], pool)
        self.assertIn("explode", str(ctx.exception))

    def test_all_known_op_types_accepted(self):
        pool = DicePool(red=1, blue=1, black=1, type="ship")
        validate_attack_effect_pipeline([
            AttackEffect(type="reroll", count=1, applicable_results=["R_blank"]),
            AttackEffect(type="cancel", count=1, applicable_results=["B_blank"]),
            AttackEffect(type="add_dice", applicable_results=["U_hit"]),
        ], pool)

    def test_empty_pipeline_accepted(self):
        pool = DicePool(red=2, blue=1, black=0, type="squad")
        validate_attack_effect_pipeline([], pool)


# ---------------------------------------------------------------------------
# validate_attack_effect_pipeline — Requirement 2.3: applicable_results not validated against pool
# ---------------------------------------------------------------------------

class TestValidatePipelineFaces(unittest.TestCase):

    def test_face_not_in_pool_reroll_is_accepted(self):
        # applicable_results outside the pool is valid — it's a no-op at runtime
        pool = DicePool(red=2, blue=0, black=0, type="ship")
        validate_attack_effect_pipeline(
            [AttackEffect(type="reroll", count=1, applicable_results=["U_acc"])], pool
        )

    def test_face_not_in_pool_cancel_is_accepted(self):
        pool = DicePool(red=0, blue=0, black=1, type="ship")
        validate_attack_effect_pipeline(
            [AttackEffect(type="cancel", count=1, applicable_results=["R_blank"])], pool
        )

    def test_valid_faces_accepted(self):
        pool = DicePool(red=1, blue=0, black=1, type="ship")
        validate_attack_effect_pipeline(
            [AttackEffect(type="reroll", count=1, applicable_results=["R_blank", "B_blank"])], pool
        )

    def test_made_up_face_accepted(self):
        # No face validation — made-up faces are silently ignored at runtime
        pool = DicePool(red=1, blue=0, black=0, type="ship")
        validate_attack_effect_pipeline(
            [AttackEffect(type="cancel", count=1, applicable_results=["X_invalid"])], pool
        )

    def test_add_dice_not_validated_against_pool(self):
        pool = DicePool(red=1, blue=0, black=0, type="ship")
        validate_attack_effect_pipeline(
            [AttackEffect(type="add_dice", applicable_results=["U_hit"])], pool
        )

    def test_second_op_out_of_pool_accepted(self):
        pool = DicePool(red=1, blue=0, black=0, type="ship")
        validate_attack_effect_pipeline([
            AttackEffect(type="reroll", count=1, applicable_results=["R_blank"]),
            AttackEffect(type="reroll", count=1, applicable_results=["U_acc"]),
        ], pool)


if __name__ == "__main__":
    unittest.main()
