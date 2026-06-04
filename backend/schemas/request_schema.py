from typing import Any, Dict

from backend.services.preprocessing_service import POLLUTANT_FIELDS
from backend.utils.helpers import require_keys


def validate_predict_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    require_keys(payload, POLLUTANT_FIELDS)

    has_date = "date" in payload and payload["date"] not in (None, "")
    if not has_date:
        require_keys(payload, ("day", "month", "weekend"))
    return payload


def validate_forecast_payload(payload: Any) -> Dict[str, Any]:
    """
    Forecast payload format:
    {
      "inputs": [ <predict_payload>, <predict_payload>, ... ]
    }
    """
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    if "inputs" not in payload or not isinstance(payload["inputs"], list):
        raise ValueError("Field 'inputs' must be an array of predict payloads.")

    for item in payload["inputs"]:
        validate_predict_payload(item)

    return payload


def validate_arima_forecast_payload(payload: Any) -> Dict[str, Any]:
    """
    ARIMA payload format:
    {
      "aqi_history": [92.1, 95.4, 88.0, ...],
      "steps": 5  # optional, default 1
    }
    """
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    if "aqi_history" not in payload or not isinstance(payload["aqi_history"], list):
        raise ValueError("Field 'aqi_history' must be an array of numeric AQI values.")

    if len(payload["aqi_history"]) < 10:
        raise ValueError("Field 'aqi_history' must include at least 10 values.")

    if "steps" in payload:
        try:
            steps = int(payload["steps"])
        except Exception as e:
            raise ValueError("Field 'steps' must be an integer.") from e
        if steps < 1 or steps > 30:
            raise ValueError("Field 'steps' must be an integer between 1 and 30.")

    return payload
