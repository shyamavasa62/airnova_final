from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

from backend.config.settings import settings
from backend.services.arima_service import forecast_aqi_arima
from backend.services.live_aqi_service import (
    get_live_48h_aqi,
    get_live_air_quality,
    get_live_weather,
)
from backend.services.prediction_service import predict_aqi


@dataclass
class _RealtimeState:
    cursor: int = 0


_STATE = _RealtimeState()
_DF: Optional[pd.DataFrame] = None


def _load_df() -> pd.DataFrame:
    global _DF
    if _DF is not None:
        return _DF

    # Prefer admin-ingested DB data when present.
    try:
        from ml.src.data_source import load_effective_dataset

        df = load_effective_dataset()
    except Exception:
        df = pd.read_csv(settings.DATASET_PATH)
    df = df.dropna(
        subset=["City", "Date", "AQI", "PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]
    )
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date"])
    df["AQI"] = pd.to_numeric(df["AQI"], errors="coerce")
    for c in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["AQI", "PM2.5", "PM10", "NO2", "SO2", "CO", "O3"])
    df = df.sort_values(["City", "Date"]).reset_index(drop=True)
    _DF = df
    return _DF


def list_cities() -> List[str]:
    df = _load_df()
    cleaned = (
        df["City"]
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
    )
    # Guard against accidental header-like rows in CSV data.
    cleaned = cleaned[cleaned.str.lower() != "city"]
    return sorted(cleaned.unique().tolist())


def _city_df(city: str) -> pd.DataFrame:
    df = _load_df()
    cdf = df[df["City"].astype(str).str.lower() == city.lower()].reset_index(drop=True)
    if cdf.empty:
        raise ValueError(f"Unknown city '{city}'.")
    return cdf


def get_current(city: str) -> Dict[str, Any]:
    cdf = _city_df(city)
    idx = _STATE.cursor % len(cdf)
    row = cdf.iloc[idx]

    payload = {
        "day": int(row["Date"].day),
        "month": int(row["Date"].month),
        "weekend": 1 if int(row["Date"].weekday()) >= 5 else 0,
        "PM2.5": float(row["PM2.5"]),
        "PM10": float(row["PM10"]),
        "NO2": float(row["NO2"]),
        "SO2": float(row["SO2"]),
        "CO": float(row["CO"]),
        "O3": float(row["O3"]),
    }
    live = get_live_air_quality(str(row["City"]))
    weather = get_live_weather(str(row["City"]))
    if live is not None:
        payload.update(live["pollutants_model_units"])
    rf_next: Optional[float] = None
    try:
        rf_next = float(predict_aqi(payload))
    except Exception:
        rf_next = None

    hist = cdf.iloc[max(0, idx - 60) : idx + 1]["AQI"].astype(float).tolist()
    arima_next: Optional[float] = None
    if len(hist) >= 10:
        try:
            arima_next = float(forecast_aqi_arima(hist, steps=1)["predictions"][0])
        except Exception:
            arima_next = None

    actual_aqi = float(row["AQI"])
    source = "historical_dataset"
    if live is not None:
        actual_aqi = float(live["live_aqi"])
        source = "live_api"

    prev_idx = (idx - 1) % len(cdf)
    prev_aqi = float(cdf.iloc[prev_idx]["AQI"])
    delta = actual_aqi - prev_aqi
    delta_pct = (delta / prev_aqi * 100.0) if prev_aqi else 0.0
    trend_label = "Improving Air Quality" if delta < 0 else "Air Quality Worsening" if delta > 0 else "Stable Air Quality"
    health_icon = "😊" if actual_aqi <= 100 else "😷" if actual_aqi <= 200 else "⚠️"

    return {
        "city": str(row["City"]),
        "date": datetime.now().date().isoformat() if live is not None else str(row["Date"].date()),
        "cursor": int(idx),
        "actual_aqi": round(actual_aqi, 2),
        "last_updated": (live or {}).get("timestamp") or datetime.now().isoformat(),
        "pollutants": {
            "PM2.5": round(float(payload["PM2.5"]), 2),
            "PM10": round(float(payload["PM10"]), 2),
            "NO2": round(float(payload["NO2"]), 2),
            "SO2": round(float(payload["SO2"]), 2),
            "CO": round(float(payload["CO"]), 2),
            "O3": round(float(payload["O3"]), 2),
        },
        "weather": weather,
        "trend": {
            "delta_aqi": round(delta, 2),
            "delta_pct": round(delta_pct, 2),
            "label": trend_label,
        },
        "health_indicator": health_icon,
        "data_source": source,
        "predictions": {
            "rf_next_aqi": round(float(rf_next), 2) if rf_next is not None else None,
            "arima_next_aqi": round(float(arima_next), 2) if arima_next is not None else None,
        },
    }


