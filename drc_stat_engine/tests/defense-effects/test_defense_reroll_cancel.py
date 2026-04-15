"""Integration tests for defense reroll and cancel (Properties 2, 4, 5).

Feature: defense-effects, Properties 2, 4, 5: Defense reroll priority, cancel priority,
and accuracy/blank immunity.

Uses generate_report with real dice pools and defense pipelines to verify:
- Property 2: Defense reroll uses correct mode-specific priority ordering
- Property 5: Defense cancel uses correct priority ordering
- Property 4: Defense reroll and cancel ignore accuracy and blank faces

**Validates: Requirements 2.1, 2.2, 2.4, 3.1, 3.3**
"""
import sys
sys.path.insert(0, '.')

from drc_stat_engine.stats.report_engine import generate_report
from drc_stat_engine.stats.dice_models import DicePool, DefenseEffect

# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------
passed = 0
failed = 0
errors = []

# ===========================================================================
# Property 2: Defense reroll uses correct mode-specific priority ordering
# Feature: defense-effects, Property 2: Defense reroll uses correct mode-specific priority ordering
# **Validates: Requirements 2.1, 2.2**
#
# Approach: Use generate_report with a known pool and defense_reroll.
# After a defense reroll, the defender is rerolling the attacker's
# highest-damage faces, so post-defense avg_damage should be strictly
# less than pre-defense avg_damage (for pools that produce damage faces).
#
# We test both "safe" and "gamble" modes with multiple pool configs.
# ===========================================================================

# --- Property 2a: Safe reroll reduces avg_damage (1R 1U pool) ---
t2a_pass = True
t2a_error = None

try:
    pool = DicePool(red=1, blue=1, black=0, type="ship")
    defense = [DefenseEffect(type="defense_reroll", count=1, mode="safe")]
    variants = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense,
    )
    v = variants[0]
    assert "pre_defense" in v, "Missing pre_defense key"
    assert "post_defense" in v, "Missing post_defense key"
    pre_avg = v["pre_defense"]["avg_damage"]
    post_avg = v["post_defense"]["avg_damage"]
    # Safe reroll targets: R_hit+hit, B_hit+crit, U_crit, U_hit
    # With 1R+1U, there are damage faces to reroll, so avg should decrease
    assert post_avg < pre_avg - 1e-9, (
        f"safe reroll (1R1U): post avg_damage ({post_avg:.6f}) should be "
        f"strictly less than pre avg_damage ({pre_avg:.6f})"
    )
except Exception as e:
    t2a_pass = False
    t2a_error = str(e)

if t2a_pass:
    print("PASS: Property 2a — safe reroll reduces avg_damage (1R 1U pool)")
    passed += 1
else:
    print(f"FAIL: Property 2a — {t2a_error}")
    failed += 1
    errors.append(("Property 2a", t2a_error))

# --- Property 2b: Could-be-blank reroll reduces avg_damage (1R 1U pool) ---
t2b_pass = True
t2b_error = None

try:
    pool = DicePool(red=1, blue=1, black=0, type="ship")
    defense = [DefenseEffect(type="defense_reroll", count=1, mode="gamble")]
    variants = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense,
    )
    v = variants[0]
    pre_avg = v["pre_defense"]["avg_damage"]
    post_avg = v["post_defense"]["avg_damage"]
    # gamble targets more faces: R_hit+hit, B_hit+crit, R_crit, R_hit, U_crit, U_hit, B_hit
    assert post_avg < pre_avg - 1e-9, (
        f"gamble reroll (1R1U): post avg_damage ({post_avg:.6f}) should be "
        f"strictly less than pre avg_damage ({pre_avg:.6f})"
    )
except Exception as e:
    t2b_pass = False
    t2b_error = str(e)

if t2b_pass:
    print("PASS: Property 2b — gamble reroll reduces avg_damage (1R 1U pool)")
    passed += 1
else:
    print(f"FAIL: Property 2b — {t2b_error}")
    failed += 1
    errors.append(("Property 2b", t2b_error))

# --- Property 2c: gamble reroll reduces MORE than safe reroll ---
# gamble targets more faces (including R_crit, R_hit, B_hit),
# so it should reduce avg_damage more aggressively than safe mode.
t2c_pass = True
t2c_error = None

