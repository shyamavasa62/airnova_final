from typing import Any, Dict

from flask import Blueprint, jsonify, request

from backend.schemas.request_schema import validate_predict_payload
from backend.schemas.response_schema import make_predict_response
from backend.services.prediction_service import predict_aqi
from backend.utils.logger import logger


predict_bp = Blueprint("predict_bp", __name__)


@predict_bp.route("/predict", methods=["POST", "GET"])
def predict():
    # If someone hits this via browser (GET), return a helpful payload and an example prediction.
    if request.method == "GET":
        example_payload: Dict[str, Any] = {
            "day": 8,
            "month": 4,
            "weekend": 1,
            "PM2.5": 12.3,
            "PM10": 20.1,
            "NO2": 30.0,
            "SO2": 5.2,
            "CO": 0.7,
            "O3": 40.6,
        }
        try:
            predicted = predict_aqi(example_payload)
            resp = make_predict_response(predicted)
        except Exception:
            # Still return a helpful response if model loading/prediction fails for any reason.
            resp = None
        return jsonify(
            {
                "hint": "Use POST /predict with a JSON body. Example provided in `example_payload`.",
                "example_payload": example_payload,
                "example_response": resp,
            }
        )

    payload: Any = request.get_json(silent=True)

    try:
        validate_predict_payload(payload)
        predicted = predict_aqi(payload)
        return jsonify(make_predict_response(predicted))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("Prediction failed")
        return jsonify({"error": "Internal server error"}), 500
