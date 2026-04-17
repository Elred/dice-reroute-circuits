"""Property-based tests for applicable_results filtering (Property 3).

Feature: defense-effects, Property 3: Applicable_results filtering preserves priority ordering
**Validates: Requirements 2.3, 3.2, 13.5**

For each defense priority list (safe reroll, gamble reroll, defense_cancel),
generate random subsets of faces as applicable_results, build a DefenseEffect with those
applicable_results, run build_defense_pipeline, and verify the resolved priority_list is
exactly the subsequence of the original priority list containing only faces in
applicable_results, preserving order.
"""
import sys
sys.path.insert(0, '.')

from hypothesis import given, settings
from hypothesis import strategies as st

from drc_stat_engine.stats.dice_models import DefenseEffect
from drc_stat_engine.stats.strategies import DEFENSE_PRIORITY_LISTS, build_defense_pipeline

# ---------------------------------------------------------------------------
# Reference priority lists
# ---------------------------------------------------------------------------

SAFE_REROLL_PRIORITY = ["R_hit+hit", "B_hit+crit", "U_crit", "U_hit"]
COULD_BE_BLANK_PRIORITY = ["R_hit+hit", "B_hit+crit", "R_crit", "R_hit", "U_crit", "U_hit", "B_hit"]
DEFENSE_CANCEL_PRIORITY = ["B_hit+crit", "R_hit+hit", "U_crit", "R_crit", "R_hit", "U_hit", "B_hit"]

# ---------------------------------------------------------------------------
# Strategies: generate random subsets of each priority list
# ---------------------------------------------------------------------------

safe_subsets = st.lists(
    st.sampled_from(SAFE_REROLL_PRIORITY),
    min_size=0,
    max_size=len(SAFE_REROLL_PRIORITY),
    unique=True,
)

gamble_subsets = st.lists(
    st.sampled_from(COULD_BE_BLANK_PRIORITY),
    min_size=0,
    max_size=len(COULD_BE_BLANK_PRIORITY),
    unique=True,
)

cancel_subsets = st.lists(
    st.sampled_from(DEFENSE_CANCEL_PRIORITY),
    min_size=0,
    max_size=len(DEFENSE_CANCEL_PRIORITY),
    unique=True,
)

# ---------------------------------------------------------------------------
# Helper: compute expected subsequence
# ---------------------------------------------------------------------------

def expected_subsequence(full_priority, applicable_results):
    """Return the subsequence of full_priority containing only faces in applicable_results."""
    allowed = set(applicable_results)
    return [face for face in full_priority if face in allowed]

# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------
passed = 0
failed = 0
errors = []

# ---------------------------------------------------------------------------
# Test 1: defense_reroll safe — applicable_results filtering preserves order
# ---------------------------------------------------------------------------
t1_pass = True
t1_error = None

try:
    @given(subset=safe_subsets)
    @settings(max_examples=100)
    def test_safe_reroll_filtering(subset):
        effect = DefenseEffect(
            type="defense_reroll",
            count=1,
            mode="safe",
            applicable_results=subset,
        )
        result = build_defense_pipeline([effect])
        resolved = result[0].priority_list

        if subset:
            expected = expected_subsequence(SAFE_REROLL_PRIORITY, subset)
        else:
            # Empty applicable_results means no filter — full priority list
            expected = list(SAFE_REROLL_PRIORITY)

        assert resolved == expected, (
            f"safe reroll: applicable_results={subset}, "
            f"expected={expected}, got={resolved}"
        )

    test_safe_reroll_filtering()
except Exception as e:
    t1_pass = False
    t1_error = str(e)

if t1_pass:
    print("PASS: defense_reroll safe — applicable_results filtering preserves priority order")
    passed += 1
else:
    print(f"FAIL: defense_reroll safe — {t1_error}")
    failed += 1
    errors.append(("defense_reroll safe filtering", t1_error))

# ---------------------------------------------------------------------------
# Test 2: defense_reroll gamble — applicable_results filtering preserves order
# ---------------------------------------------------------------------------
t2_pass = True
t2_error = None

try:
    @given(subset=gamble_subsets)
    @settings(max_examples=100)
    def test_gamble_reroll_filtering(subset):
        effect = DefenseEffect(
            type="defense_reroll",
            count=1,
            mode="gamble",
            applicable_results=subset,
        )
        result = build_defense_pipeline([effect])
        resolved = result[0].priority_list

        if subset:
            expected = expected_subsequence(COULD_BE_BLANK_PRIORITY, subset)
        else:
            expected = list(COULD_BE_BLANK_PRIORITY)

        assert resolved == expected, (
            f"gamble reroll: applicable_results={subset}, "
            f"expected={expected}, got={resolved}"
        )

    test_gamble_reroll_filtering()
except Exception as e:
    t2_pass = False
    t2_error = str(e)

if t2_pass:
    print("PASS: defense_reroll gamble — applicable_results filtering preserves priority order")
    passed += 1
else:
    print(f"FAIL: defense_reroll gamble — {t2_error}")
    failed += 1
    errors.append(("defense_reroll gamble filtering", t2_error))

# ---------------------------------------------------------------------------
# Test 3: defense_cancel — applicable_results filtering preserves order
# ---------------------------------------------------------------------------
t3_pass = True
t3_error = None

try:
    @given(subset=cancel_subsets)
    @settings(max_examples=100)
    def test_cancel_filtering(subset):
        effect = DefenseEffect(
            type="defense_cancel",
            count=1,
            applicable_results=subset,
        )
        result = build_defense_pipeline([effect])
        resolved = result[0].priority_list

        if subset:
            expected = expected_subsequence(DEFENSE_CANCEL_PRIORITY, subset)
        else:
            expected = list(DEFENSE_CANCEL_PRIORITY)

        assert resolved == expected, (
            f"defense_cancel: applicable_results={subset}, "
            f"expected={expected}, got={resolved}"
        )

    test_cancel_filtering()
except Exception as e:
    t3_pass = False
    t3_error = str(e)

if t3_pass:
    print("PASS: defense_cancel — applicable_results filtering preserves priority order")
    passed += 1
else:
    print(f"FAIL: defense_cancel — {t3_error}")
    failed += 1
    errors.append(("defense_cancel filtering", t3_error))

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