try:
    pool = DicePool(red=1, blue=1, black=0, type="ship")
    defense_safe = [DefenseEffect(type="defense_reroll", count=1, mode="safe")]
    defense_cbb = [DefenseEffect(type="defense_reroll", count=1, mode="gamble")]

    v_safe = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense_safe,
    )[0]
    v_cbb = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense_cbb,
    )[0]

    safe_post = v_safe["post_defense"]["avg_damage"]
    cbb_post = v_cbb["post_defense"]["avg_damage"]
    # gamble targets strictly more faces, so it should reduce damage
    # at least as much (and typically more) than safe mode
    assert cbb_post <= safe_post + 1e-9, (
        f"gamble post avg ({cbb_post:.6f}) should be <= "
        f"safe post avg ({safe_post:.6f})"
    )
except Exception as e:
    t2c_pass = False
    t2c_error = str(e)

if t2c_pass:
    print("PASS: Property 2c — gamble reroll reduces at least as much as safe reroll")
    passed += 1
else:
    print(f"FAIL: Property 2c — {t2c_error}")
    failed += 1
    errors.append(("Property 2c", t2c_error))

# --- Property 2d: Safe reroll with 2R pool (more reroll targets) ---
t2d_pass = True
t2d_error = None

try:
    pool = DicePool(red=2, blue=0, black=0, type="ship")
    defense = [DefenseEffect(type="defense_reroll", count=1, mode="safe")]
    variants = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense,
    )
    v = variants[0]
    pre_avg = v["pre_defense"]["avg_damage"]
    post_avg = v["post_defense"]["avg_damage"]
    # Red die has R_hit+hit in safe priority — rerolling it should reduce damage
    assert post_avg < pre_avg - 1e-9, (
        f"safe reroll (2R): post avg_damage ({post_avg:.6f}) should be "
        f"strictly less than pre avg_damage ({pre_avg:.6f})"
    )
except Exception as e:
    t2d_pass = False
    t2d_error = str(e)

if t2d_pass:
    print("PASS: Property 2d — safe reroll reduces avg_damage (2R pool)")
    passed += 1
else:
    print(f"FAIL: Property 2d — {t2d_error}")
    failed += 1
    errors.append(("Property 2d", t2d_error))

# --- Property 2e: Rerolling more dice reduces damage more ---
t2e_pass = True
t2e_error = None

try:
    pool = DicePool(red=1, blue=1, black=1, type="ship")
    defense_1 = [DefenseEffect(type="defense_reroll", count=1, mode="gamble")]
    defense_2 = [DefenseEffect(type="defense_reroll", count=2, mode="gamble")]

    v1 = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense_1,
    )[0]
    v2 = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense_2,
    )[0]

    post_1 = v1["post_defense"]["avg_damage"]
    post_2 = v2["post_defense"]["avg_damage"]
    # Rerolling 2 dice should reduce damage at least as much as rerolling 1
    assert post_2 <= post_1 + 1e-9, (
        f"reroll count=2 post avg ({post_2:.6f}) should be <= "
        f"reroll count=1 post avg ({post_1:.6f})"
    )
except Exception as e:
    t2e_pass = False
    t2e_error = str(e)

if t2e_pass:
    print("PASS: Property 2e — rerolling 2 dice reduces damage at least as much as rerolling 1")
    passed += 1
else:
    print(f"FAIL: Property 2e — {t2e_error}")
    failed += 1
    errors.append(("Property 2e", t2e_error))


# ===========================================================================
# Property 5: Defense cancel uses correct priority ordering
# Feature: defense-effects, Property 5: Defense cancel uses correct priority ordering
# **Validates: Requirements 3.1**
#
# Approach: Use generate_report with a known pool and defense_cancel.
# After cancelling dice, the highest-priority damage faces are removed,
# so post-defense avg_damage should be strictly less than pre-defense.
# Cancel priority: B_hit+crit, R_hit+hit, U_crit, R_crit, R_hit, U_hit, B_hit
# ===========================================================================

