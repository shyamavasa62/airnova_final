from __future__ import annotations

import os
import pickle
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA


@dataclass(frozen=True)
class ArimaTrainConfig:
    raw_path: str = "data/raw/aqi_dataset.csv"
    model_out: str = "ml/models/arima_model.pkl"

    # Small grid to keep training fast.
    p_values: Tuple[int, ...] = (0, 1, 2)
    d_values: Tuple[int, ...] = (0, 1)
    q_values: Tuple[int, ...] = (0, 1, 2)

    # Hold out last chunk for a simple validation score.
    holdout_ratio: float = 0.2


def _load_aqi_series(raw_path: str) -> pd.Series:
    df = pd.read_csv(raw_path)
    df = df.dropna(subset=["Date", "AQI"])

    # Dataset often uses DD/MM/YY; be permissive.
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date"])
    df = df.sort_values("Date")

    # Ensure AQI is numeric (some CSVs contain AQI as text).
    df["AQI"] = pd.to_numeric(df["AQI"], errors="coerce")
    df = df.dropna(subset=["AQI"])

    # If there are multiple rows per day, average them to a single daily series.
    daily = df.groupby(df["Date"].dt.date)["AQI"].mean()
    daily.index = pd.to_datetime(daily.index)

    # Regularize to daily frequency and fill small gaps.
    daily = daily.asfreq("D")
    daily = daily.interpolate(limit_direction="both")

    series = daily.astype(float)
    series = series.replace([np.inf, -np.inf], np.nan).dropna()
    if len(series) < 30:
        raise ValueError("Not enough data points to train ARIMA (need >= 30).")
    return series


def _train_holdout_split(series: pd.Series, holdout_ratio: float) -> Tuple[pd.Series, pd.Series]:
    n = len(series)
    holdout_n = max(1, int(round(n * holdout_ratio)))
    train = series.iloc[: n - holdout_n]
    valid = series.iloc[n - holdout_n :]
    return train, valid


def _iter_orders(p_values: Iterable[int], d_values: Iterable[int], q_values: Iterable[int]):
    for p in p_values:
        for d in d_values:
            for q in q_values:
                yield (p, d, q)


def _select_order_by_aic(train: pd.Series, cfg: ArimaTrainConfig) -> Tuple[int, int, int]:
    best_order: Optional[Tuple[int, int, int]] = None
    best_aic: float = float("inf")

    for order in _iter_orders(cfg.p_values, cfg.d_values, cfg.q_values):
        try:
            res = ARIMA(train, order=order, enforce_stationarity=False, enforce_invertibility=False).fit()
        except Exception:
            continue
        aic = float(res.aic)
        if np.isfinite(aic) and aic < best_aic:
            best_aic = aic
            best_order = order

    if best_order is None:
        raise RuntimeError("Failed to fit any ARIMA model from the configured grid.")
    return best_order


def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true - y_pred)))


def train_arima(cfg: ArimaTrainConfig) -> Dict[str, object]:
    series = _load_aqi_series(cfg.raw_path)
    train, valid = _train_holdout_split(series, cfg.holdout_ratio)

    order = _select_order_by_aic(train, cfg)
    fitted = ARIMA(train, order=order, enforce_stationarity=False, enforce_invertibility=False).fit()

    # Simple validation: 1-step ahead rolling forecast over the holdout window.
    history = train.copy()
    preds = []
    for t in range(len(valid)):
        step_model = ARIMA(history, order=order, enforce_stationarity=False, enforce_invertibility=False).fit()
        yhat = float(step_model.forecast(steps=1).iloc[0])
        preds.append(yhat)
        history = pd.concat([history, valid.iloc[t : t + 1]])

    valid_mae = _mae(valid.values, np.asarray(preds))

    artifact = {
        "model_type": "arima",
        "order": order,
        "train_start": str(series.index.min().date()),
        "train_end": str(series.index.max().date()),
        "n_points": int(len(series)),
        "fitted_model": fitted,
    }

    os.makedirs(os.path.dirname(cfg.model_out), exist_ok=True)
    with open(cfg.model_out, "wb") as f:
        pickle.dump(artifact, f)

    return {"order": order, "valid_mae": valid_mae, "model_out": cfg.model_out}


def main() -> None:
    cfg = ArimaTrainConfig()
    result = train_arima(cfg)
    print(
        "ARIMA training complete. "
        f"order={result['order']} valid_mae={result['valid_mae']:.3f} "
        f"saved={result['model_out']}"
    )


if __name__ == "__main__":
    main()
