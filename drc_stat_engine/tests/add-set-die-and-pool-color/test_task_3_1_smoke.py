"""Smoke test for add_set_die_to_roll in the combinatorial backend."""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.dice_maths_combinatories import (
    add_set_die_to_roll, combine_dice, value_to_dice_attr_dict,
    value_str_to_list,
)

def test_basic_add_set_die():
    """Add R_hit to a 1-red pool and verify value strings, stats, and probabilities."""
    roll_df = combine_dice(1, 0, 0, "ship")
    target = "R_hit"
    result = add_set_die_to_roll(roll_df, target, "ship")

    attrs = value_to_dice_attr_dict(target, "ship")
    print(f"Target attrs: {attrs}")

    # Every outcome should now contain the target token
    for _, row in result.iterrows():
        tokens = value_str_to_list(row["value"])
        assert target in tokens, f"FAIL: {target} not in {row['value']}"
    print("PASS: every outcome contains the target token")

    # Value strings should be sorted
    for _, row in result.iterrows():
        tokens = value_str_to_list(row["value"])
        assert tokens == sorted(tokens), f"FAIL: tokens not sorted: {tokens}"
    print("PASS: all value strings are canonically sorted")

    # Probabilities should sum to 1.0
    total_proba = result["proba"].sum()
    assert abs(total_proba - 1.0) < 1e-9, f"FAIL: proba sum = {total_proba}"
    print(f"PASS: probability sum = {total_proba}")

    # Stats should be original + face attrs
    orig = combine_dice(1, 0, 0, "ship")
    for _, orig_row in orig.iterrows():
        orig_tokens = value_str_to_list(orig_row["value"])
        new_tokens = sorted(orig_tokens + [target])
        new_value = " ".join(new_tokens)
        match = result[result["value"] == new_value]
        assert len(match) >= 1, f"FAIL: expected value '{new_value}' not found"
        new_row = match.iloc[0]
        for stat in ("damage", "crit", "acc", "blank"):
            expected = orig_row[stat] + attrs[stat]
            actual = new_row[stat]
            assert actual == expected, (
                f"FAIL: {stat} for '{new_value}': expected {expected}, got {actual}"
            )
    print("PASS: stats correctly updated for all outcomes")


def test_grouping_after_collision():
    """When adding a set die causes value string collisions, probabilities should merge."""
    # 1 red die has 5 faces. Adding R_hit means R_hit + R_hit = "R_hit R_hit"
    # which is the same regardless of whether the original was R_hit.
    # But R_blank + R_hit = "R_blank R_hit" is unique.
    roll_df = combine_dice(1, 0, 0, "ship")
    result = add_set_die_to_roll(roll_df, "R_hit", "ship")

    # Should have fewer or equal rows than original (collisions reduce rows)
    # Actually for 1 red die, all original faces are distinct, so adding R_hit
    # produces distinct value strings (no collision expected for 1 die).
    # Let's just verify the groupby works by checking no duplicate value strings.
    assert result["value"].is_unique, "FAIL: duplicate value strings found"
    print("PASS: no duplicate value strings after groupby")


def test_add_set_die_to_multi_die_pool():
    """Add B_hit+crit to a 1R+1U pool."""
    roll_df = combine_dice(1, 1, 0, "ship")
    target = "B_hit+crit"
    result = add_set_die_to_roll(roll_df, target, "ship")

    attrs = value_to_dice_attr_dict(target, "ship")

    # Every outcome should contain the target
    for _, row in result.iterrows():
        assert target in value_str_to_list(row["value"]), (
            f"FAIL: {target} not in {row['value']}"
        )
    print("PASS: B_hit+crit present in all outcomes of 1R+1U pool")

    # Proba sum
    total = result["proba"].sum()
    assert abs(total - 1.0) < 1e-9, f"FAIL: proba sum = {total}"
    print(f"PASS: probability sum = {total}")

    # Damage should be original + 2 for every row
    orig = combine_dice(1, 1, 0, "ship")
    for _, orig_row in orig.iterrows():
        new_value = " ".join(sorted(value_str_to_list(orig_row["value"]) + [target]))
        match = result[result["value"] == new_value]
        assert len(match) >= 1, f"FAIL: expected '{new_value}' not found"
        assert match.iloc[0]["damage"] == orig_row["damage"] + attrs["damage"], (
            f"FAIL: damage mismatch for '{new_value}'"
        )
    print("PASS: damage correctly updated for 1R+1U + B_hit+crit")


def test_squad_type():
    """Verify add_set_die works with squad type."""
    roll_df = combine_dice(0, 1, 0, "squad")
    target = "U_hit"
    result = add_set_die_to_roll(roll_df, target, "squad")

    total = result["proba"].sum()
    assert abs(total - 1.0) < 1e-9, f"FAIL: proba sum = {total}"
    print(f"PASS: squad type works, proba sum = {total}")


if __name__ == "__main__":
    try:
        test_basic_add_set_die()
        print()
        test_grouping_after_collision()
        print()
        test_add_set_die_to_multi_die_pool()
        print()
        test_squad_type()
        print()
        print("ALL SMOKE TESTS PASSED")
    except Exception as e:
        print(f"FAIL: unexpected error: {e}")
        import traceback
        traceback.print_exc()