# --- Property 5a: Cancel 1 die reduces avg_damage (1R 1U pool) ---
t5a_pass = True
t5a_error = None

try:
    pool = DicePool(red=1, blue=1, black=0, type="ship")
    defense = [DefenseEffect(type="defense_cancel", count=1)]
    variants = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense,
    )
    v = variants[0]
    assert "pre_defense" in v, "Missing pre_defense key"
    assert "post_defense" in v, "Missing post_defense key"
    pre_avg = v["pre_defense"]["avg_damage"]
    post_avg = v["post_defense"]["avg_damage"]
    # Cancelling a damage die should reduce avg_damage
    assert post_avg < pre_avg - 1e-9, (
        f"cancel 1 (1R1U): post avg_damage ({post_avg:.6f}) should be "
        f"strictly less than pre avg_damage ({pre_avg:.6f})"
    )
except Exception as e:
    t5a_pass = False
    t5a_error = str(e)

if t5a_pass:
    print("PASS: Property 5a — cancel 1 die reduces avg_damage (1R 1U pool)")
    passed += 1
else:
    print(f"FAIL: Property 5a — {t5a_error}")
    failed += 1
    errors.append(("Property 5a", t5a_error))

# --- Property 5b: Cancel 1 die with black die pool (B_hit+crit is top priority) ---
t5b_pass = True
t5b_error = None

try:
    pool = DicePool(red=0, blue=1, black=1, type="ship")
    defense = [DefenseEffect(type="defense_cancel", count=1)]
    variants = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense,
    )
    v = variants[0]
    pre_avg = v["pre_defense"]["avg_damage"]
    post_avg = v["post_defense"]["avg_damage"]
    # B_hit+crit is top cancel priority — should reduce damage
    assert post_avg < pre_avg - 1e-9, (
        f"cancel 1 (1U1B): post avg_damage ({post_avg:.6f}) should be "
        f"strictly less than pre avg_damage ({pre_avg:.6f})"
    )
except Exception as e:
    t5b_pass = False
    t5b_error = str(e)

if t5b_pass:
    print("PASS: Property 5b — cancel 1 die reduces avg_damage (1U 1B pool)")
    passed += 1
else:
    print(f"FAIL: Property 5b — {t5b_error}")
    failed += 1
    errors.append(("Property 5b", t5b_error))

# --- Property 5c: Cancelling more dice reduces damage more ---
t5c_pass = True
t5c_error = None

try:
    pool = DicePool(red=1, blue=1, black=1, type="ship")
    defense_1 = [DefenseEffect(type="defense_cancel", count=1)]
    defense_2 = [DefenseEffect(type="defense_cancel", count=2)]

    v1 = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense_1,
    )[0]
    v2 = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense_2,
    )[0]

    post_1 = v1["post_defense"]["avg_damage"]
    post_2 = v2["post_defense"]["avg_damage"]
    # Cancelling 2 dice should reduce damage at least as much as cancelling 1
    assert post_2 <= post_1 + 1e-9, (
        f"cancel count=2 post avg ({post_2:.6f}) should be <= "
        f"cancel count=1 post avg ({post_1:.6f})"
    )
except Exception as e:
    t5c_pass = False
    t5c_error = str(e)

if t5c_pass:
    print("PASS: Property 5c — cancelling 2 dice reduces damage at least as much as cancelling 1")
    passed += 1
else:
    print(f"FAIL: Property 5c — {t5c_error}")
    failed += 1
    errors.append(("Property 5c", t5c_error))

# --- Property 5d: Cancel reduces damage more than reroll (cancel removes, reroll re-randomizes) ---
t5d_pass = True
t5d_error = None

try:
    pool = DicePool(red=1, blue=1, black=0, type="ship")
    defense_cancel = [DefenseEffect(type="defense_cancel", count=1)]
    defense_reroll = [DefenseEffect(type="defense_reroll", count=1, mode="gamble")]

    v_cancel = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense_cancel,
    )[0]
    v_reroll = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense_reroll,
    )[0]

    cancel_post = v_cancel["post_defense"]["avg_damage"]
    reroll_post = v_reroll["post_defense"]["avg_damage"]
    # Cancel removes a die entirely; reroll just re-randomizes it.
    # Cancel should reduce damage at least as much as reroll.
    assert cancel_post <= reroll_post + 1e-9, (
        f"cancel post avg ({cancel_post:.6f}) should be <= "
        f"reroll post avg ({reroll_post:.6f})"
    )
