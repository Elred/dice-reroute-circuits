"""
Checkpoint test runner — runs all dice_stat_report tests (t1, t2, t3).
Run from project root:
    /home/elred/.virtualenvs/drc/bin/python drc_stat_engine/tests/dice_stat_report/test_dice_stats_report_t4_checkpoint.py
"""
import sys
import os
import unittest
import importlib.util

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, '..', '..', '..', '..'))


def _load(filename):
    path = os.path.join(_HERE, filename)
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


t_validation  = _load("test_dice_stats_report_t1_validation.py")
t_pipeline    = _load("test_dice_stats_report_t2_pipeline.py")
t_cumulative  = _load("test_dice_stats_report_t3_cumulative_proba.py")

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(t_validation))
    suite.addTests(loader.loadTestsFromModule(t_pipeline))
    suite.addTests(loader.loadTestsFromModule(t_cumulative))

    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    print(f"\nOVERALL: {'ALL PASS' if result.wasSuccessful() else 'SOME FAILURES'}")
    sys.exit(0 if result.wasSuccessful() else 1)
