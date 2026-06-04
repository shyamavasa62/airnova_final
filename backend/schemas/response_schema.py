from typing import Any, Dict

from backend.services.aqi_calculator import get_alert, get_aqi_status


def make_predict_response(predicted_aqi: float) -> Dict[str, Any]:
    """
    Response format returned by /predict (and reused by /forecast).
    """
    predicted_aqi = float(predicted_aqi)
    status = get_aqi_status(predicted_aqi)
    alert = get_alert(predicted_aqi)
    return {
        "predicted_aqi": predicted_aqi,
        "status": status,
        "alert": alert,
    }
