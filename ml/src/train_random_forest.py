from __future__ import annotations

import os
import pickle
from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from backend.config.settings import settings
from ml.src.data_source import load_effective_dataset


@dataclass(frozen=True)
class RfTrainConfig:
    test_size: float = 0.2
    random_state: int = 42
    n_estimators: int = 150


def _build_xy(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    df = df.dropna(subset=["Date", "AQI", "PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]).copy()
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date"])

    df["day"] = df["Date"].dt.day
    df["month"] = df["Date"].dt.month
    df["weekend"] = (df["Date"].dt.weekday >= 5).astype(int)

    df["AQI"] = pd.to_numeric(df["AQI"], errors="coerce")
    for c in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["AQI_future"] = df["AQI"].shift(-1)
    df = df.dropna(subset=["AQI_future", "AQI", "PM2.5", "PM10", "NO2", "SO2", "CO", "O3"])

    X = df[["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "day", "month", "weekend"]]
    y = df["AQI_future"].astype(float)
    if len(X) < 30:
        raise ValueError("Not enough rows to train RandomForest (need >= 30 after feature engineering).")
    return X, y


def train_random_forest(cfg: RfTrainConfig = RfTrainConfig()) -> Dict[str, object]:
    df = load_effective_dataset()
    X, y = _build_xy(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=cfg.test_size,
        random_state=cfg.random_state,
    )

    model = RandomForestRegressor(
        n_estimators=cfg.n_estimators,
        random_state=cfg.random_state,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, preds))
    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    r2 = float(r2_score(y_test, preds))

    os.makedirs(os.path.dirname(settings.MODEL_PATH), exist_ok=True)
    with open(settings.MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    return {
        "model_type": "random_forest",
        "model_out": settings.MODEL_PATH,
        "n_rows": int(len(X)),
        "test_size": float(cfg.test_size),
        "metrics": {"mae": mae, "rmse": rmse, "r2": r2},
    }


def main() -> None:
    res = train_random_forest()
    print(res)


if __name__ == "__main__":
    main()

