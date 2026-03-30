"""
Unit tests for change_die_face in dice.py.
Feature: set-die-result
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
from drc_stat_engine.stats.dice_maths_combinatories import (
    change_die_face, combine_dice, _resolve_color_agnostic_result, _all_pool_results,
)

PASS = "PASS"
FAIL = "FAIL"

def run(name, fn):
    try:
        fn()
        print(f"{PASS}: {name}")
    except Exception as e:
        print(f"{FAIL}: {name} — {e}")


# ---------------------------------------------------------------------------
# Test 1: No-op when source face absent
# ---------------------------------------------------------------------------
def test_noop_when_source_absent():
    roll_df = combine_dice(1, 0, 0, "ship")
    result_df = change_die_face(roll_df, ["U_hit"], "R_blank", "ship")
    left = roll_df.sort_values("value").reset_index(drop=True)
    right = result_df.sort_values("value").reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right)


# ---------------------------------------------------------------------------
# Test 2: Correct substitution for single-die roll
# ---------------------------------------------------------------------------
def test_substitution_single_die():
    roll_df = combine_dice(1, 0, 0, "ship")
    result_df = change_die_face(roll_df, ["R_blank"], "R_hit", "ship")

    # R_blank row should be gone; R_hit row should have doubled proba
    assert "R_blank" not in result_df["value"].values, "R_blank should be replaced"
    r_hit_row = result_df[result_df["value"] == "R_hit"]
    assert not r_hit_row.empty, "R_hit row should exist"
    # Original R_hit proba=0.25, R_blank proba=0.25 → combined = 0.5
    assert abs(r_hit_row.iloc[0]["proba"] - 0.5) < 1e-9, (
        f"Expected R_hit proba=0.5, got {r_hit_row.iloc[0]['proba']}"
    )


# ---------------------------------------------------------------------------
# Test 3: Correct stat column adjustment after substitution
# ---------------------------------------------------------------------------
def test_stat_column_adjustment():
    roll_df = combine_dice(1, 0, 0, "ship")
    result_df = change_die_face(roll_df, ["R_blank"], "R_crit", "ship")

    r_crit_row = result_df[result_df["value"] == "R_crit"]
    assert not r_crit_row.empty
    row = r_crit_row.iloc[0]
    assert row["damage"] == 1, f"Expected damage=1, got {row['damage']}"
    assert row["crit"] == 1, f"Expected crit=1, got {row['crit']}"
    assert row["acc"] == 0, f"Expected acc=0, got {row['acc']}"
    assert row["blank"] == 0, f"Expected blank=0, got {row['blank']}"


# ---------------------------------------------------------------------------
# Test 4: Aggregation when two outcomes collapse to same value string
# ---------------------------------------------------------------------------
def test_aggregation_on_collapse():
    roll_df = combine_dice(1, 0, 1, "ship")
    result_df = change_die_face(roll_df, ["B_blank"], "R_blank", "ship")

    # Probabilities must still sum to 1.0
    total = result_df["proba"].sum()
    assert abs(total - 1.0) < 1e-9, f"Proba sum {total} != 1.0"

    # No duplicate value strings
    assert result_df["value"].nunique() == len(result_df), "Duplicate value strings found after aggregation"


# ---------------------------------------------------------------------------
# Test 5: Color-agnostic resolution picks highest-scoring face (ship)
# ---------------------------------------------------------------------------
def test_color_agnostic_resolution_ship():
    # "hit" → should resolve to the face with highest damage+crit+acc among R_hit, U_hit, B_hit
    # All have damage=1, crit=0, acc=0 → score=1. Tie-break by damage desc (all equal),
    # crit desc (all equal), acc desc (all equal) → first encountered wins.
    resolved = _resolve_color_agnostic_result("hit", "ship")
    all_faces = _all_pool_results("ship")
    candidates = [f for f in all_faces if f["value"].split("_", 1)[-1] == "hit"]
    max_score = max(f["damage"] + f["crit"] + f["acc"] for f in candidates)
    resolved_face = next(f for f in all_faces if f["value"] == resolved)
    resolved_score = resolved_face["damage"] + resolved_face["crit"] + resolved_face["acc"]
    assert resolved_score == max_score, f"Resolved '{resolved}' score {resolved_score} != max {max_score}"


# ---------------------------------------------------------------------------
# Test 6: Color-agnostic resolution for each type_str
# ---------------------------------------------------------------------------
def test_color_agnostic_resolution_squad():
    # "hit+crit" for squad: B_hit+crit has damage=1,crit=0,acc=0 (squad)
    resolved = _resolve_color_agnostic_result("hit+crit", "squad")
    assert resolved == "B_hit+crit", f"Expected B_hit+crit, got {resolved}"


def test_color_agnostic_resolution_crit_ship():
    # "crit" for ship: R_crit (damage=1,crit=1,acc=0,score=2) vs U_crit (same) → first wins
    resolved = _resolve_color_agnostic_result("crit", "ship")
    all_faces = _all_pool_results("ship")
    candidates = [f for f in all_faces if f["value"].split("_", 1)[-1] == "crit"]
    max_score = max(f["damage"] + f["crit"] + f["acc"] for f in candidates)
    resolved_face = next(f for f in all_faces if f["value"] == resolved)
    assert resolved_face["damage"] + resolved_face["crit"] + resolved_face["acc"] == max_score


def test_color_agnostic_resolution_blank():
    # "blank" → R_blank or B_blank, both score=0
    resolved = _resolve_color_agnostic_result("blank", "ship")
    assert resolved in ["R_blank", "B_blank"], f"Unexpected resolved blank: {resolved}"


def test_color_agnostic_resolution_hit_plus_hit():
    # "hit+hit" → only R_hit+hit exists (ship)
    resolved = _resolve_color_agnostic_result("hit+hit", "ship")
    assert resolved == "R_hit+hit", f"Expected R_hit+hit, got {resolved}"


if __name__ == "__main__":
    run("No-op when source face absent", test_noop_when_source_absent)
    run("Correct substitution for single-die roll", test_substitution_single_die)
    run("Correct stat column adjustment", test_stat_column_adjustment)
    run("Aggregation when outcomes collapse", test_aggregation_on_collapse)
    run("Color-agnostic resolution picks highest-scoring face (ship)", test_color_agnostic_resolution_ship)
    run("Color-agnostic resolution for squad hit+crit", test_color_agnostic_resolution_squad)
    run("Color-agnostic resolution for crit (ship)", test_color_agnostic_resolution_crit_ship)
    run("Color-agnostic resolution for blank", test_color_agnostic_resolution_blank)
    run("Color-agnostic resolution for hit+hit", test_color_agnostic_resolution_hit_plus_hit)