def _aqi_band(aqi: float) -> str:
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Sensitive"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def get_forecast_48h(city: str) -> Dict[str, Any]:
    cdf = _city_df(city)
    idx = _STATE.cursor % len(cdf)
    row = cdf.iloc[idx]

    steps = 16
    interval_hours = 3
    hist = cdf.iloc[max(0, idx - 120) : idx + 1]["AQI"].astype(float).tolist()

    arima_preds: List[float] = []
    if len(hist) >= 10:
        try:
            result = forecast_aqi_arima(hist, steps=steps)
            arima_preds = [float(v) for v in result["predictions"]]
        except Exception:
            arima_preds = []

    live_now = get_live_air_quality(str(row["City"]))
    live_series = get_live_48h_aqi(str(row["City"]))

    rf_preds: List[float] = []
    pm25 = float(row["PM2.5"])
    pm10 = float(row["PM10"])
    no2 = float(row["NO2"])
    so2 = float(row["SO2"])
    co = float(row["CO"])
    o3 = float(row["O3"])
    if live_now is not None:
        p = live_now["pollutants_model_units"]
        pm25 = float(p["PM2.5"])
        pm10 = float(p["PM10"])
        no2 = float(p["NO2"])
        so2 = float(p["SO2"])
        co = float(p["CO"])
        o3 = float(p["O3"])

    for i in range(steps):
        drift = 1 + (i * 0.01)
        payload = {
            "day": int(row["Date"].day),
            "month": int(row["Date"].month),
            "weekend": 1 if int(row["Date"].weekday()) >= 5 else 0,
            "PM2.5": pm25 * drift,
            "PM10": pm10 * drift,
            "NO2": no2 * drift,
            "SO2": so2 * drift,
            "CO": co * drift,
            "O3": o3 * drift,
        }
        try:
            rf_preds.append(float(predict_aqi(payload)))
        except Exception:
            break

    best_available = arima_preds if arima_preds else rf_preds
    if not best_available:
        raise ValueError("Unable to build forecast from current model state.")

    base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    points: List[Dict[str, Any]] = []
    for i in range(steps):
        ts = base_time + timedelta(hours=(i + 1) * interval_hours)
        arima_v = arima_preds[i] if i < len(arima_preds) else None
        rf_v = rf_preds[i] if i < len(rf_preds) else None
        live_v = live_series[i]["live_aqi"] if i < len(live_series) else None
        ml_v = arima_v if arima_v is not None else rf_v
        if ml_v is None and live_v is None:
            continue
        final_v = ((float(ml_v) + float(live_v)) / 2.0) if (ml_v is not None and live_v is not None) else float(
            ml_v if ml_v is not None else live_v
        )
        points.append(
            {
                "horizon_hour": int((i + 1) * interval_hours),
                "timestamp": ts.isoformat(),
                "predicted_aqi": round(float(final_v), 2),
                "status": _aqi_band(float(final_v)),
                "live_predicted_aqi": round(float(live_v), 2) if live_v is not None else None,
                "ml_predicted_aqi": round(float(ml_v), 2) if ml_v is not None else None,
                "rf_predicted_aqi": round(float(rf_v), 2) if rf_v is not None else None,
                "arima_predicted_aqi": round(float(arima_v), 2) if arima_v is not None else None,
            }
        )

    return {
        "city": str(row["City"]),
        "based_on_record_date": str(row["Date"].date()),
        "cursor": int(idx),
        "window_hours": 48,
        "interval_hours": interval_hours,
        "generated_at": datetime.now().isoformat(),
        "points": points,
        "note": "Hybrid forecast combining live AQI API feed with AIRNOVA ML projections.",
    }


def step_forward(city: str) -> Dict[str, Any]:
    cdf = _city_df(city)
    _STATE.cursor = (_STATE.cursor + 1) % len(cdf)
    return get_current(city)


def get_city_comparison() -> Dict[str, Any]:
    cities = list_cities()
    cards: List[Dict[str, Any]] = []
    for city in cities:
        try:
            rec = get_current(city)
            cards.append(
                {
                    "city": city,
                    "aqi": rec["actual_aqi"],
                    "status": _aqi_band(float(rec["actual_aqi"])),
                    "data_source": rec.get("data_source", "historical_dataset"),
                }
            )
        except Exception:
            continue
    cards.sort(key=lambda x: float(x["aqi"]), reverse=True)
    return {"cities": cards}
