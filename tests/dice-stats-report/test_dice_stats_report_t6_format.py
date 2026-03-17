"""
Tests for task 6.2: format_report output.
Covers header content, damage table formatting, strategy labeling, and single-variant behavior.
Requirements: 7.2, 7.3, 7.6
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'stats'))

from report import DicePool, Operation, format_report

PASS = 0
FAIL = 0


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"PASS: {label}")
        PASS += 1
    else:
        print(f"FAIL: {label}" + (f" — {detail}" if detail else ""))
        FAIL += 1


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

pool_3r2b = DicePool(red=3, blue=0, black=2, type="ship")

pipeline_reroll = [
    Operation(type="reroll", count=1, applicable_results=["R_blank", "B_blank"]),
    Operation(type="cancel", count=2, applicable_results=["R_blank", "B_blank", "R_hit"]),
]

single_variant = [
    {
        "label": "max_damage",
        "damage": [(0, 1.0), (1, 0.753), (2, 0.438)],
        "accuracy": [(0, 1.0), (1, 0.188)],
        "crit": 0.438,
    }
]

multi_variants = [
    {
        "label": "max_damage",
        "damage": [(0, 1.0), (1, 0.753), (2, 0.438)],
        "accuracy": [(0, 1.0), (1, 0.188)],
        "crit": 0.438,
    },
    {
        "label": "max_accuracy",
        "damage": [(0, 1.0), (1, 0.600), (2, 0.300)],
        "accuracy": [(0, 1.0), (1, 0.500)],
        "crit": 0.200,
    },
]

# ---------------------------------------------------------------------------
# 7.2 — Header contains dice pool counts and type
# ---------------------------------------------------------------------------

output_single = format_report(pool_3r2b, pipeline_reroll, single_variant)
header_line = output_single.splitlines()[0]

check(
    "header contains red count",
    "3R" in header_line,
    f"header={header_line!r}",
)
check(
    "header contains blue count",
    "0U" in header_line,
    f"header={header_line!r}",
)
check(
    "header contains black count",
    "2B" in header_line,
    f"header={header_line!r}",
)
check(
    "header contains dice type 'ship'",
    "ship" in header_line,
    f"header={header_line!r}",
)

# Pipeline line present
pipeline_line = output_single.splitlines()[1]
check(
    "pipeline line present",
    "Pipeline:" in pipeline_line,
    f"pipeline_line={pipeline_line!r}",
)
check(
    "pipeline line contains operation type",
    "reroll" in pipeline_line,
    f"pipeline_line={pipeline_line!r}",
)

# ---------------------------------------------------------------------------
# 7.3 — Damage table rows formatted to 1 decimal place
# ---------------------------------------------------------------------------

check(
    "damage table row >= 0 shows 100.0%",
    "100.0%" in output_single,
    f"output={output_single!r}",
)
check(
    "damage table row >= 1 shows 75.3%",
    "75.3%" in output_single,
    f"output={output_single!r}",
)
check(
    "damage table row >= 2 shows 43.8%",
    "43.8%" in output_single,
    f"output={output_single!r}",
)

# Accuracy table
check(
    "accuracy table row >= 1 shows 18.8%",
    "18.8%" in output_single,
    f"output={output_single!r}",
)

# Crit probability line
check(
    "crit probability shows 43.8%",
    "Crit Probability: 43.8%" in output_single,
    f"output={output_single!r}",
)

# ---------------------------------------------------------------------------
# 7.6 — Multiple variants: strategy sections labeled correctly
# ---------------------------------------------------------------------------

output_multi = format_report(pool_3r2b, pipeline_reroll, multi_variants)

check(
    "multi-variant output contains 'Strategy: max_damage'",
    "Strategy: max_damage" in output_multi,
    f"output={output_multi!r}",
)
check(
    "multi-variant output contains 'Strategy: max_accuracy'",
    "Strategy: max_accuracy" in output_multi,
    f"output={output_multi!r}",
)
check(
    "multi-variant output contains separator line",
    "=" * 10 in output_multi,
    f"output={output_multi!r}",
)

# ---------------------------------------------------------------------------
# 6.5 / 7.6 — Single variant shows strategy label
# ---------------------------------------------------------------------------

check(
    "single variant shows 'Strategy:' label",
    "Strategy:" in output_single,
    f"output={output_single!r}",
)

# ---------------------------------------------------------------------------
# Edge: empty pipeline shows '(none)' in pipeline line
# ---------------------------------------------------------------------------

output_empty_pipe = format_report(DicePool(red=1, blue=0, black=0, type="ship"), [], single_variant)
check(
    "empty pipeline shows '(none)' in pipeline line",
    "(none)" in output_empty_pipe,
    f"output={output_empty_pipe!r}",
)

# ---------------------------------------------------------------------------
print(f"\n{'='*40}")
print(f"Results: {PASS} passed, {FAIL} failed")
