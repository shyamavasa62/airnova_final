from typing import Any

from flask import Blueprint, jsonify, request

from backend.services.realtime_service import (
    get_city_comparison,
    get_current,
    get_forecast_48h,
    list_cities,
    step_forward,
)
from backend.utils.logger import logger

realtime_bp = Blueprint("realtime_bp", __name__)


@realtime_bp.route("/realtime/cities", methods=["GET"])
def realtime_cities():
    try:
        return jsonify({"cities": list_cities()})
    except Exception:
        logger.exception("Failed to list cities")
        return jsonify({"error": "Internal server error"}), 500


@realtime_bp.route("/realtime/current", methods=["GET"])
def realtime_current():
    city = request.args.get("city", "Delhi")
    try:
        return jsonify(get_current(city))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("Realtime current failed")
        return jsonify({"error": "Internal server error"}), 500


@realtime_bp.route("/realtime/next", methods=["POST"])
def realtime_next():
    payload: Any = request.get_json(silent=True) or {}
    city = payload.get("city", "Delhi")
    try:
        return jsonify(step_forward(city))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("Realtime next failed")
        return jsonify({"error": "Internal server error"}), 500


@realtime_bp.route("/realtime/forecast", methods=["GET"])
def realtime_forecast():
    city = request.args.get("city", "Delhi")
    try:
        return jsonify(get_forecast_48h(city))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("Realtime forecast failed")
        return jsonify({"error": "Internal server error"}), 500


@realtime_bp.route("/realtime/comparison", methods=["GET"])
def realtime_comparison():
    try:
        return jsonify(get_city_comparison())
    except Exception:
        logger.exception("Realtime comparison failed")
        return jsonify({"error": "Internal server error"}), 500
