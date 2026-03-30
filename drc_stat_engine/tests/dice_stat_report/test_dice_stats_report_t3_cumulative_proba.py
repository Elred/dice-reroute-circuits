"""
Tests for cumulative probability computations in report.py.
Covers: cumulative_damage, cumulative_accuracy, crit_probability

Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.1, 5.2

Run from stats/ directory:
    /home/elred/.virtualenvs/drc/bin/python -m unittest tests.test_dice_stats_report_cumulative_proba
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from drc_stat_engine.stats.dice_maths_combinatories import combine_dice
from drc_stat_engine.stats.report_engine import cumulative_damage, cumulative_accuracy, crit_probability

TOL = 1e-9

POOL_CONFIGS = [
    (1, 0, 0, "ship"),
    (0, 1, 0, "ship"),
    (0, 0, 1, "ship"),
    (2, 1, 0, "ship"),
    (1, 1, 1, "ship"),
    (3, 0, 2, "ship"),
    (1, 0, 0, "squad"),
    (0, 1, 0, "squad"),
    (0, 0, 1, "squad"),
    (2, 1, 1, "squad"),
]


def _make_damage_test(r, u, b, t):
    def test(self):
        roll_df = combine_dice(r, u, b, t)
        result = cumulative_damage(roll_df)
        label = f"{r}R {u}U {b}B {t}"

        # First entry threshold is 0
        self.assertEqual(result[0][0], 0, f"[{label}] first threshold should be 0")
        # P(damage >= 0) == 1.0
        self.assertAlmostEqual(result[0][1], 1.0, delta=TOL,
            msg=f"[{label}] P(damage>=0) should be 1.0")
        # Monotonically non-increasing
        probs = [p for _, p in result]
        for i in range(1, len(probs)):
            self.assertLessEqual(probs[i], probs[i-1] + TOL,
                msg=f"[{label}] not monotone at index {i}: {probs[i-1]} -> {probs[i]}")
        # All thresholds 0..max_damage covered
        thresholds = [x for x, _ in result]
        expected = list(range(0, int(roll_df["damage"].max()) + 1))
        self.assertEqual(thresholds, expected,
            msg=f"[{label}] thresholds {thresholds} != {expected}")
    return test


def _make_accuracy_test(r, u, b, t):
    def test(self):
        roll_df = combine_dice(r, u, b, t)
        result = cumulative_accuracy(roll_df)
        label = f"{r}R {u}U {b}B {t}"

        self.assertEqual(result[0][0], 0, f"[{label}] first threshold should be 0")
        self.assertAlmostEqual(result[0][1], 1.0, delta=TOL,
            msg=f"[{label}] P(acc>=0) should be 1.0")
        probs = [p for _, p in result]
        for i in range(1, len(probs)):
            self.assertLessEqual(probs[i], probs[i-1] + TOL,
                msg=f"[{label}] not monotone at index {i}")
    return test


def _make_crit_test(r, u, b, t):
    def test(self):
        roll_df = combine_dice(r, u, b, t)
        p = crit_probability(roll_df)
        label = f"{r}R {u}U {b}B {t}"
        self.assertGreaterEqual(p, 0.0 - TOL, msg=f"[{label}] crit_probability < 0")
        self.assertLessEqual(p, 1.0 + TOL, msg=f"[{label}] crit_probability > 1")
    return test


class TestCumulativeDamage(unittest.TestCase):
    pass

class TestCumulativeAccuracy(unittest.TestCase):
    pass

class TestCritProbability(unittest.TestCase):
    pass


for _r, _u, _b, _t in POOL_CONFIGS:
    _suffix = f"{_r}R_{_u}U_{_b}B_{_t}"
    setattr(TestCumulativeDamage,   f"test_{_suffix}", _make_damage_test(_r, _u, _b, _t))
    setattr(TestCumulativeAccuracy, f"test_{_suffix}", _make_accuracy_test(_r, _u, _b, _t))
    setattr(TestCritProbability,    f"test_{_suffix}", _make_crit_test(_r, _u, _b, _t))


# Keep the standalone runner for direct execution
def run_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (TestCumulativeDamage, TestCumulativeAccuracy, TestCritProbability):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=1, stream=sys.stdout)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    unittest.main()
