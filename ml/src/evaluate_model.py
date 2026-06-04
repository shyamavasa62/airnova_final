from __future__ import annotations

import argparse
import pickle
from typing import Dict, Tuple

import numpy as np
import pandas as pd


def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true - y_pred)))


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


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


def evaluate_arima(
    model_path: str,
    raw_path: str = "data/raw/aqi_dataset.csv",
    holdout_ratio: float = 0.2,
) -> Dict[str, float | Tuple[int, int, int]]:
    with open(model_path, "rb") as f:
        artifact = pickle.load(f)

    if not isinstance(artifact, dict) or "fitted_model" not in artifact:
        raise ValueError("Model artifact is not in expected ARIMA artifact format.")

    order = tuple(artifact.get("order", ()))  # type: ignore[assignment]

    series = _load_aqi_series(raw_path)
    n = len(series)
    holdout_n = max(1, int(round(n * holdout_ratio)))
    train = series.iloc[: n - holdout_n]
    valid = series.iloc[n - holdout_n :]

    # Rolling 1-step MAE/RMSE.
    from statsmodels.tsa.arima.model import ARIMA

    history = train.copy()
    preds = []
    for t in range(len(valid)):
        step_model = ARIMA(history, order=order, enforce_stationarity=False, enforce_invertibility=False).fit()
        yhat = float(step_model.forecast(steps=1).iloc[0])
        preds.append(yhat)
        history = pd.concat([history, valid.iloc[t : t + 1]])

    y_true = valid.values
    y_pred = np.asarray(preds)
    return {"order": order, "mae": _mae(y_true, y_pred), "rmse": _rmse(y_true, y_pred)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Path to ARIMA model artifact pkl")
    parser.add_argument("--raw", default="data/raw/aqi_dataset.csv", help="Path to raw AQI CSV")
    parser.add_argument("--holdout", type=float, default=0.2, help="Holdout ratio for evaluation")
    args = parser.parse_args()

    metrics = evaluate_arima(args.model, raw_path=args.raw, holdout_ratio=args.holdout)
    print(f"ARIMA eval: order={metrics['order']} mae={metrics['mae']:.3f} rmse={metrics['rmse']:.3f}")


if __name__ == "__main__":
    main()
