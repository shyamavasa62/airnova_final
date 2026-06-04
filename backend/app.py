import os
import sys
from typing import Optional

from flask import Flask, Response, request

# Ensure imports work when running:
# - `python3 backend/app.py` (project root not automatically on PYTHONPATH)
# - `python3 -m backend.app`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config.settings import settings
from backend.routes.arima import arima_bp
from backend.routes.admin import admin_bp
from backend.routes.forecast import forecast_bp
from backend.routes.health import health_bp
from backend.routes.predict import predict_bp
from backend.routes.realtime import realtime_bp


def create_app() -> Flask:
    app = Flask(__name__)

    @app.before_request
    def handle_preflight() -> Optional[Response]:
        if request.method == "OPTIONS":
            resp = app.make_default_options_response()
            return _with_cors_headers(resp)
        return None

    @app.after_request
    def add_cors_headers(resp: Response) -> Response:
        return _with_cors_headers(resp)

    @app.route("/")
    def home() -> str:
        return "AirNova API is running!"

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(predict_bp)
    app.register_blueprint(forecast_bp)
    app.register_blueprint(arima_bp)
    app.register_blueprint(realtime_bp)
    app.register_blueprint(admin_bp)

    return app


def _with_cors_headers(resp: Response) -> Response:
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp


app = create_app()


if __name__ == "__main__":
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)