from typing import Any, Dict, List

import numpy as np

from backend.models.model_loader import load_model
from backend.services.preprocessing_service import build_features


def predict_aqi(request_data: Dict[str, Any]) -> float:
    """
    Predict a single AQI value from one request payload.

    Expected feature vector order is handled by `build_features()`.
    """
    model = load_model()
    features: List[float] = build_features(request_data)

    # RandomForestRegressor expects 2D input.
    pred = model.predict(np.array([features], dtype=float))[0]
    return round(float(pred), 2)
