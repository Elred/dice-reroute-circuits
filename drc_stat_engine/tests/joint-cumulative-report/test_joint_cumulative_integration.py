"""
Integration tests for joint_cumulative in generate_report.

Feature: joint-cumulative-report
"""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.report_engine import generate_report
from drc_stat_engine.stats.dice_models import DicePool, DefenseEffect


def test_joint_cumulative_key_exists_in_variant():
    """
    Test that joint_cumulative key exists in each variant when calling
    generate_report with a simple pool (1 Red ship die, no defense).
    Requirements: 2.1, 2.2
    """
    pool = DicePool(red=1, blue=0, black=0, type="ship")
    variants = generate_report(pool, pipeline=[], strategies=["max_damage"])

    assert len(variants) == 1
    variant = variants[0]
    assert "joint_cumulative" in variant, \
        f"Expected 'joint_cumulative' key in variant, got keys: {list(variant.keys())}"

    jc = variant["joint_cumulative"]
    assert "damage_thresholds" in jc
    assert "accuracy_thresholds" in jc
    assert "matrix" in jc
    assert isinstance(jc["matrix"], list)
    assert len(jc["matrix"]) > 0
    assert isinstance(jc["matrix"][0], list)
    print("PASS: joint_cumulative key exists in non-defense variant")


def test_joint_cumulative_in_defense_branches():
    """
    Test that joint_cumulative appears in both pre_defense and post_defense
    when a defense pipeline is provided.
    Requirements: 2.1, 2.2, 2.3
    """
    pool = DicePool(red=2, blue=0, black=0, type="ship")
    defense_pipeline = [
        DefenseEffect(type="reduce_damage", amount=1),
    ]
    variants = generate_report(
        pool, pipeline=[], strategies=["max_damage"],
        defense_pipeline=defense_pipeline,
    )

    assert len(variants) == 1
    variant = variants[0]

    # Defense branch should have pre_defense and post_defense
    assert "pre_defense" in variant, \
        f"Expected 'pre_defense' key, got keys: {list(variant.keys())}"
    assert "post_defense" in variant, \
        f"Expected 'post_defense' key, got keys: {list(variant.keys())}"

    # Both should contain joint_cumulative
    assert "joint_cumulative" in variant["pre_defense"], \
        f"Expected 'joint_cumulative' in pre_defense, got keys: {list(variant['pre_defense'].keys())}"
    assert "joint_cumulative" in variant["post_defense"], \
        f"Expected 'joint_cumulative' in post_defense, got keys: {list(variant['post_defense'].keys())}"

    # Verify structure
    for branch_name in ("pre_defense", "post_defense"):
        jc = variant[branch_name]["joint_cumulative"]
        assert "damage_thresholds" in jc
        assert "accuracy_thresholds" in jc
        assert "matrix" in jc
        assert abs(jc["matrix"][0][0] - 1.0) < 1e-12, \
            f"{branch_name}: matrix[0][0] should be 1.0, got {jc['matrix'][0][0]}"

    print("PASS: joint_cumulative exists in both pre_defense and post_defense")


def test_known_value_1_red_ship():
    """
    Test a known-value scenario with 1 Red ship die where matrix values
    can be manually verified.

    Red ship die faces (from profiles.py):
    - R_blank: proba=0.25, damage=0, crit=0, acc=0, blank=1
    - R_hit: proba=0.25, damage=1, crit=0, acc=0, blank=0
    - R_crit: proba=0.25, damage=1, crit=1, acc=0, blank=0
    - R_acc: proba=0.125, damage=0, crit=0, acc=1, blank=0
    - R_hit+hit: proba=0.125, damage=2, crit=0, acc=0, blank=0

    max_damage = 2, max_acc = 1
    damage_thresholds = [0, 1, 2]
    accuracy_thresholds = [0, 1]

    Expected matrix:
    P(dmg>=0, acc>=0) = 1.0
    P(dmg>=0, acc>=1) = 0.125 (only R_acc)
    P(dmg>=1, acc>=0) = 0.25 + 0.25 + 0.125 = 0.625 (R_hit + R_crit + R_hit+hit)
    P(dmg>=1, acc>=1) = 0.0 (no face has both dmg>=1 and acc>=1)
    P(dmg>=2, acc>=0) = 0.125 (R_hit+hit)
    P(dmg>=2, acc>=1) = 0.0

    Requirements: 2.1, 2.2
    """
    pool = DicePool(red=1, blue=0, black=0, type="ship")
    variants = generate_report(pool, pipeline=[], strategies=["max_damage"])

    jc = variants[0]["joint_cumulative"]

    assert jc["damage_thresholds"] == [0, 1, 2], \
        f"Expected [0, 1, 2], got {jc['damage_thresholds']}"
    assert jc["accuracy_thresholds"] == [0, 1], \
        f"Expected [0, 1], got {jc['accuracy_thresholds']}"

    matrix = jc["matrix"]
    assert len(matrix) == 3, f"Expected 3 rows, got {len(matrix)}"
    assert len(matrix[0]) == 2, f"Expected 2 columns, got {len(matrix[0])}"

    # Verify known values
    tol = 1e-12
    assert abs(matrix[0][0] - 1.0) < tol, f"matrix[0][0] = {matrix[0][0]}, expected 1.0"
    assert abs(matrix[0][1] - 0.125) < tol, f"matrix[0][1] = {matrix[0][1]}, expected 0.125"
    assert abs(matrix[1][0] - 0.625) < tol, f"matrix[1][0] = {matrix[1][0]}, expected 0.625"
    assert abs(matrix[1][1] - 0.0) < tol, f"matrix[1][1] = {matrix[1][1]}, expected 0.0"
    assert abs(matrix[2][0] - 0.125) < tol, f"matrix[2][0] = {matrix[2][0]}, expected 0.125"
    assert abs(matrix[2][1] - 0.0) < tol, f"matrix[2][1] = {matrix[2][1]}, expected 0.0"

    print("PASS: known-value test for 1 Red ship die")


if __name__ == "__main__":
    try:
        test_joint_cumulative_key_exists_in_variant()
    except Exception as e:
        print(f"FAIL: test_joint_cumulative_key_exists_in_variant — {e}")
        sys.exit(1)

    try:
        test_joint_cumulative_in_defense_branches()
    except Exception as e:
        print(f"FAIL: test_joint_cumulative_in_defense_branches — {e}")
        sys.exit(1)

    try:
        test_known_value_1_red_ship()
    except Exception as e:
        print(f"FAIL: test_known_value_1_red_ship — {e}")
        sys.exit(1)

    print("\nAll integration tests passed.")