except Exception as e:
    t5d_pass = False
    t5d_error = str(e)

if t5d_pass:
    print("PASS: Property 5d — cancel reduces damage at least as much as reroll")
    passed += 1
else:
    print(f"FAIL: Property 5d — {t5d_error}")
    failed += 1
    errors.append(("Property 5d", t5d_error))


# ===========================================================================
# Property 4: Defense reroll and cancel ignore accuracy and blank faces
# Feature: defense-effects, Property 4: Defense reroll and cancel ignore accuracy and blank faces
# **Validates: Requirements 2.4, 3.3**
#
# Approach: Use generate_report with a pool that produces accuracy faces
# (blue dice have U_acc). After defense_reroll or defense_cancel, the
# accuracy distribution should be unchanged between pre_defense and
# post_defense — defense effects never touch accuracy or blank faces.
#
# Similarly, blank faces should not be affected. We verify by checking
# that the accuracy cumulative distribution is identical pre and post defense.
# ===========================================================================

# --- Property 4a: Defense reroll (safe) never targets accuracy faces ---
# Accuracy faces are never in the defense reroll priority list, so they
# are never selected for reroll. When damage faces are rerolled, some may
# land on accuracy faces, so P(acc >= 1) can only increase or stay the same.
# If accuracy faces WERE being rerolled, P(acc >= 1) would decrease.
t4a_pass = True
t4a_error = None

try:
    # Use 2 blue dice — U_acc (25% each). Safe reroll targets [U_crit, U_hit].
    pool = DicePool(red=0, blue=2, black=0, type="ship")
    defense = [DefenseEffect(type="defense_reroll", count=2, mode="safe")]
    variants = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense,
    )
    v = variants[0]
    pre_acc_zero = v["pre_defense"]["acc_zero"]
    post_acc_zero = v["post_defense"]["acc_zero"]
    # Rerolling damage faces can produce accuracy faces, so P(acc=0) should
    # decrease or stay the same (more accuracy after reroll, not less).
    # If accuracy faces were targeted, P(acc=0) would increase.
    assert post_acc_zero <= pre_acc_zero + 1e-9, (
        f"safe reroll: P(acc=0) increased from {pre_acc_zero:.9f} to "
        f"{post_acc_zero:.9f} — accuracy faces may have been targeted"
    )
except Exception as e:
    t4a_pass = False
    t4a_error = str(e)

if t4a_pass:
    print("PASS: Property 4a — safe reroll does not target accuracy faces (2U pool)")
    passed += 1
else:
    print(f"FAIL: Property 4a — {t4a_error}")
    failed += 1
    errors.append(("Property 4a", t4a_error))

# --- Property 4b: Defense reroll (gamble) never targets accuracy faces ---
t4b_pass = True
t4b_error = None

try:
    pool = DicePool(red=0, blue=2, black=0, type="ship")
    defense = [DefenseEffect(type="defense_reroll", count=2, mode="gamble")]
    variants = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense,
    )
    v = variants[0]
    pre_acc_zero = v["pre_defense"]["acc_zero"]
    post_acc_zero = v["post_defense"]["acc_zero"]
    # Same logic: rerolling damage faces can produce accuracy, so P(acc=0)
    # should decrease or stay the same.
    assert post_acc_zero <= pre_acc_zero + 1e-9, (
        f"gamble reroll: P(acc=0) increased from {pre_acc_zero:.9f} to "
        f"{post_acc_zero:.9f} — accuracy faces may have been targeted"
    )
except Exception as e:
    t4b_pass = False
    t4b_error = str(e)

if t4b_pass:
    print("PASS: Property 4b — gamble reroll does not target accuracy faces (2U pool)")
    passed += 1
else:
    print(f"FAIL: Property 4b — {t4b_error}")
    failed += 1
    errors.append(("Property 4b", t4b_error))

