from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class FeatureEngineeringConfig:
    cleaned_path: str = "data/processed/cleaned_data.csv"
    feature_engineered_path: str = "data/processed/feature_engineered_data.csv"

    # Match ml/src/train_model.py behavior: predict future AQI by shifting AQI by -1.
    target_shift_steps: int = -1


def add_time_features_and_target(
    df: pd.DataFrame,
    shift_steps: int = -1,
) -> pd.DataFrame:
    """
    Add:
    - day, month, weekend
    - AQI_future = AQI shifted by -1 (global shift to match current training script)
    """
    if "Date" not in df.columns or "AQI" not in df.columns:
        raise ValueError("Input dataframe must include columns: 'Date', 'AQI'.")

    # Ensure Date is datetime (idempotent).
    if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        df = df.dropna(subset=["Date"])

    df = df.copy()
    df["day"] = df["Date"].dt.day
    df["month"] = df["Date"].dt.month
    df["weekend"] = (df["Date"].dt.weekday >= 5).astype(int)

    df["AQI_future"] = df["AQI"].shift(shift_steps)
    df = df.dropna(subset=["AQI_future"])
    return df


def feature_engineer(
    cleaned_path: str,
    feature_engineered_path: str,
    out_dir: Optional[str] = None,
) -> pd.DataFrame:
    df = pd.read_csv(cleaned_path)
    engineered = add_time_features_and_target(df, shift_steps=-1)

    os.makedirs(out_dir or os.path.dirname(feature_engineered_path), exist_ok=True)
    engineered.to_csv(feature_engineered_path, index=False)
    return engineered


def main() -> None:
    cfg = FeatureEngineeringConfig()
    engineered = feature_engineer(
        cleaned_path=cfg.cleaned_path,
        feature_engineered_path=cfg.feature_engineered_path,
    )
    print(
        f"Feature engineering done. Rows: {len(engineered)}. "
        f"Saved feature engineered CSV."
    )


if __name__ == "__main__":
    main()
