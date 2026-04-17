"""
Task 9.2 — Verify /meta endpoint includes add_set_die in attack_effect_types.

Since attack_effect_types is derived from VALID_ATTACK_EFFECT_TYPES,
adding add_set_die to the set in task 1.1 should automatically expose it.

Validates: Requirement 16.4
"""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.dice_models import VALID_ATTACK_EFFECT_TYPES

# --- Test 1: add_set_die is in VALID_ATTACK_EFFECT_TYPES ---
try:
    assert "add_set_die" in VALID_ATTACK_EFFECT_TYPES, (
        f"'add_set_die' not found in VALID_ATTACK_EFFECT_TYPES: {VALID_ATTACK_EFFECT_TYPES}"
    )
    print("PASS: 'add_set_die' is in VALID_ATTACK_EFFECT_TYPES")
except AssertionError as e:
    print(f"FAIL: {e}")
except Exception as e:
    print(f"ERROR: {e}")

# --- Test 2: sorted list (as returned by /meta) includes add_set_die ---
try:
    sorted_types = sorted(VALID_ATTACK_EFFECT_TYPES)
    assert "add_set_die" in sorted_types, (
        f"'add_set_die' not in sorted list: {sorted_types}"
    )
    print(f"PASS: sorted attack_effect_types includes 'add_set_die': {sorted_types}")
except AssertionError as e:
    print(f"FAIL: {e}")
except Exception as e:
    print(f"ERROR: {e}")

# --- Test 3: all expected types present ---
try:
    expected = {"reroll", "cancel", "add_dice", "change_die", "reroll_all", "add_set_die"}
    assert VALID_ATTACK_EFFECT_TYPES == expected, (
        f"Mismatch: got {VALID_ATTACK_EFFECT_TYPES}, expected {expected}"
    )
    print(f"PASS: VALID_ATTACK_EFFECT_TYPES matches expected set")
except AssertionError as e:
    print(f"FAIL: {e}")
except Exception as e:
    print(f"ERROR: {e}")

print("\nAll task 9.2 verification checks complete.")
