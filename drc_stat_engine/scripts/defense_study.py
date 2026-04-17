#!/usr/bin/env python3
"""
defense_study.py — Run a defense impact study from a YAML scenario file.

Computes exact probability distributions for each attack (combinatorial backend,
pool size <= 3), applies per-attack defense effects, sums total damage across
all attacks, and outputs a CSV with per-attack and total statistics including
quantiles (P5, P20, P50, P80, P95).

Usage:
    python -m drc_stat_engine.scripts.defense_study <study.yaml> [output.csv]

If output.csv is omitted, prints to stdout.
"""

import sys
import csv
import yaml
import numpy as np
from typing import List, Dict, Any

from drc_stat_engine.stats.dice_models import (
    DicePool, AttackEffect, DefenseEffect,
    validate_dice_pool, validate_attack_effect_pipeline, validate_defense_pipeline,
)
from drc_stat_engine.stats.strategies import build_strategy_pipeline
from drc_stat_engine.stats.report_engine import run_pipeline, run_defense_pipeline
import drc_stat_engine.stats.dice_maths_combinatories as combinatories


# ---------------------------------------------------------------------------
# Distribution helpers
# ---------------------------------------------------------------------------

def roll_to_damage_dist(roll_df) -> Dict[int, float]:
    """Extract {damage_value: probability} from a roll DataFrame."""
    grouped = roll_df.groupby("damage")["proba"].sum()
    return {int(d): float(p) for d, p in grouped.items()}


def convolve_distributions(dists: List[Dict[int, float]]) -> Dict[int, float]:
    """Convolve (sum) independent damage distributions."""
    if not dists:
        return {0: 1.0}
    result = dists[0].copy()
    for dist in dists[1:]:
        new_result: Dict[int, float] = {}
        for d1, p1 in result.items():
            for d2, p2 in dist.items():
                new_result[d1 + d2] = new_result.get(d1 + d2, 0.0) + p1 * p2
        result = new_result
    return result


def dist_stats(dist: Dict[int, float]) -> Dict[str, float]:
    """Compute statistics from a damage distribution."""
    if not dist:
        return {"avg": 0, "p5": 0, "p20": 0, "p50": 0, "p80": 0, "p95": 0, "prob_zero": 1.0}
    sorted_items = sorted(dist.items())
    damages = [d for d, _ in sorted_items]
    probas = [p for _, p in sorted_items]
    avg = sum(d * p for d, p in sorted_items)
    prob_zero = dist.get(0, 0.0)
    cumulative = np.cumsum(probas)

    def quantile(q: float) -> int:
        for i, c in enumerate(cumulative):
            if c >= q - 1e-12:
                return damages[i]
        return damages[-1]

    return {
        "avg": avg,
        "p5": quantile(0.05),
        "p20": quantile(0.20),
        "p50": quantile(0.50),
        "p80": quantile(0.80),
        "p95": quantile(0.95),
        "prob_zero": prob_zero,
    }


# ---------------------------------------------------------------------------
# Attack resolution
# ---------------------------------------------------------------------------

def resolve_attack(
    pool: DicePool,
    strategy: str,
    attack_effects: List[AttackEffect],
    defense_effects: List[DefenseEffect],
) -> tuple:
    """Resolve a single attack.
    Returns (pre_defense_dist, post_defense_dist, saved_dist).
    saved_dist is {saved_damage: probability} where saved = pre_damage - post_damage per outcome.
    """
    validate_dice_pool(pool)
    validate_attack_effect_pipeline(attack_effects, pool)
    roll_df = combinatories.combine_dice(pool.red, pool.blue, pool.black, pool.type)
    strategy_pipeline = build_strategy_pipeline(attack_effects, strategy, pool.type)
    roll_df = run_pipeline(roll_df, strategy_pipeline, pool.type, backend_mod=combinatories)
    pre_dist = roll_to_damage_dist(roll_df)

    if defense_effects:
        validate_defense_pipeline(defense_effects)
        defended_df = run_defense_pipeline(roll_df.copy(), defense_effects, pool.type, backend_mod=combinatories)
        post_dist = roll_to_damage_dist(defended_df)

        # Compute saved damage distribution by running defense on each pre-defense
        # outcome individually. Each row in roll_df is a specific dice result with
        # known damage. Running the defense pipeline on it gives the conditional
        # post-defense distribution for that exact roll. This correctly tracks the
        # joint (pre_damage, post_damage) through rerolls.
        saved_dist: Dict[int, float] = {}
        for _, pre_row in roll_df.iterrows():
            pre_damage = int(pre_row["damage"])
            pre_proba = float(pre_row["proba"])
            # Build a single-row DataFrame for this outcome
            single = roll_df[roll_df["value"] == pre_row["value"]].copy()
            single["proba"] = single["proba"] / single["proba"].sum()  # normalize
            # Run defense on this single outcome
            post_single = run_defense_pipeline(single, defense_effects, pool.type, backend_mod=combinatories)
            # Each post row is a possible post-defense result for this pre-defense outcome
            for _, post_row in post_single.iterrows():
                post_damage = int(post_row["damage"])
                post_proba = float(post_row["proba"])
                s = pre_damage - post_damage
                saved_dist[s] = saved_dist.get(s, 0.0) + pre_proba * post_proba
    else:
        post_dist = pre_dist.copy()
        saved_dist = {0: 1.0}

    return pre_dist, post_dist, saved_dist


