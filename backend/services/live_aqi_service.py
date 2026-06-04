from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import urlopen


# Keep only AIRNOVA dataset cities (no new names).
CITY_COORDS: Dict[str, Dict[str, float]] = {
    "bangalore": {"lat": 12.9716, "lon": 77.5946},
    "chennai": {"lat": 13.0827, "lon": 80.2707},
    "delhi": {"lat": 28.6139, "lon": 77.2090},
    "hyderabad": {"lat": 17.3850, "lon": 78.4867},
    "mumbai": {"lat": 19.0760, "lon": 72.8777},
}


def _to_ppb(ug_m3: float, mw: float) -> float:
    # ppb = ug/m3 * 24.45 / molecular_weight
    return (float(ug_m3) * 24.45) / float(mw)


def _co_ugm3_to_ppm(ug_m3: float) -> float:
    # ppm = (ug/m3 / 1000) * (24.45 / 28.01)
    return (float(ug_m3) / 1000.0) * (24.45 / 28.01)


def _fetch_json(url: str) -> Dict[str, Any]:
    with urlopen(url, timeout=6) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def get_live_air_quality(city: str) -> Optional[Dict[str, Any]]:
    key = city.strip().lower()
    if key not in CITY_COORDS:
        return None

    coords = CITY_COORDS[key]
    query = urlencode(
        {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "current": "us_aqi,pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,ozone,carbon_monoxide",
            "timezone": "auto",
        }
    )
    url = f"https://air-quality-api.open-meteo.com/v1/air-quality?{query}"

    try:
        data = _fetch_json(url)
        current = data.get("current", {})
        if not current:
            return None

        pm25 = float(current.get("pm2_5"))
        pm10 = float(current.get("pm10"))
        no2_ppb = _to_ppb(float(current.get("nitrogen_dioxide")), 46.0055)
        so2_ppb = _to_ppb(float(current.get("sulphur_dioxide")), 64.066)
        o3_ppb = _to_ppb(float(current.get("ozone")), 48.0)
        co_ppm = _co_ugm3_to_ppm(float(current.get("carbon_monoxide")))
        live_aqi = float(current.get("us_aqi"))

        return {
            "timestamp": current.get("time"),
            "live_aqi": live_aqi,
            "pollutants_model_units": {
                "PM2.5": pm25,
                "PM10": pm10,
                "NO2": no2_ppb,
                "SO2": so2_ppb,
                "CO": co_ppm,
                "O3": o3_ppb,
            },
            "source": "open-meteo",
        }
    except Exception:
        return None


def get_live_48h_aqi(city: str) -> List[Dict[str, Any]]:
    key = city.strip().lower()
    if key not in CITY_COORDS:
        return []

    coords = CITY_COORDS[key]
    query = urlencode(
        {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "hourly": "us_aqi",
            "forecast_days": 3,
            "timezone": "auto",
        }
    )
    url = f"https://air-quality-api.open-meteo.com/v1/air-quality?{query}"

    try:
        data = _fetch_json(url)
        hourly = data.get("hourly", {})
        times = hourly.get("time", []) or []
        aqi_values = hourly.get("us_aqi", []) or []
        if not times or not aqi_values:
            return []

        now = datetime.now()
        points: List[Dict[str, Any]] = []
        for t, aqi in zip(times, aqi_values):
            dt = datetime.fromisoformat(str(t))
            if dt <= now:
                continue
            points.append({"timestamp": dt.isoformat(), "live_aqi": float(aqi)})
            if len(points) >= 48:
                break

        # Sample each 3rd hour to match AIRNOVA 16-point forecast.
        sampled = points[::3][:16]
        with_horizon = []
        for i, p in enumerate(sampled):
            with_horizon.append(
                {
                    "horizon_hour": int((i + 1) * 3),
                    "timestamp": p["timestamp"],
                    "live_aqi": p["live_aqi"],
                }
            )
        return with_horizon
    except Exception:
        return []


def get_live_weather(city: str) -> Optional[Dict[str, Any]]:
    key = city.strip().lower()
    if key not in CITY_COORDS:
        return None

    coords = CITY_COORDS[key]
    query = urlencode(
        {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
            "timezone": "auto",
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{query}"

    try:
        data = _fetch_json(url)
        current = data.get("current", {})
        if not current:
            return None
        return {
            "timestamp": current.get("time"),
            "temperature_c": round(float(current.get("temperature_2m")), 2),
            "humidity_pct": round(float(current.get("relative_humidity_2m")), 2),
            "wind_speed_kmh": round(float(current.get("wind_speed_10m")), 2),
            "source": "open-meteo",
        }
    except Exception:
        return None
