"""Property-based tests for defense in generate_report (Properties 11-12).

Feature: defense-effects, Properties 11-12: Defense pipeline integration in generate_report
**Validates: Requirements 7.2, 7.3, 14.4**

Uses Hypothesis to verify:
- Property 11: Post-defense statistics reflect modified damage values
- Property 12: Probability integrity after defense reroll and cancel
"""
import sys
sys.path.insert(0, '.')

from hypothesis import given, settings
from hypothesis import strategies as st

from drc_stat_engine.stats.report_engine import generate_report
from drc_stat_engine.stats.dice_models import DicePool, DefenseEffect

# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------
passed = 0
failed = 0
errors = []

# ---------------------------------------------------------------------------
# Property 11: Post-defense statistics reflect modified damage values
# Feature: defense-effects, Property 11: Post-defense statistics reflect modified damage values
# **Validates: Requirements 7.2, 7.3**
# Use generate_report with a small dice pool and a defense pipeline with
# reduce_damage or divide_damage. Verify that post-defense avg_damage is
# <= pre-defense avg_damage. Use hypothesis to generate random reduce
# amounts (1-5) and verify the relationship.
# ---------------------------------------------------------------------------
t11_pass = True
t11_error = None

try:
    @given(amount=st.integers(min_value=1, max_value=5))
    @settings(max_examples=100)
    def test_post_defense_avg_damage_reduced(amount):
        pool = DicePool(red=1, blue=1, black=0, type="ship")
        defense = [DefenseEffect(type="reduce_damage", amount=amount)]
        variants = generate_report(
            pool, [], ["max_damage"],
            backend="combinatorial",
            defense_pipeline=defense,
        )
        v = variants[0]
        assert "pre_defense" in v, "Missing pre_defense key in variant"
        assert "post_defense" in v, "Missing post_defense key in variant"
        pre_avg = v["pre_defense"]["avg_damage"]
        post_avg = v["post_defense"]["avg_damage"]
        assert post_avg <= pre_avg + 1e-9, (
            f"reduce_damage({amount}): post avg_damage ({post_avg:.6f}) > "
            f"pre avg_damage ({pre_avg:.6f})"
        )

    test_post_defense_avg_damage_reduced()
except Exception as e:
    t11_pass = False
    t11_error = str(e)

if t11_pass:
    print("PASS: Property 11a — reduce_damage: post-defense avg_damage <= pre-defense avg_damage")
    passed += 1
else:
    print(f"FAIL: Property 11a — {t11_error}")
    failed += 1
    errors.append(("Property 11a: reduce_damage avg_damage", t11_error))

# Property 11b: divide_damage also reduces avg_damage
t11b_pass = True
t11b_error = None

try:
    @settings(max_examples=100)
    @given(data=st.data())
    def test_post_defense_avg_damage_divided(data):
        pool = DicePool(red=1, blue=1, black=0, type="ship")
        defense = [DefenseEffect(type="divide_damage")]
        variants = generate_report(
            pool, [], ["max_damage"],
            backend="combinatorial",
            defense_pipeline=defense,
        )
        v = variants[0]
        assert "pre_defense" in v, "Missing pre_defense key in variant"
        assert "post_defense" in v, "Missing post_defense key in variant"
        pre_avg = v["pre_defense"]["avg_damage"]
        post_avg = v["post_defense"]["avg_damage"]
        assert post_avg <= pre_avg + 1e-9, (
            f"divide_damage: post avg_damage ({post_avg:.6f}) > "
            f"pre avg_damage ({pre_avg:.6f})"
        )

    test_post_defense_avg_damage_divided()
except Exception as e:
    t11b_pass = False
    t11b_error = str(e)

if t11b_pass:
    print("PASS: Property 11b — divide_damage: post-defense avg_damage <= pre-defense avg_damage")
    passed += 1
else:
    print(f"FAIL: Property 11b — {t11b_error}")
    failed += 1
    errors.append(("Property 11b: divide_damage avg_damage", t11b_error))

# ---------------------------------------------------------------------------
# Property 12: Probability integrity after defense reroll and cancel
# Feature: defense-effects, Property 12: Probability integrity after defense reroll and cancel
# **Validates: Requirements 14.4**
# Use generate_report with a small dice pool and defense_reroll or
# defense_cancel. Verify that the post-defense damage distribution
# probabilities sum to approximately 1.0. The damage distribution is
# returned as [(threshold, P(damage >= threshold))], so P(damage >= 0)
# should be ≈ 1.0.
# ---------------------------------------------------------------------------
t12_pass = True
t12_error = None

try:
    @given(mode=st.sampled_from(["safe", "gamble"]))
    @settings(max_examples=100)
    def test_probability_integrity_after_defense_reroll(mode):
        pool = DicePool(red=1, blue=1, black=0, type="ship")
        defense = [DefenseEffect(type="defense_reroll", count=1, mode=mode)]
        variants = generate_report(
            pool, [], ["max_damage"],
            backend="combinatorial",
            defense_pipeline=defense,
        )
        v = variants[0]
        # P(damage >= 0) should be ≈ 1.0
        damage_dist = v["post_defense"]["damage"]
        p_ge_0 = damage_dist[0][1]  # first entry is (0, P(damage >= 0))
        assert abs(p_ge_0 - 1.0) < 1e-9, (
            f"P(damage >= 0) = {p_ge_0}, expected ≈ 1.0"
        )

    test_probability_integrity_after_defense_reroll()
except Exception as e:
    t12_pass = False
    t12_error = str(e)

if t12_pass:
    print("PASS: Property 12a — defense_reroll: P(damage >= 0) ≈ 1.0")
    passed += 1
else:
    print(f"FAIL: Property 12a — {t12_error}")
    failed += 1
    errors.append(("Property 12a: defense_reroll probability integrity", t12_error))

# Property 12b: defense_cancel probability integrity
t12b_pass = True
t12b_error = None

try:
    @given(count=st.integers(min_value=1, max_value=2))
    @settings(max_examples=100)
    def test_probability_integrity_after_defense_cancel(count):
        pool = DicePool(red=1, blue=1, black=0, type="ship")
        defense = [DefenseEffect(type="defense_cancel", count=count)]
        variants = generate_report(
            pool, [], ["max_damage"],
            backend="combinatorial",
            defense_pipeline=defense,
        )
        v = variants[0]
        # P(damage >= 0) should be ≈ 1.0
        damage_dist = v["post_defense"]["damage"]
        p_ge_0 = damage_dist[0][1]  # first entry is (0, P(damage >= 0))
        assert abs(p_ge_0 - 1.0) < 1e-9, (
            f"P(damage >= 0) = {p_ge_0}, expected ≈ 1.0"
        )

    test_probability_integrity_after_defense_cancel()
except Exception as e:
    t12b_pass = False
    t12b_error = str(e)

if t12b_pass:
    print("PASS: Property 12b — defense_cancel: P(damage >= 0) ≈ 1.0")
    passed += 1
else:
    print(f"FAIL: Property 12b — {t12b_error}")
    failed += 1
    errors.append(("Property 12b: defense_cancel probability integrity", t12b_error))

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
