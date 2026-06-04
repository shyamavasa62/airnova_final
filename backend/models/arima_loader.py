import os
import pickle
from typing import Any, Dict, Optional, Tuple

from backend.config.settings import settings
from backend.utils.logger import logger

_ARIMA_ARTIFACT: Optional[Dict[str, Any]] = None


def load_arima_artifact(force_reload: bool = False) -> Dict[str, Any]:
    global _ARIMA_ARTIFACT
    if _ARIMA_ARTIFACT is not None and not force_reload:
        return _ARIMA_ARTIFACT

    model_path = settings.ARIMA_MODEL_PATH
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"ARIMA model file not found at '{model_path}'. "
            f"Set ARIMA_MODEL_PATH env var to override."
        )

    logger.info("Loading ARIMA artifact from %s", model_path)
    with open(model_path, "rb") as f:
        artifact = pickle.load(f)

    if not isinstance(artifact, dict) or "order" not in artifact:
        raise ValueError("Invalid ARIMA artifact format (expected a dict with 'order').")

    _ARIMA_ARTIFACT = artifact
    return artifact


def get_arima_order(artifact: Dict[str, Any]) -> Tuple[int, int, int]:
    order = artifact.get("order")
    if (
        not isinstance(order, tuple)
        or len(order) != 3
        or not all(isinstance(x, int) for x in order)
    ):
        raise ValueError("Invalid ARIMA 'order' in artifact.")
    return order  # type: ignore[return-value]

