import os


def _project_root() -> str:
    # backend/config/settings.py -> project root is two levels up
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


PROJECT_ROOT = _project_root()


class Settings:
    # Flask
    DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes", "y", "on")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5000"))

    # Model
    MODEL_PATH = os.getenv(
        "MODEL_PATH",
        os.path.join(PROJECT_ROOT, "ml", "models", "aqi_model.pkl"),
    )

    ARIMA_MODEL_PATH = os.getenv(
        "ARIMA_MODEL_PATH",
        os.path.join(PROJECT_ROOT, "ml", "models", "arima_model.pkl"),
    )

    DATASET_PATH = os.getenv(
        "DATASET_PATH",
        os.path.join(PROJECT_ROOT, "data", "raw", "aqi_dataset.csv"),
    )

    # Database (SQLite)
    DB_PATH = os.getenv(
        "DB_PATH",
        os.path.join(PROJECT_ROOT, "data", "airnova.sqlite3"),
    )

    # AQI classification thresholds
    AQI_STATUS_THRESHOLDS = [
        (50, "Good"),
        (100, "Moderate"),
        (200, "Poor"),
        (300, "Very Poor"),
        (float("inf"), "Severe"),
    ]

    ALERT_THRESHOLD = 200


settings = Settings()
