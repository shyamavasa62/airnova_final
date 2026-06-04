from __future__ import annotations

import argparse
import pickle
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX


def _load_aqi_series(raw_path: str) -> pd.Series:
    df = pd.read_csv(raw_path)
    df = df.dropna(subset=["Date", "AQI"])
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date"])
    df = df.sort_values("Date")
    df["AQI"] = pd.to_numeric(df["AQI"], errors="coerce")
    df = df.dropna(subset=["AQI"])
    daily = df.groupby(df["Date"].dt.date)["AQI"].mean()
    daily.index = pd.to_datetime(daily.index)
    daily = daily.asfreq("D").interpolate(limit_direction="both")
    return daily.astype(float).replace([np.inf, -np.inf], np.nan).dropna()


def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float))))


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    err = np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean(err**2)))


def evaluate_sarima(
    model_path: str,
    raw_path: str = "data/raw/aqi_dataset.csv",
    holdout_ratio: float = 0.2,
) -> Dict[str, object]:
    with open(model_path, "rb") as f:
        artifact = pickle.load(f)

    if not isinstance(artifact, dict) or "order" not in artifact or "seasonal_order" not in artifact:
        raise ValueError("Invalid SARIMA artifact format.")

    order = tuple(artifact["order"])
    seasonal_order = tuple(artifact["seasonal_order"])

    series = _load_aqi_series(raw_path)
    n = len(series)
    holdout_n = max(1, int(round(n * holdout_ratio)))
    train = series.iloc[: n - holdout_n]
    valid = series.iloc[n - holdout_n :]

    history = train.copy()
    preds = []
    for i in range(len(valid)):
        fit = SARIMAX(
            history,
            order=order,
            seasonal_order=seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False)
        yhat = float(fit.forecast(steps=1).iloc[0])
        preds.append(yhat)
        history = pd.concat([history, valid.iloc[i : i + 1]])

    y_true = valid.values.astype(float)
    y_pred = np.asarray(preds, dtype=float)
    return {
        "order": order,
        "seasonal_order": seasonal_order,
        "mae": _mae(y_true, y_pred),
        "rmse": _rmse(y_true, y_pred),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="ml/models/sarima_model.pkl")
    parser.add_argument("--raw", default="data/raw/aqi_dataset.csv")
    parser.add_argument("--holdout", type=float, default=0.2)
    args = parser.parse_args()

    metrics = evaluate_sarima(args.model, raw_path=args.raw, holdout_ratio=args.holdout)
    print(
        "SARIMA eval: "
        f"order={metrics['order']} seasonal_order={metrics['seasonal_order']} "
        f"mae={metrics['mae']:.3f} rmse={metrics['rmse']:.3f}"
    )


if __name__ == "__main__":
    main()
