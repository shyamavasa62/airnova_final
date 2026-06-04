from __future__ import annotations

import os
import pickle
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX


@dataclass(frozen=True)
class SarimaTrainConfig:
    raw_path: str = "data/raw/aqi_dataset.csv"
    model_out: str = "ml/models/sarima_model.pkl"

    p_values: Tuple[int, ...] = (0, 1)
    d_values: Tuple[int, ...] = (0, 1)
    q_values: Tuple[int, ...] = (0, 1)

    P_values: Tuple[int, ...] = (0, 1)
    D_values: Tuple[int, ...] = (0, 1)
    Q_values: Tuple[int, ...] = (0, 1)
    seasonal_period: int = 7

    holdout_ratio: float = 0.2


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

    series = daily.astype(float).replace([np.inf, -np.inf], np.nan).dropna()
    if len(series) < 60:
        raise ValueError("Not enough data points to train SARIMA (need >= 60).")
    return series


def _split(series: pd.Series, holdout_ratio: float) -> Tuple[pd.Series, pd.Series]:
    n = len(series)
    holdout_n = max(1, int(round(n * holdout_ratio)))
    return series.iloc[: n - holdout_n], series.iloc[n - holdout_n :]


def _iter_orders(values: Iterable[int]):
    for a in values:
        yield a


def _select_best(train: pd.Series, cfg: SarimaTrainConfig) -> Tuple[Tuple[int, int, int], Tuple[int, int, int, int]]:
    best_aic = float("inf")
    best_order: Optional[Tuple[int, int, int]] = None
    best_seasonal: Optional[Tuple[int, int, int, int]] = None

    for p in cfg.p_values:
        for d in cfg.d_values:
            for q in cfg.q_values:
                order = (p, d, q)
                for P in cfg.P_values:
                    for D in cfg.D_values:
                        for Q in cfg.Q_values:
                            seasonal = (P, D, Q, cfg.seasonal_period)
                            try:
                                fit = SARIMAX(
                                    train,
                                    order=order,
                                    seasonal_order=seasonal,
                                    enforce_stationarity=False,
                                    enforce_invertibility=False,
                                ).fit(disp=False)
                            except Exception:
                                continue
                            aic = float(fit.aic)
                            if np.isfinite(aic) and aic < best_aic:
                                best_aic = aic
                                best_order = order
                                best_seasonal = seasonal

    if best_order is None or best_seasonal is None:
        raise RuntimeError("Failed to fit any SARIMA model from configured grid.")
    return best_order, best_seasonal


def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float))))


def train_sarima(cfg: SarimaTrainConfig) -> Dict[str, object]:
    series = _load_aqi_series(cfg.raw_path)
    train, valid = _split(series, cfg.holdout_ratio)
    order, seasonal = _select_best(train, cfg)

    fitted = SARIMAX(
        train,
        order=order,
        seasonal_order=seasonal,
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(disp=False)

    history = train.copy()
    preds = []
    for i in range(len(valid)):
        step_fit = SARIMAX(
            history,
            order=order,
            seasonal_order=seasonal,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False)
        yhat = float(step_fit.forecast(steps=1).iloc[0])
        preds.append(yhat)
        history = pd.concat([history, valid.iloc[i : i + 1]])

    valid_mae = _mae(valid.values, np.asarray(preds))

    artifact = {
        "model_type": "sarima",
        "order": order,
        "seasonal_order": seasonal,
        "seasonal_period": cfg.seasonal_period,
        "train_start": str(series.index.min().date()),
        "train_end": str(series.index.max().date()),
        "n_points": int(len(series)),
        "fitted_model": fitted,
    }

    os.makedirs(os.path.dirname(cfg.model_out), exist_ok=True)
    with open(cfg.model_out, "wb") as f:
        pickle.dump(artifact, f)

    return {
        "order": order,
        "seasonal_order": seasonal,
        "valid_mae": valid_mae,
        "model_out": cfg.model_out,
    }


def main() -> None:
    cfg = SarimaTrainConfig()
    result = train_sarima(cfg)
    print(
        "SARIMA training complete. "
        f"order={result['order']} seasonal_order={result['seasonal_order']} "
        f"valid_mae={result['valid_mae']:.3f} saved={result['model_out']}"
    )


if __name__ == "__main__":
    main()