# ---------------------------------------------------------------------------
# YAML parsing
# ---------------------------------------------------------------------------

def parse_pool(d: dict) -> DicePool:
    return DicePool(
        red=d.get("red", 0),
        blue=d.get("blue", 0),
        black=d.get("black", 0),
        type=d.get("type", "ship"),
    )


def parse_attack_effects(effects_list: list) -> List[AttackEffect]:
    if not effects_list:
        return []
    result = []
    for e in effects_list:
        result.append(AttackEffect(
            type=e["type"],
            count=e.get("count", 1),
            applicable_results=e.get("applicable_results", []),
            dice_to_add=e.get("dice_to_add"),
            target_result=e.get("target_result"),
        ))
    return result


def parse_defense_effects(effects_list: list) -> List[DefenseEffect]:
    if not effects_list:
        return []
    result = []
    for e in effects_list:
        result.append(DefenseEffect(
            type=e["type"],
            count=e.get("count", 1),
            mode=e.get("mode"),
            amount=e.get("amount", 0),
            applicable_results=e.get("applicable_results", []),
        ))
    return result


# ---------------------------------------------------------------------------
# Main study runner
# ---------------------------------------------------------------------------

def run_study(study_path: str, include_quantiles: bool = False):
    """Run a defense study from a YAML file.
    Returns (rows, fields, total_pre_dist, total_post_dist, total_saved_dist, column_labels).
    """
    with open(study_path) as f:
        study = yaml.safe_load(f)

    attacks = study["attacks"]
    column_labels = study.get("column_labels", {})

    pre_dists = []
    post_dists = []
    saved_dists = []
    attack_data = []  # (label, pre_stats, post_stats)

    for attack in attacks:
        pool = parse_pool(attack["pool"])
        total_dice = pool.red + pool.blue + pool.black
        if total_dice > 3:
            raise ValueError(
                f"Attack '{attack['label']}' has {total_dice} dice, "
                f"max 3 for combinatorial study."
            )
        strategy = attack.get("strategy", "max_damage")
        attack_effects = parse_attack_effects(attack.get("attack_effects", []))
        defense_effects = parse_defense_effects(attack.get("defense_effects", []))

        pre_dist, post_dist, saved_dist = resolve_attack(pool, strategy, attack_effects, defense_effects)
        pre_dists.append(pre_dist)
        post_dists.append(post_dist)
        saved_dists.append(saved_dist)
        attack_data.append((attack["label"], dist_stats(pre_dist), dist_stats(post_dist)))

    # Convolve to get total distributions
    total_pre_dist = convolve_distributions(pre_dists)
    total_post_dist = convolve_distributions(post_dists)
    total_saved_dist = convolve_distributions(saved_dists)
    total_pre = dist_stats(total_pre_dist)
    total_post = dist_stats(total_post_dist)

    fields = ["avg"]
    if include_quantiles:
        fields += ["p5", "p20", "p50", "p80", "p95"]

    def make_row(label: str, pre_s: dict, post_s: dict) -> Dict[str, Any]:
        row: Dict[str, Any] = {"label": label}
        for q in fields:
            row[f"pre_{q}"] = pre_s[q]
            row[f"post_{q}"] = post_s[q]
            row[f"diff_{q}"] = pre_s[q] - post_s[q]
        return row

    rows = []
    for label, pre_s, post_s in attack_data:
        rows.append(make_row(label, pre_s, post_s))
    rows.append(make_row("TOTAL", total_pre, total_post))

    return rows, fields, total_pre_dist, total_post_dist, total_saved_dist, column_labels


