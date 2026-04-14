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
        return {"avg": 0, "p5": 0, "p20": 0, "p50": 0, "p80": 0, "p95": 0, "p_zero": 1.0}
    sorted_items = sorted(dist.items())
    damages = [d for d, _ in sorted_items]
    probas = [p for _, p in sorted_items]
    avg = sum(d * p for d, p in sorted_items)
    p_zero = dist.get(0, 0.0)
    cumulative = np.cumsum(probas)

    def quantile(q: float) -> int:
        for i, c in enumerate(cumulative):
            if c >= q - 1e-12:
                return damages[i]
        return damages[-1]

    return {
        "avg": round(avg, 3),
        "p5": quantile(0.05),
        "p20": quantile(0.20),
        "p50": quantile(0.50),
        "p80": quantile(0.80),
        "p95": quantile(0.95),
        "p_zero": round(p_zero, 4),
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
    """Resolve a single attack. Returns (pre_defense_dist, post_defense_dist)."""
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
    else:
        post_dist = pre_dist.copy()
    return pre_dist, post_dist


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

def run_study(study_path: str) -> List[Dict[str, Any]]:
    """Run a defense study from a YAML file. Returns rows for CSV output."""
    with open(study_path) as f:
        study = yaml.safe_load(f)

    attacks = study["attacks"]
    rows = []

    pre_dists = []
    post_dists = []
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

        pre_dist, post_dist = resolve_attack(pool, strategy, attack_effects, defense_effects)
        pre_dists.append(pre_dist)
        post_dists.append(post_dist)
        attack_data.append((attack["label"], dist_stats(pre_dist), dist_stats(post_dist)))

    # Convolve to get total distributions
    total_pre = dist_stats(convolve_distributions(pre_dists))
    total_post = dist_stats(convolve_distributions(post_dists))

    QUANTILES = ["avg", "p5", "p20", "p50", "p80", "p95"]

    for label, pre_s, post_s in attack_data:
        row: Dict[str, Any] = {}
        # Total stats
        for q in QUANTILES:
            row[f"total_pre_{q}"] = total_pre[q]
            row[f"total_post_{q}"] = total_post[q]
            row[f"total_diff_{q}"] = round(total_pre[q] - total_post[q], 3)
        row["total_pre_p_zero"] = total_pre["p_zero"]
        row["total_post_p_zero"] = total_post["p_zero"]
        # Per-attack stats
        row["attack"] = label
        for q in QUANTILES:
            row[f"attack_pre_{q}"] = pre_s[q]
            row[f"attack_post_{q}"] = post_s[q]
            row[f"attack_diff_{q}"] = round(pre_s[q] - post_s[q], 3)
        row["attack_pre_p_zero"] = pre_s["p_zero"]
        row["attack_post_p_zero"] = post_s["p_zero"]
        rows.append(row)

    return rows


def _build_columns():
    QUANTILES = ["avg", "p5", "p20", "p50", "p80", "p95"]
    cols = []
    for q in QUANTILES:
        cols.extend([f"total_pre_{q}", f"total_post_{q}", f"total_diff_{q}"])
    cols.extend(["total_pre_p_zero", "total_post_p_zero"])
    cols.append("attack")
    for q in QUANTILES:
        cols.extend([f"attack_pre_{q}", f"attack_post_{q}", f"attack_diff_{q}"])
    cols.extend(["attack_pre_p_zero", "attack_post_p_zero"])
    return cols

CSV_COLUMNS = _build_columns()


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m drc_stat_engine.scripts.defense_study <study.yaml> [output.csv]")
        sys.exit(1)

    study_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    rows = run_study(study_path)

    if output_path:
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} rows to {output_path}")
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
