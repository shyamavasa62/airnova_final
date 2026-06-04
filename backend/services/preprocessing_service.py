from typing import Any, Dict, List

from backend.utils.helpers import (
    coerce_float,
    coerce_weekend,
    parse_date_to_features,
    require_keys,
)


POLLUTANT_FIELDS = ("PM2.5", "PM10", "NO2", "SO2", "CO", "O3")


def build_features(data: Dict[str, Any]) -> List[float]:
    """
    Build the model feature vector in the expected order:
    [PM2.5, PM10, NO2, SO2, CO, O3, day, month, weekend]
    """
    # Pollutants are always required.
    require_keys(data, POLLUTANT_FIELDS)

    day: int
    month: int
    weekend: int

    if "date" in data and data["date"] not in (None, ""):
        day, month, weekend = parse_date_to_features(str(data["date"]))
    else:
        require_keys(data, ("day", "month", "weekend"))
        try:
            day = int(float(data["day"]))
            month = int(float(data["month"]))
        except Exception as e:
            raise ValueError("Fields 'day' and 'month' must be numeric.") from e
        weekend = coerce_weekend(data["weekend"])

    features = [
        coerce_float(data["PM2.5"], "PM2.5"),
        coerce_float(data["PM10"], "PM10"),
        coerce_float(data["NO2"], "NO2"),
        coerce_float(data["SO2"], "SO2"),
        coerce_float(data["CO"], "CO"),
        coerce_float(data["O3"], "O3"),
        float(day),
        float(month),
        float(weekend),
    ]
    return features
