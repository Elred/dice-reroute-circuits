"""Property-based tests for DefenseEffect validation (Property 1).

Feature: defense-effects, Property 1: Defense effect validation accepts valid effects and rejects invalid ones
**Validates: Requirements 1.1, 1.2, 1.4, 1.5, 1.6, 9.1, 9.2, 9.3, 9.4, 9.5**

Uses Hypothesis to generate valid and invalid DefenseEffect instances and verify
that validate_defense_pipeline accepts valid effects and raises ValueError for invalid ones.
"""
import sys
sys.path.insert(0, '.')

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from drc_stat_engine.stats.dice_models import (
    DefenseEffect,
    validate_defense_pipeline,
    VALID_DEFENSE_EFFECT_TYPES,
)

# ---------------------------------------------------------------------------
# Strategies / Generators
# ---------------------------------------------------------------------------

valid_modes = st.sampled_from(["safe", "could_be_blank"])
positive_ints = st.integers(min_value=1, max_value=100)

# Valid defense_reroll: mode in {"safe", "could_be_blank"}, count > 0
valid_defense_reroll = st.builds(
    DefenseEffect,
    type=st.just("defense_reroll"),
    count=positive_ints,
    mode=valid_modes,
)

# Valid defense_cancel: count > 0
valid_defense_cancel = st.builds(
    DefenseEffect,
    type=st.just("defense_cancel"),
    count=positive_ints,
)

# Valid reduce_damage: amount > 0
valid_reduce_damage = st.builds(
    DefenseEffect,
    type=st.just("reduce_damage"),
    amount=positive_ints,
)

# Valid divide_damage: no special fields needed
valid_divide_damage = st.builds(
    DefenseEffect,
    type=st.just("divide_damage"),
)

# Combined valid effect strategy
valid_defense_effect = st.one_of(
    valid_defense_reroll,
    valid_defense_cancel,
    valid_reduce_damage,
    valid_divide_damage,
)

# Invalid: unknown type
invalid_type_strings = st.text(min_size=1, max_size=30).filter(
    lambda s: s not in VALID_DEFENSE_EFFECT_TYPES
)

# Invalid modes for defense_reroll (not "safe" or "could_be_blank")
invalid_modes = st.one_of(
    st.text(min_size=1, max_size=20).filter(lambda s: s not in ("safe", "could_be_blank")),
)

# Non-positive integers for count/amount
non_positive_ints = st.integers(min_value=-100, max_value=0)

# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------
passed = 0
failed = 0
errors = []

# ---------------------------------------------------------------------------
# Test 1: Valid defense_reroll with mode "safe" or "could_be_blank" and count > 0
# ---------------------------------------------------------------------------
t1_pass = True
t1_error = None

try:
    @given(effect=valid_defense_reroll)
    @settings(max_examples=100)
    def test_valid_defense_reroll(effect):
        """Valid defense_reroll effects should pass validation."""
        validate_defense_pipeline([effect])

    test_valid_defense_reroll()
except Exception as e:
    t1_pass = False
    t1_error = str(e)

if t1_pass:
    print("PASS: Valid defense_reroll accepted (mode safe/could_be_blank, count > 0)")
    passed += 1
else:
    print(f"FAIL: Valid defense_reroll — {t1_error}")
    failed += 1
    errors.append(("Valid defense_reroll", t1_error))

# ---------------------------------------------------------------------------
# Test 2: Valid defense_cancel with count > 0
# ---------------------------------------------------------------------------
t2_pass = True
t2_error = None

try:
    @given(effect=valid_defense_cancel)
    @settings(max_examples=100)
    def test_valid_defense_cancel(effect):
        """Valid defense_cancel effects should pass validation."""
        validate_defense_pipeline([effect])

    test_valid_defense_cancel()
except Exception as e:
    t2_pass = False
    t2_error = str(e)

if t2_pass:
    print("PASS: Valid defense_cancel accepted (count > 0)")
    passed += 1
else:
    print(f"FAIL: Valid defense_cancel — {t2_error}")
    failed += 1
    errors.append(("Valid defense_cancel", t2_error))

# ---------------------------------------------------------------------------
# Test 3: Valid reduce_damage with amount > 0
# ---------------------------------------------------------------------------
t3_pass = True
t3_error = None

try:
    @given(effect=valid_reduce_damage)
    @settings(max_examples=100)
    def test_valid_reduce_damage(effect):
        """Valid reduce_damage effects should pass validation."""
        validate_defense_pipeline([effect])

    test_valid_reduce_damage()
except Exception as e:
    t3_pass = False
    t3_error = str(e)

if t3_pass:
    print("PASS: Valid reduce_damage accepted (amount > 0)")
    passed += 1
else:
    print(f"FAIL: Valid reduce_damage — {t3_error}")
    failed += 1
    errors.append(("Valid reduce_damage", t3_error))

# ---------------------------------------------------------------------------
# Test 4: Valid divide_damage (no special fields)
# ---------------------------------------------------------------------------
t4_pass = True
t4_error = None

try:
    @given(effect=valid_divide_damage)
    @settings(max_examples=100)
    def test_valid_divide_damage(effect):
        """Valid divide_damage effects should pass validation."""
        validate_defense_pipeline([effect])

    test_valid_divide_damage()
except Exception as e:
    t4_pass = False
    t4_error = str(e)

if t4_pass:
    print("PASS: Valid divide_damage accepted")
    passed += 1
else:
    print(f"FAIL: Valid divide_damage — {t4_error}")
    failed += 1
    errors.append(("Valid divide_damage", t4_error))

# ---------------------------------------------------------------------------
# Test 5: Invalid — unknown type raises ValueError
# ---------------------------------------------------------------------------
t5_pass = True
t5_error = None

