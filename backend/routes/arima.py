from typing import Any

from flask import Blueprint, jsonify, request

from backend.schemas.request_schema import validate_arima_forecast_payload
from backend.services.arima_service import forecast_aqi_arima
from backend.utils.logger import logger

arima_bp = Blueprint("arima_bp", __name__)


@arima_bp.route("/arima/forecast", methods=["POST"])
def arima_forecast():
    payload: Any = request.get_json(silent=True)

    try:
        validate_arima_forecast_payload(payload)
        aqi_history = payload.get("aqi_history")
        steps = payload.get("steps", 1)
        result = forecast_aqi_arima(aqi_history, steps=int(steps))
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("ARIMA forecast failed")
        return jsonify({"error": "Internal server error"}), 500

