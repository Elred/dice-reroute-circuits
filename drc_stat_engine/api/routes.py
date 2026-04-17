import traceback
from flask import Blueprint, request, jsonify
from drc_stat_engine.stats.dice_models import (
    Condition,
    DicePool, AttackEffect, DefenseEffect,
    VALID_ATTACK_EFFECT_TYPES,
    validate_dice_pool, validate_attack_effect_pipeline,
    validate_defense_pipeline,
)
from drc_stat_engine.stats.strategies import STRATEGY_PRIORITY_LISTS
from drc_stat_engine.stats.report_engine import generate_report
from drc_stat_engine.stats.profiles import (
    red_die_ship, blue_die_ship, black_die_ship,
    red_die_squad, blue_die_squad, black_die_squad,
)

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def parse_report_request(data: dict):
    """Parse JSON body into DicePool, List[AttackEffect], and strategies list."""
    try:
        dp = data["dice_pool"]
    except KeyError:
        raise KeyError("dice_pool")

    pool = DicePool(
        red=dp.get("red", 0),
        blue=dp.get("blue", 0),
        black=dp.get("black", 0),
        type=dp.get("type", "ship"),
    )

    # Resolve "any" count to pool size at each pipeline position.
    # Pool size grows as add_dice ops are encountered.
    running_size = pool.red + pool.blue + pool.black
    pipeline = []
    for op in data.get("pipeline", []):
        raw_count = op.get("count", 1)
        if op["type"] == "add_dice":
            d = op.get("dice_to_add") or {}
            running_size += d.get("red", 0) + d.get("blue", 0) + d.get("black", 0)
            resolved_count = raw_count if raw_count != "any" else running_size
        elif op["type"] == "add_set_die":
            running_size += 1
            resolved_count = running_size if raw_count == "any" else int(raw_count)
        else:
            resolved_count = running_size if raw_count == "any" else int(raw_count)
        target_result = None
        if op["type"] == "change_die":
            target_result = op["target_result"]  # raises KeyError if missing → HTTP 400
        if op["type"] == "add_set_die":
            target_result = op["target_result"]  # raises KeyError if missing → HTTP 400

        # Parse optional face_condition (REQ-16.2)
        face_condition = op.get("face_condition", None)

        # Parse optional color_in_pool and color_priority for add_dice (REQ-16.3)
        color_in_pool = op.get("color_in_pool", False)
        color_priority = op.get("color_priority", None)

        # Parse optional condition for reroll_all
        condition = None
        raw_condition = op.get("condition")
        if raw_condition:
            condition = Condition(
                attribute=raw_condition["attribute"],
                operator=raw_condition["operator"],
                threshold=raw_condition["threshold"],
            )

        pipeline.append(AttackEffect(
            type=op["type"],
            count=resolved_count,
            applicable_results=op.get("applicable_results", []),
            dice_to_add=op.get("dice_to_add"),
            target_result=target_result,
            face_condition=face_condition,
            color_in_pool=color_in_pool,
            color_priority=color_priority,
            condition=condition,
        ))

    strategies = data.get("strategies", ["max_damage"])
    if len(strategies) != 1:
        raise ValueError("Exactly one strategy must be provided.")

    defense_pipeline = []
    for dp_entry in data.get("defense_pipeline", []):
        defense_pipeline.append(DefenseEffect(
            type=dp_entry["type"],
            count=dp_entry.get("count", 1),
            mode=dp_entry.get("mode"),
            amount=dp_entry.get("amount", 0),
            applicable_results=dp_entry.get("applicable_results", []),
        ))

    return pool, pipeline, strategies, defense_pipeline


@api_bp.route("/report", methods=["POST"])
def report():
    # REQ-3.1: invalid/missing JSON body → 400
    if not request.is_json:
        return jsonify({"error": "Invalid JSON"}), 400
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        pool, pipeline, strategies, defense_pipeline = parse_report_request(data)
    except KeyError as e:
        return jsonify({"error": f"Missing field: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 422

    precision = request.args.get("precision", "normal")
    sample_count = 100_000 if precision == "high" else 10_000

    try:
        # REQ-3.2 / REQ-3.3: validation errors → 422
        validate_dice_pool(pool)
        validate_attack_effect_pipeline(pipeline, pool)

        if defense_pipeline:
            validate_defense_pipeline(defense_pipeline)

        # REQ-3.4: unknown strategy → 422 (raised inside generate_report)
        variants = generate_report(pool, pipeline, strategies, sample_count=sample_count, defense_pipeline=defense_pipeline)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"variants": variants}), 200


@api_bp.route("/meta", methods=["GET"])
def meta():
    """REQ-2.1 / REQ-2.2 / REQ-2.3: derive all metadata from live imports."""
    result_values = {
        "ship": {
            "red":   [f["value"] for f in red_die_ship],
            "blue":  [f["value"] for f in blue_die_ship],
            "black": [f["value"] for f in black_die_ship],
        },
        "squad": {
            "red":   [f["value"] for f in red_die_squad],
            "blue":  [f["value"] for f in blue_die_squad],
            "black": [f["value"] for f in black_die_squad],
        },
    }
    return jsonify({
        "dice_types": ["ship", "squad"],
        "strategies": {k: list(v.keys()) for k, v in STRATEGY_PRIORITY_LISTS.items()},
        "attack_effect_types": sorted(VALID_ATTACK_EFFECT_TYPES),
        "result_values": result_values,
        "strategy_priority_lists": {
            type_str: {
                strategy: {
                    "reroll": lists["reroll"],
                    "cancel": lists.get("cancel", []),
                    "change_die": lists["change_die"],
                }
                for strategy, lists in strategies.items()
            }
            for type_str, strategies in STRATEGY_PRIORITY_LISTS.items()
        },
    }), 200
