from __future__ import annotations

import argparse
import os
import pickle
from typing import Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX


def _load_aqi_series(raw_path: str) -> pd.Series:
    df = pd.read_csv(raw_path)
    df = df.dropna(subset=["Date", "AQI"])
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date"])
    df["AQI"] = pd.to_numeric(df["AQI"], errors="coerce")
    df = df.dropna(subset=["AQI"])
    df = df.sort_values("Date")
    daily = df.groupby(df["Date"].dt.date)["AQI"].mean()
    daily.index = pd.to_datetime(daily.index)
    daily = daily.asfreq("D").interpolate(limit_direction="both")
    return daily.astype(float).replace([np.inf, -np.inf], np.nan).dropna()


def _split_train_test(series: pd.Series, test_ratio: float = 0.2):
    n = len(series)
    test_n = max(1, int(round(n * test_ratio)))
    return series.iloc[: n - test_n], series.iloc[n - test_n :]


def _rolling_forecast(
    train: pd.Series,
    test: pd.Series,
    order: Tuple[int, int, int],
    seasonal_order: Tuple[int, int, int, int],
) -> np.ndarray:
    history = train.copy()
    preds = []
    for i in range(len(test)):
        fit = SARIMAX(
            history,
            order=order,
            seasonal_order=seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False)
        yhat = float(fit.forecast(steps=1).iloc[0])
        preds.append(yhat)
        history = pd.concat([history, test.iloc[i : i + 1]])
    return np.asarray(preds, dtype=float)


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Tuple[float, float]:
    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    return mae, rmse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", default="data/raw/aqi_dataset.csv")
    parser.add_argument("--model", default="ml/models/sarima_model.pkl")
    parser.add_argument("--out", default="docs/screenshots/sarima_actual_vs_predicted.png")
    parser.add_argument("--test-ratio", type=float, default=0.2)
    parser.add_argument("--max-points", type=int, default=120)
    args = parser.parse_args()

    with open(args.model, "rb") as f:
        artifact = pickle.load(f)
    order = tuple(artifact["order"])
    seasonal_order = tuple(artifact["seasonal_order"])

    series = _load_aqi_series(args.raw)
    train, test = _split_train_test(series, test_ratio=args.test_ratio)
    preds = _rolling_forecast(train, test, order=order, seasonal_order=seasonal_order)

    y_true = test.values.astype(float)
    mae, rmse = _metrics(y_true, preds)

    n_plot = min(args.max_points, len(y_true))
    x = np.arange(n_plot)

    plt.figure(figsize=(11, 6))
    plt.plot(x, y_true[:n_plot], label="Actual AQI", linewidth=2)
    plt.plot(x, preds[:n_plot], label="Predicted AQI (SARIMA)", linewidth=2)
    plt.title(
        f"SARIMA Actual vs Predicted AQI | order={order} "
        f"seasonal={seasonal_order} | MAE={mae:.2f} RMSE={rmse:.2f}"
    )
    plt.xlabel("Test Samples")
    plt.ylabel("AQI")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    plt.savefig(args.out, dpi=220)
    print(f"Saved plot to: {args.out}")
    print(
        f"order={order} seasonal_order={seasonal_order} "
        f"mae={mae:.3f} rmse={rmse:.3f} test_points={len(y_true)}"
    )


if __name__ == "__main__":
    main()