def cumulative_from_dist(dist: Dict[int, float]) -> List[tuple]:
    """Return [(x, P(value >= x))] for x in min..max of dist keys."""
    if not dist:
        return [(0, 1.0)]
    min_d = min(dist.keys())
    max_d = max(dist.keys())
    result = []
    for x in range(min_d, max_d + 1):
        p = sum(prob for d, prob in dist.items() if d >= x)
        result.append((x, p))
    return result


def write_cumulative_csv(cumul: List[tuple], out):
    """Write cumulative distribution as semicolon-separated CSV."""
    out.write("damage_threshold;probability\n")
    for x, p in cumul:
        out.write(f"{x};{format_value(p)}\n")


def get_columns(fields: List[str]) -> List[str]:
    cols = ["label"]
    for q in fields:
        cols.extend([f"pre_{q}", f"post_{q}", f"diff_{q}"])
    return cols


def resolve_column_labels(columns: List[str], column_labels: dict) -> List[str]:
    """Map internal column IDs to display labels from YAML config."""
    # Default display names
    defaults = {
        "label": "Label",
        "pre_avg": "Average Damage",
        "post_avg": "Average after Defense",
        "diff_avg": "Average Saved",
        "threshold": "Damage",
        "cumul_pre": "Cumulated Damage",
        "cumul_post": "Cumulated after Defense",
        "cumul_saved": "Cumulated Saved Damage",
    }
    merged = {**defaults, **column_labels}
    return [merged.get(c, c) for c in columns]


def format_value(v: Any) -> str:
    """Format a value for CSV: use comma as decimal separator."""
    if isinstance(v, float):
        return str(v).replace(".", ",")
    return str(v)


def write_csv(rows: List[Dict[str, Any]], columns: List[str], out):
    """Write rows as semicolon-separated CSV with comma decimals."""
    out.write(";".join(columns) + "\n")
    for row in rows:
        out.write(";".join(format_value(row.get(c, "")) for c in columns) + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m drc_stat_engine.scripts.defense_study <study.yaml> [output.csv] [--quantiles]")
        sys.exit(1)

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    include_quantiles = "--quantiles" in flags

    study_path = args[0]
    output_path = args[1] if len(args) > 1 else None

    rows, fields, total_pre_dist, total_post_dist, total_saved_dist, column_labels = run_study(study_path, include_quantiles=include_quantiles)
    columns = get_columns(fields)
    display_columns = resolve_column_labels(columns, column_labels)

    if output_path:
        with open(output_path, "w", newline="") as f:
            # Write header with display labels
            f.write("\t".join(display_columns) + "\n")
            for row in rows:
                f.write("\t".join(format_value(row.get(c, "")) for c in columns) + "\n")
        print(f"Wrote {len(rows)} rows to {output_path}")

        # Write combined cumulative distribution CSV
        base = output_path.rsplit(".", 1)[0] if "." in output_path else output_path
        cumul_pre = dict(cumulative_from_dist(total_pre_dist))
        cumul_post = dict(cumulative_from_dist(total_post_dist))
        cumul_saved = dict(cumulative_from_dist(total_saved_dist))

        all_keys = set(cumul_pre.keys()) | set(cumul_post.keys()) | set(cumul_saved.keys())
        t_min = min(all_keys)
        t_max = max(all_keys)

        cumul_columns = ["threshold", "cumul_pre", "cumul_post", "cumul_saved"]
        cumul_display = resolve_column_labels(cumul_columns, column_labels)

        cumul_path = f"{base}_cumul.csv"
        with open(cumul_path, "w", newline="") as f:
            f.write("\t".join(cumul_display) + "\n")
            for t in range(t_min, t_max + 1):
                pre_v = format_value(cumul_pre[t]) if t in cumul_pre else ""
                post_v = format_value(cumul_post[t]) if t in cumul_post else ""
                saved_v = format_value(cumul_saved[t]) if t in cumul_saved else ""
                f.write(f"{t}\t{pre_v}\t{post_v}\t{saved_v}\n")

        print(f"Wrote cumulative CSV: {cumul_path}")
    else:
        sys.stdout.write("\t".join(display_columns) + "\n")
        for row in rows:
            sys.stdout.write("\t".join(format_value(row.get(c, "")) for c in columns) + "\n")


if __name__ == "__main__":
    main()
