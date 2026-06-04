import os
import pickle
from typing import Any, Optional

from backend.config.settings import settings
from backend.utils.logger import logger

_MODEL: Optional[Any] = None


def clear_model_cache() -> None:
    global _MODEL
    _MODEL = None


def load_model(force_reload: bool = False) -> Any:
    """
    Load and cache the trained AQI model.
    """
    global _MODEL
    if _MODEL is not None and not force_reload:
        return _MODEL

    model_path = settings.MODEL_PATH
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model file not found at '{model_path}'. "
            f"Set MODEL_PATH env var to override."
        )

    logger.info("Loading model from %s", model_path)
    with open(model_path, "rb") as f:
        _MODEL = pickle.load(f)
    return _MODEL
