import math
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


def coerce_float(value: Any, field_name: str) -> float:
    """
    Convert a JSON value into float, raising a ValueError with context when invalid.
    """
    try:
        # Reject NaN/inf to avoid silent model weirdness.
        f = float(value)
    except Exception as e:
        raise ValueError(f"Field '{field_name}' must be numeric.") from e

    if math.isnan(f) or math.isinf(f):
        raise ValueError(f"Field '{field_name}' must be a finite number.")
    return f


def coerce_weekend(value: Any) -> int:
    """
    Accept boolean, 0/1, or "true"/"false" and return 0 or 1.
    """
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)) and float(value) in (0.0, 1.0):
        return int(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "1", "yes", "y", "on"):
            return 1
        if v in ("false", "0", "no", "n", "off"):
            return 0
    raise ValueError("Field 'weekend' must be 0/1 or true/false.")


def parse_date_to_features(date_str: str) -> Tuple[int, int, int]:
    """
    Parse YYYY-MM-DD (or YYYY/MM/DD) into (day, month, weekend).
    weekend is 1 when weekday is Sat/Sun.
    """
    date_str = (date_str or "").strip()
    if not date_str:
        raise ValueError("Field 'date' must be provided.")

    dt: Optional[datetime] = None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%d-%m", "%Y.%m.%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue

    if dt is None:
        # datetime.fromisoformat handles some ISO variants
        try:
            dt = datetime.fromisoformat(date_str)
        except Exception as e:
            raise ValueError(
                "Field 'date' must be in YYYY-MM-DD (or similar) format."
            ) from e

    day = int(dt.day)
    month = int(dt.month)
    weekend = 1 if dt.weekday() >= 5 else 0
    return day, month, weekend


def require_keys(data: Dict[str, Any], keys: Tuple[str, ...]) -> None:
    missing = [k for k in keys if k not in data]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