try:
    @given(bad_type=invalid_type_strings)
    @settings(max_examples=100)
    def test_invalid_unknown_type(bad_type):
        """Unknown defense effect types should raise ValueError."""
        effect = DefenseEffect(type=bad_type)
        try:
            validate_defense_pipeline([effect])
            raise AssertionError(f"Expected ValueError for unknown type '{bad_type}'")
        except ValueError:
            pass  # Expected

    test_invalid_unknown_type()
except Exception as e:
    t5_pass = False
    t5_error = str(e)

if t5_pass:
    print("PASS: Unknown type rejected with ValueError")
    passed += 1
else:
    print(f"FAIL: Unknown type — {t5_error}")
    failed += 1
    errors.append(("Unknown type", t5_error))

# ---------------------------------------------------------------------------
# Test 6: Invalid — defense_reroll with missing mode (None) raises ValueError
# ---------------------------------------------------------------------------
t6_pass = True
t6_error = None

try:
    @given(count=positive_ints)
    @settings(max_examples=100)
    def test_invalid_reroll_missing_mode(count):
        """defense_reroll with mode=None should raise ValueError."""
        effect = DefenseEffect(type="defense_reroll", count=count, mode=None)
        try:
            validate_defense_pipeline([effect])
            raise AssertionError("Expected ValueError for defense_reroll with mode=None")
        except ValueError:
            pass  # Expected

    test_invalid_reroll_missing_mode()
except Exception as e:
    t6_pass = False
    t6_error = str(e)

if t6_pass:
    print("PASS: defense_reroll with missing mode rejected")
    passed += 1
else:
    print(f"FAIL: defense_reroll missing mode — {t6_error}")
    failed += 1
    errors.append(("defense_reroll missing mode", t6_error))

# ---------------------------------------------------------------------------
# Test 7: Invalid — defense_reroll with bad mode string raises ValueError
# ---------------------------------------------------------------------------
t7_pass = True
t7_error = None

try:
    @given(bad_mode=invalid_modes, count=positive_ints)
    @settings(max_examples=100)
    def test_invalid_reroll_bad_mode(bad_mode, count):
        """defense_reroll with invalid mode string should raise ValueError."""
        effect = DefenseEffect(type="defense_reroll", count=count, mode=bad_mode)
        try:
            validate_defense_pipeline([effect])
            raise AssertionError(f"Expected ValueError for mode '{bad_mode}'")
        except ValueError:
            pass  # Expected

    test_invalid_reroll_bad_mode()
except Exception as e:
    t7_pass = False
    t7_error = str(e)

if t7_pass:
    print("PASS: defense_reroll with bad mode rejected")
    passed += 1
else:
    print(f"FAIL: defense_reroll bad mode — {t7_error}")
    failed += 1
    errors.append(("defense_reroll bad mode", t7_error))

# ---------------------------------------------------------------------------
# Test 8: Invalid — defense_reroll/cancel with count <= 0 raises ValueError
# ---------------------------------------------------------------------------
t8_pass = True
t8_error = None

try:
    @given(
        bad_count=non_positive_ints,
        mode=valid_modes,
    )
    @settings(max_examples=100)
    def test_invalid_reroll_bad_count(bad_count, mode):
        """defense_reroll with count <= 0 should raise ValueError."""
        effect = DefenseEffect(type="defense_reroll", count=bad_count, mode=mode)
        try:
            validate_defense_pipeline([effect])
            raise AssertionError(f"Expected ValueError for reroll count={bad_count}")
        except ValueError:
            pass  # Expected

    test_invalid_reroll_bad_count()
except Exception as e:
    t8_pass = False
    t8_error = str(e)

try:
    @given(bad_count=non_positive_ints)
    @settings(max_examples=100)
    def test_invalid_cancel_bad_count(bad_count):
        """defense_cancel with count <= 0 should raise ValueError."""
        effect = DefenseEffect(type="defense_cancel", count=bad_count)
        try:
            validate_defense_pipeline([effect])
            raise AssertionError(f"Expected ValueError for cancel count={bad_count}")
        except ValueError:
            pass  # Expected

    test_invalid_cancel_bad_count()
except Exception as e:
    t8_pass = False
    t8_error = str(e)

if t8_pass:
    print("PASS: defense_reroll/cancel with count <= 0 rejected")
    passed += 1
else:
    print(f"FAIL: defense_reroll/cancel bad count — {t8_error}")
    failed += 1
    errors.append(("defense_reroll/cancel bad count", t8_error))

# ---------------------------------------------------------------------------
# Test 9: Invalid — reduce_damage with amount <= 0 raises ValueError
# ---------------------------------------------------------------------------
t9_pass = True
t9_error = None

try:
    @given(bad_amount=non_positive_ints)
    @settings(max_examples=100)
    def test_invalid_reduce_bad_amount(bad_amount):
        """reduce_damage with amount <= 0 should raise ValueError."""
        effect = DefenseEffect(type="reduce_damage", amount=bad_amount)
        try:
            validate_defense_pipeline([effect])
            raise AssertionError(f"Expected ValueError for reduce_damage amount={bad_amount}")
        except ValueError:
            pass  # Expected

    test_invalid_reduce_bad_amount()
except Exception as e:
    t9_pass = False
    t9_error = str(e)

if t9_pass:
    print("PASS: reduce_damage with amount <= 0 rejected")
    passed += 1
else:
    print(f"FAIL: reduce_damage bad amount — {t9_error}")
    failed += 1
    errors.append(("reduce_damage bad amount", t9_error))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
if failed == 0:
    print("ALL PROPERTY TESTS PASSED")
else:
    print("SOME PROPERTY TESTS FAILED")
    for name, err in errors:
        print(f"  {name}: {err}")
