from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
from statsmodels.tsa.arima.model import ARIMA

from backend.models.arima_loader import get_arima_order, load_arima_artifact


def forecast_aqi_arima(aqi_history: List[Any], steps: int = 1) -> Dict[str, Any]:
    """
    Forecast future AQI values using an ARIMA(p,d,q) order stored in the trained artifact.

    This endpoint expects an AQI time series (most recent last). It does NOT use pollutant inputs.
    """
    if not isinstance(aqi_history, list) or len(aqi_history) < 10:
        raise ValueError("Field 'aqi_history' must be an array with at least 10 values.")

    try:
        y = np.asarray([float(x) for x in aqi_history], dtype=float)
    except Exception as e:
        raise ValueError("All values in 'aqi_history' must be numeric.") from e

    if not np.all(np.isfinite(y)):
        raise ValueError("All values in 'aqi_history' must be finite numbers.")

    if not isinstance(steps, int) or steps < 1 or steps > 30:
        raise ValueError("Field 'steps' must be an integer between 1 and 30.")

    artifact = load_arima_artifact()
    order = get_arima_order(artifact)

    fitted = ARIMA(y, order=order, enforce_stationarity=False, enforce_invertibility=False).fit()
    preds = fitted.forecast(steps=steps)
    preds_list = [round(float(v), 2) for v in list(preds)]

    return {"model": "arima", "order": order, "steps": steps, "predictions": preds_list}