# --- Property 4c: Defense cancel does not affect accuracy distribution ---
t4c_pass = True
t4c_error = None

try:
    pool = DicePool(red=0, blue=2, black=0, type="ship")
    defense = [DefenseEffect(type="defense_cancel", count=2)]
    variants = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense,
    )
    v = variants[0]
    pre_acc = v["pre_defense"]["accuracy"]
    post_acc = v["post_defense"]["accuracy"]
    assert len(pre_acc) == len(post_acc), (
        f"Accuracy distribution length mismatch: pre={len(pre_acc)}, post={len(post_acc)}"
    )
    for (pre_thresh, pre_prob), (post_thresh, post_prob) in zip(pre_acc, post_acc):
        assert pre_thresh == post_thresh, (
            f"Accuracy threshold mismatch: pre={pre_thresh}, post={post_thresh}"
        )
        assert abs(pre_prob - post_prob) < 1e-9, (
            f"Accuracy P(acc >= {pre_thresh}) changed: "
            f"pre={pre_prob:.9f}, post={post_prob:.9f}"
        )
except Exception as e:
    t4c_pass = False
    t4c_error = str(e)

if t4c_pass:
    print("PASS: Property 4c — defense cancel does not affect accuracy distribution (2U pool)")
    passed += 1
else:
    print(f"FAIL: Property 4c — {t4c_error}")
    failed += 1
    errors.append(("Property 4c", t4c_error))

# --- Property 4d: Defense reroll with mixed pool (1R 1U) never targets accuracy ---
t4d_pass = True
t4d_error = None

try:
    # Red die has R_acc, blue die has U_acc — neither should be targeted
    pool = DicePool(red=1, blue=1, black=0, type="ship")
    defense = [DefenseEffect(type="defense_reroll", count=2, mode="gamble")]
    variants = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense,
    )
    v = variants[0]
    pre_acc_zero = v["pre_defense"]["acc_zero"]
    post_acc_zero = v["post_defense"]["acc_zero"]
    # Rerolling damage faces can produce accuracy, so P(acc=0) should
    # decrease or stay the same.
    assert post_acc_zero <= pre_acc_zero + 1e-9, (
        f"gamble reroll (1R1U): P(acc=0) increased from "
        f"{pre_acc_zero:.9f} to {post_acc_zero:.9f} — accuracy faces may have been targeted"
    )
except Exception as e:
    t4d_pass = False
    t4d_error = str(e)

if t4d_pass:
    print("PASS: Property 4d — gamble reroll does not target accuracy (1R 1U pool)")
    passed += 1
else:
    print(f"FAIL: Property 4d — {t4d_error}")
    failed += 1
    errors.append(("Property 4d", t4d_error))

# --- Property 4e: Defense cancel with mixed pool (1R 1U 1B) preserves accuracy ---
t4e_pass = True
t4e_error = None

try:
    pool = DicePool(red=1, blue=1, black=1, type="ship")
    defense = [DefenseEffect(type="defense_cancel", count=2)]
    variants = generate_report(
        pool, [], ["max_damage"],
        backend="combinatorial",
        defense_pipeline=defense,
    )
    v = variants[0]
    pre_acc = v["pre_defense"]["accuracy"]
    post_acc = v["post_defense"]["accuracy"]
    assert len(pre_acc) == len(post_acc), (
        f"Accuracy distribution length mismatch: pre={len(pre_acc)}, post={len(post_acc)}"
    )
    for (pre_thresh, pre_prob), (post_thresh, post_prob) in zip(pre_acc, post_acc):
        assert abs(pre_prob - post_prob) < 1e-9, (
            f"Accuracy P(acc >= {pre_thresh}) changed: "
            f"pre={pre_prob:.9f}, post={post_prob:.9f}"
        )
except Exception as e:
    t4e_pass = False
    t4e_error = str(e)

if t4e_pass:
    print("PASS: Property 4e — defense cancel preserves accuracy (1R 1U 1B pool)")
    passed += 1
else:
    print(f"FAIL: Property 4e — {t4e_error}")
    failed += 1
    errors.append(("Property 4e", t4e_error))

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
