from backend.config.settings import settings


def get_aqi_status(aqi: float) -> str:
    """
    Convert a numeric AQI value into a human-readable category.
    """
    aqi = float(aqi)
    for threshold, label in settings.AQI_STATUS_THRESHOLDS:
        if aqi <= threshold:
            return label
    # Should be unreachable because we end with inf
    return "Severe"


def get_alert(aqi: float) -> str:
    """
    Simple alert message used by the UI.
    """
    aqi = float(aqi)
    if aqi > settings.ALERT_THRESHOLD:
        return "High Pollution Alert!"
    return "Air Quality is Acceptable"
