import traceback
from flask import Blueprint, request, jsonify
from drc_stat_engine.stats.report import (
    generate_report, validate_dice_pool, validate_operation_pipeline,
    DicePool, Operation, STRATEGY_PRIORITY_LISTS, VALID_OPERATION_TYPES,
)
from drc_stat_engine.stats.profiles import (
    red_die_ship, blue_die_ship, black_die_ship,
    red_die_squad, blue_die_squad, black_die_squad,
)

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def parse_report_request(data: dict):
    """Parse JSON body into DicePool, List[Operation], and strategies list."""
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

    pipeline = []
    for op in data.get("pipeline", []):
        pipeline.append(Operation(
            type=op["type"],
            count=op.get("count", 1),
            applicable_results=op.get("applicable_results", []),
            dice_to_add=op.get("dice_to_add"),
        ))

    strategies = data.get("strategies", ["max_damage"])
    return pool, pipeline, strategies


@api_bp.route("/report", methods=["POST"])
def report():
    # REQ-3.1: invalid/missing JSON body → 400
    if not request.is_json:
        return jsonify({"error": "Invalid JSON"}), 400
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        pool, pipeline, strategies = parse_report_request(data)
    except KeyError as e:
        return jsonify({"error": f"Missing field: {e}"}), 400

    try:
        # REQ-3.2 / REQ-3.3: validation errors → 422
        validate_dice_pool(pool)
        validate_operation_pipeline(pipeline, pool)

        # REQ-3.4: unknown strategy → 422 (raised inside generate_report)
        variants = generate_report(pool, pipeline, strategies)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"variants": variants}), 200


@api_bp.route("/meta", methods=["GET"])
def meta():
    """REQ-2.1 / REQ-2.2 / REQ-2.3: derive all metadata from live imports."""
    face_values = {
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
        "operation_types": sorted(VALID_OPERATION_TYPES),
        "face_values": face_values,
    }), 200
