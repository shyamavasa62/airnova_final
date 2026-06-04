from __future__ import annotations

import io
import threading
from typing import Any, Dict, Optional

import pandas as pd
from flask import Blueprint, jsonify, request

from backend.db import get_stats, insert_many, replace_all
from backend.models.model_loader import clear_model_cache
from backend.utils.logger import logger
from ml.src.train_arima import ArimaTrainConfig, train_arima
from ml.src.train_random_forest import RfTrainConfig, train_random_forest

admin_bp = Blueprint("admin_bp", __name__)


_REQUIRED_COLS = ["City", "Date", "AQI", "PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]


def _normalize_records(df: pd.DataFrame):
    df = df.dropna(subset=_REQUIRED_COLS).copy()
    df["City"] = df["City"].astype(str).str.strip()
    df = df[df["City"] != ""]

    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date"])
    df["Date"] = df["Date"].dt.date.astype(str)  # ISO yyyy-mm-dd

    df["AQI"] = pd.to_numeric(df["AQI"], errors="coerce")
    for c in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["AQI", "PM2.5", "PM10", "NO2", "SO2", "CO", "O3"])

    records = []
    for _, row in df.iterrows():
        records.append(
            (
                str(row["City"]),
                str(row["Date"]),
                float(row["AQI"]),
                float(row["PM2.5"]),
                float(row["PM10"]),
                float(row["NO2"]),
                float(row["SO2"]),
                float(row["CO"]),
                float(row["O3"]),
            )
        )
    return records


@admin_bp.route("/admin/stats", methods=["GET"])
def admin_stats():
    try:
        stats = get_stats()
        return jsonify({"db_rows": stats.n_rows})
    except Exception:
        logger.exception("Admin stats failed")
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route("/admin/ingest", methods=["POST"])
def admin_ingest():
    """
    Ingest admin-provided dataset into DB.

    Accepts multipart form:
      - file: CSV file
      - mode: 'append' (default) or 'replace'
    """
    try:
        mode = (request.form.get("mode") or "append").strip().lower()
        f = request.files.get("file")
        if f is None:
            return jsonify({"error": "Missing multipart file field 'file'."}), 400

        raw = f.read()
        df = pd.read_csv(io.BytesIO(raw))

        missing = [c for c in _REQUIRED_COLS if c not in df.columns]
        if missing:
            return (
                jsonify(
                    {
                        "error": "CSV missing required columns.",
                        "missing": missing,
                        "required": _REQUIRED_COLS,
                    }
                ),
                400,
            )

        records = _normalize_records(df)
        if not records:
            return jsonify({"error": "No valid rows found after validation."}), 400

        if mode == "replace":
            n = replace_all(records)
        elif mode == "append":
            n = insert_many(records)
        else:
            return jsonify({"error": "Invalid mode. Use 'append' or 'replace'."}), 400

        stats = get_stats()
        return jsonify({"inserted": int(n), "db_rows": int(stats.n_rows), "mode": mode})
    except Exception:
        logger.exception("Admin ingest failed")
        return jsonify({"error": "Internal server error"}), 500


_TRAIN_STATE: Dict[str, Any] = {"running": False, "last_result": None, "last_error": None}


def _train_job(raw_path: str) -> None:
    try:
        _TRAIN_STATE["running"] = True
        _TRAIN_STATE["last_error"] = None
        rf_res = train_random_forest(RfTrainConfig())
        clear_model_cache()

        arima_cfg = ArimaTrainConfig(raw_path=raw_path)
        arima_res = train_arima(arima_cfg)
        _TRAIN_STATE["last_result"] = {"random_forest": rf_res, "arima": arima_res}
    except Exception as e:
        logger.exception("Retrain failed")
        _TRAIN_STATE["last_error"] = str(e)
        _TRAIN_STATE["last_result"] = None
    finally:
        _TRAIN_STATE["running"] = False


@admin_bp.route("/admin/retrain", methods=["POST"])
def admin_retrain():
    """
    Triggers a lightweight retrain (ARIMA) on the current dataset source.
    If DB has data, it is exported to a temporary CSV and used as training input.
    """
    try:
        if _TRAIN_STATE.get("running"):
            return jsonify({"status": "running"}), 202

        # Training scripts expect a CSV path. We'll write a temp CSV derived from the
        # current effective dataset (DB preferred) in the ML data loader.
        from ml.src.data_source import export_effective_dataset_csv

        raw_path = export_effective_dataset_csv()
        t = threading.Thread(target=_train_job, args=(raw_path,), daemon=True)
        t.start()
        return jsonify({"status": "started"}), 202
    except Exception:
        logger.exception("Retrain trigger failed")
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route("/admin/retrain/status", methods=["GET"])
def admin_retrain_status():
    try:
        return jsonify(
            {
                "running": bool(_TRAIN_STATE.get("running")),
                "last_result": _TRAIN_STATE.get("last_result"),
                "last_error": _TRAIN_STATE.get("last_error"),
            }
        )
    except Exception:
        logger.exception("Retrain status failed")
        return jsonify({"error": "Internal server error"}), 500

