from __future__ import annotations

import os
import tempfile
from typing import Optional

import pandas as pd

from backend.config.settings import settings
from backend.db import fetch_all_as_rows, get_stats


def load_effective_dataset() -> pd.DataFrame:
    """
    Preferred dataset source:
    - if DB has rows: return DB records as a dataframe with original CSV-like columns
    - else: fall back to settings.DATASET_PATH
    """
    stats = get_stats()
    if stats.n_rows > 0:
        rows = fetch_all_as_rows()
        df = pd.DataFrame(
            [
                {
                    "City": r["city"],
                    "Date": r["date"],
                    "AQI": r["aqi"],
                    "PM2.5": r["pm25"],
                    "PM10": r["pm10"],
                    "NO2": r["no2"],
                    "SO2": r["so2"],
                    "CO": r["co"],
                    "O3": r["o3"],
                }
                for r in rows
            ]
        )
        return df

    return pd.read_csv(settings.DATASET_PATH)


def export_effective_dataset_csv(out_path: Optional[str] = None) -> str:
    """
    Exports the effective dataset to a CSV path and returns that path.
    Useful because some training scripts assume a CSV path.
    """
    df = load_effective_dataset()
    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        df.to_csv(out_path, index=False)
        return out_path

    fd, path = tempfile.mkstemp(prefix="airnova_dataset_", suffix=".csv")
    os.close(fd)
    df.to_csv(path, index=False)
    return path

