"""
Property-based tests for set-die-result feature.
Uses Hypothesis to verify correctness properties.

Feature: set-die-result
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from drc_stat_engine.stats.dice_maths_combinatories import (
    set_die_face, combine_dice, _resolve_color_agnostic_result, _all_pool_results,
    value_to_dice_attr_dict,
)
from drc_stat_engine.stats.dice_models import (
    AttackEffect, DicePool,
)
from drc_stat_engine.stats.strategies import (
    build_strategy_pipeline, STRATEGY_PRIORITY_LISTS,
)
from drc_stat_engine.stats.report_engine import run_pipeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALL_SHIP_FACES = [f["value"] for f in _all_pool_results("ship")]
ALL_SQUAD_FACES = [f["value"] for f in _all_pool_results("squad")]
COLOR_AGNOSTIC_FACES = ["hit", "crit", "blank", "acc", "hit+hit", "hit+crit"]

PROB_TOL = 1e-9


def make_single_die_df(type_str="ship"):
    """Return a 1-die roll DataFrame for a red die."""
    return combine_dice(1, 0, 0, type_str)


def make_roll_df(red=1, blue=1, black=0, type_str="ship"):
    return combine_dice(red, blue, black, type_str)


# ---------------------------------------------------------------------------
# Property 1: Probability invariant after set_die_face
# Feature: set-die-result, Property 1: probability invariant after set_die_face
# Validates: Requirements 3.6
# ---------------------------------------------------------------------------

@given(
    red=st.integers(min_value=0, max_value=2),
    blue=st.integers(min_value=0, max_value=2),
    black=st.integers(min_value=0, max_value=2),
    type_str=st.sampled_from(["ship", "squad"]),
    n_sources=st.integers(min_value=1, max_value=3),
    seed=st.integers(min_value=0, max_value=99),
)
@settings(max_examples=100)
def test_set_die_face_probability_invariant(red, blue, black, type_str, n_sources, seed):
    """Property 1: probabilities sum to 1.0 after set_die_face for any valid inputs."""
    assume(red + blue + black >= 1)
    all_faces = ALL_SHIP_FACES if type_str == "ship" else ALL_SQUAD_FACES
    rng = np.random.default_rng(seed)
    source_faces = list(rng.choice(all_faces, size=min(n_sources, len(all_faces)), replace=False))
    target_face = rng.choice(all_faces)

    roll_df = combine_dice(red, blue, black, type_str)
    result_df = set_die_face(roll_df, source_faces, target_face, type_str)

    total = result_df["proba"].sum()
    assert abs(total - 1.0) <= PROB_TOL, (
        f"Probability sum {total} deviates from 1.0 by {abs(total - 1.0)} "
        f"(pool={red}R{blue}U{black}B {type_str}, sources={source_faces}, target={target_face})"
    )


# ---------------------------------------------------------------------------
# Property 2: No-op when no source face present
# Feature: set-die-result, Property 2: no-op when no source face present
# Validates: Requirements 3.2
# ---------------------------------------------------------------------------

@given(
    red=st.integers(min_value=1, max_value=2),
    blue=st.integers(min_value=0, max_value=2),
    black=st.integers(min_value=0, max_value=2),
    type_str=st.sampled_from(["ship", "squad"]),
)
@settings(max_examples=100)
def test_set_die_face_noop_when_no_source(red, blue, black, type_str):
    """Property 2: returns unchanged df when no outcome contains any source face."""
    roll_df = combine_dice(red, blue, black, type_str)
    # Use a source face that cannot appear in any outcome (empty list)
    result_df = set_die_face(roll_df, [], "R_hit", type_str)
    left = roll_df.sort_values("value").reset_index(drop=True)
    right = result_df.sort_values("value").reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right)


# ---------------------------------------------------------------------------
# Property 3: Result to set appears after substitution
# Feature: set-die-result, Property 3: target face appears after substitution
# Validates: Requirements 3.3
# ---------------------------------------------------------------------------

@given(
    type_str=st.sampled_from(["ship", "squad"]),
    seed=st.integers(min_value=0, max_value=99),
)
@settings(max_examples=100)
def test_set_die_face_target_appears(type_str, seed):
    """Property 3: every affected outcome contains the resolved target face."""
    all_faces = ALL_SHIP_FACES if type_str == "ship" else ALL_SQUAD_FACES
    rng = np.random.default_rng(seed)
    source_face = rng.choice(all_faces)
    target_face = rng.choice(all_faces)

    roll_df = combine_dice(1, 0, 0, type_str)
    # Only test when at least one outcome has the source face
    has_source = roll_df["value"].apply(lambda v: source_face in v.split(" ")).any()
    assume(has_source)

    result_df = set_die_face(roll_df, [source_face], target_face, type_str)

    # Resolve target for comparison
    resolved_target = target_face
    if "_" not in target_face:
        resolved_target = _resolve_color_agnostic_result(target_face, type_str)

    # All rows that previously had the source face should now have the target face
    original_with_source = roll_df[roll_df["value"].apply(lambda v: source_face in v.split(" "))]
    for _, orig_row in original_with_source.iterrows():
        orig_tokens = orig_row["value"].split(" ")
        new_tokens = orig_tokens.copy()
        new_tokens.remove(source_face)
        new_tokens.append(resolved_target)
        expected_value = " ".join(sorted(new_tokens))
        assert expected_value in result_df["value"].values, (
            f"Expected value '{expected_value}' not found in result after substituting "
            f"'{source_face}' → '{resolved_target}'"
        )


# ---------------------------------------------------------------------------
# Property 4: Stat columns reflect substitution
# Feature: set-die-result, Property 4: stat columns reflect substitution
# Validates: Requirements 3.4
# ---------------------------------------------------------------------------

@given(
    type_str=st.sampled_from(["ship", "squad"]),
    seed=st.integers(min_value=0, max_value=99),
)
@settings(max_examples=100)
def test_set_die_face_stat_columns(type_str, seed):
    """Property 4: stat delta = target_attrs - source_attrs for each affected row."""
    all_faces = ALL_SHIP_FACES if type_str == "ship" else ALL_SQUAD_FACES
    rng = np.random.default_rng(seed)
    source_face = rng.choice(all_faces)
    target_face = rng.choice(all_faces)

    roll_df = combine_dice(1, 0, 0, type_str)
    has_source = roll_df["value"].apply(lambda v: source_face in v.split(" ")).any()
    assume(has_source)

    result_df = set_die_face(roll_df, [source_face], target_face, type_str)

    resolved_target = target_face
    if "_" not in target_face:
        resolved_target = _resolve_color_agnostic_result(target_face, type_str)

    src_attrs = value_to_dice_attr_dict(source_face, type_str)
    tgt_attrs = value_to_dice_attr_dict(resolved_target, type_str)

    for _, orig_row in roll_df[roll_df["value"].apply(lambda v: source_face in v.split(" "))].iterrows():
        orig_tokens = orig_row["value"].split(" ")
        new_tokens = orig_tokens.copy()
        new_tokens.remove(source_face)
        new_tokens.append(resolved_target)
        expected_value = " ".join(sorted(new_tokens))

        result_rows = result_df[result_df["value"] == expected_value]
        assert not result_rows.empty, f"Expected row with value '{expected_value}' not found"
        result_row = result_rows.iloc[0]

        for stat in ["damage", "crit", "acc", "blank"]:
            expected = orig_row[stat] - src_attrs[stat] + tgt_attrs[stat]
            assert result_row[stat] == expected, (
                f"Stat '{stat}': expected {expected}, got {result_row[stat]} "
                f"(source={source_face}, target={resolved_target})"
            )


# ---------------------------------------------------------------------------
# Property 5: Color-agnostic target resolves to a valid pool face
# Feature: set-die-result, Property 5: color-agnostic target resolves to valid pool face
# Validates: Requirements 3.7
# ---------------------------------------------------------------------------

@given(
    type_str=st.sampled_from(["ship", "squad"]),
    target_suffix=st.sampled_from(["hit", "crit", "blank", "acc", "hit+hit", "hit+crit"]),
)
@settings(max_examples=100)
def test_set_die_face_color_agnostic_resolution(type_str, target_suffix):
    """Property 5: color-agnostic target resolves to a face in the pool with max score."""
    all_faces = _all_pool_results(type_str)
    candidates = [f for f in all_faces if f["value"].split("_", 1)[-1] == target_suffix]
    assume(len(candidates) > 0)

    resolved = _resolve_color_agnostic_result(target_suffix, type_str)

    # Must be a valid pool face
    pool_values = [f["value"] for f in all_faces]
    assert resolved in pool_values, f"Resolved face '{resolved}' not in pool for {type_str}"

    # Must have the maximum score
    resolved_face = next(f for f in all_faces if f["value"] == resolved)
    resolved_score = resolved_face["damage"] + resolved_face["crit"] + resolved_face["acc"]
    max_score = max(f["damage"] + f["crit"] + f["acc"] for f in candidates)
    assert resolved_score == max_score, (
        f"Resolved face '{resolved}' has score {resolved_score}, but max is {max_score}"
    )


# ---------------------------------------------------------------------------
# Property 6: Pipeline probability integrity preserved end-to-end
# Feature: set-die-result, Property 6: pipeline probability integrity preserved end-to-end
# Validates: Requirements 3.6, 4.1
# ---------------------------------------------------------------------------

@given(
    red=st.integers(min_value=1, max_value=2),
    blue=st.integers(min_value=0, max_value=2),
    black=st.integers(min_value=0, max_value=2),
    type_str=st.sampled_from(["ship", "squad"]),
    strategy=st.sampled_from(["max_damage", "max_accuracy", "max_crits", "max_doubles"]),
    seed=st.integers(min_value=0, max_value=99),
)
@settings(max_examples=100)
def test_set_die_pipeline_probability_integrity(red, blue, black, type_str, strategy, seed):
    """Property 6: full pipeline with set_die preserves probability sum = 1.0."""
    assume(red + blue + black >= 1)
    # max_doubles only defined for ship
    if type_str == "squad" and strategy == "max_doubles":
        strategy = "max_damage"

    all_faces = ALL_SHIP_FACES if type_str == "ship" else ALL_SQUAD_FACES
    rng = np.random.default_rng(seed)
    applicable = list(rng.choice(all_faces, size=min(3, len(all_faces)), replace=False))
    target_face = rng.choice(all_faces)

    pool = DicePool(red=red, blue=blue, black=black, type=type_str)
    pipeline = [AttackEffect(
        type="set_die",
        applicable_results=applicable,
        target_result=target_face,
    )]

    from drc_stat_engine.stats.dice_maths_combinatories import combine_dice as cd
    roll_df = cd(red, blue, black, type_str)
    strategy_pipeline = build_strategy_pipeline(pipeline, strategy, type_str)
    result_df = run_pipeline(roll_df, strategy_pipeline, type_str)

    total = result_df["proba"].sum()
    assert abs(total - 1.0) <= PROB_TOL, (
        f"Pipeline probability sum {total} deviates from 1.0 "
        f"(pool={red}R{blue}U{black}B {type_str}, strategy={strategy})"
    )


# ---------------------------------------------------------------------------
# Property 7: build_strategy_pipeline preserves target_result and produces correct priority_list
# Feature: set-die-result, Property 7: build_strategy_pipeline preserves target_result and produces correct priority_list
# Validates: Requirements 2.3, 5.6
# ---------------------------------------------------------------------------

@given(
    type_str=st.sampled_from(["ship", "squad"]),
    strategy=st.sampled_from(["max_damage", "max_accuracy", "max_crits", "max_doubles"]),
    seed=st.integers(min_value=0, max_value=99),
)
@settings(max_examples=100)
def test_set_die_build_pipeline_preserves_and_filters(type_str, strategy, seed):
    """Property 7: build_strategy_pipeline preserves target_result and filters priority_list correctly."""
    if type_str == "squad" and strategy == "max_doubles":
        strategy = "max_damage"

    all_faces = ALL_SHIP_FACES if type_str == "ship" else ALL_SQUAD_FACES
    rng = np.random.default_rng(seed)
    n = rng.integers(1, min(5, len(all_faces)) + 1)
    applicable = list(rng.choice(all_faces, size=int(n), replace=False))
    target_result = rng.choice(all_faces)

    effect = AttackEffect(
        type="set_die",
        applicable_results=applicable,
        target_result=target_result,
    )
    result_pipeline = build_strategy_pipeline([effect], strategy, type_str)
    assert len(result_pipeline) == 1
    result_effect = result_pipeline[0]

    # (a) target_result preserved
    assert result_effect.target_result == target_result, (
        f"target_result not preserved: expected '{target_result}', got '{result_effect.target_result}'"
    )

    # (b) priority_list is a subsequence of strategy ordering filtered to applicable_results
    ordering = STRATEGY_PRIORITY_LISTS[type_str][strategy]["set_die"]
    applicable_set = set(applicable)
    expected = [f for f in ordering if f in applicable_set]
    assert result_effect.priority_list == expected, (
        f"priority_list mismatch: expected {expected}, got {result_effect.priority_list}"
    )


if __name__ == "__main__":
    print("Running PBT tests...")
    test_set_die_face_probability_invariant()
    print("PASS: Property 1 - probability invariant")
    test_set_die_face_noop_when_no_source()
    print("PASS: Property 2 - no-op when no source")
    test_set_die_face_target_appears()
    print("PASS: Property 3 - target appears after substitution")
    test_set_die_face_stat_columns()
    print("PASS: Property 4 - stat columns reflect substitution")
    test_set_die_face_color_agnostic_resolution()
    print("PASS: Property 5 - color-agnostic resolution")
    test_set_die_pipeline_probability_integrity()
    print("PASS: Property 6 - pipeline probability integrity")
    test_set_die_build_pipeline_preserves_and_filters()
    print("PASS: Property 7 - build_strategy_pipeline preserves target_result")
    print("All PBT tests passed.")
