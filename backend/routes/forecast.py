from typing import Any, Dict, List

from flask import Blueprint, jsonify, request

from backend.schemas.request_schema import validate_forecast_payload
from backend.schemas.response_schema import make_predict_response
from backend.services.prediction_service import predict_aqi
from backend.utils.logger import logger


forecast_bp = Blueprint("forecast_bp", __name__)


@forecast_bp.route("/forecast", methods=["POST"])
def forecast():
    payload: Any = request.get_json(silent=True)

    try:
        validate_forecast_payload(payload)
        inputs: List[Dict[str, Any]] = payload["inputs"]

        predictions = [make_predict_response(predict_aqi(item)) for item in inputs]
        return jsonify({"predictions": predictions})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("Forecast failed")
        return jsonify({"error": "Internal server error"}), 500
