"""
Flask blueprints for backend routes.
"""

from backend.routes.arima import arima_bp
from backend.routes.forecast import forecast_bp
from backend.routes.health import health_bp
from backend.routes.predict import predict_bp
from backend.routes.realtime import realtime_bp

__all__ = ["health_bp", "predict_bp", "forecast_bp", "arima_bp", "realtime_bp"]

