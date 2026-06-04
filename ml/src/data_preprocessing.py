from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class PreprocessConfig:
    raw_path: str = "data/raw/aqi_dataset.csv"
    interim_path: str = "data/interim/temp_data.csv"
    cleaned_path: str = "data/processed/cleaned_data.csv"


def preprocess_raw_data(
    raw_path: str,
    interim_path: Optional[str] = None,
    cleaned_path: Optional[str] = None,
) -> pd.DataFrame:
    """
    Basic cleaning step:
    - load raw CSV
    - drop NA rows
    - parse Date
    - drop rows with invalid Date
    """
    df = pd.read_csv(raw_path)
    df = df.dropna()

    # Dataset uses DD/MM/YY in practice (e.g., 01/01/18). Use dayfirst=True.
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date"])

    if interim_path:
        os.makedirs(os.path.dirname(interim_path), exist_ok=True)
        df.to_csv(interim_path, index=False)

    if cleaned_path:
        os.makedirs(os.path.dirname(cleaned_path), exist_ok=True)
        df.to_csv(cleaned_path, index=False)

    return df


def main() -> None:
    cfg = PreprocessConfig()
    df = preprocess_raw_data(
        raw_path=cfg.raw_path,
        interim_path=cfg.interim_path,
        cleaned_path=cfg.cleaned_path,
    )
    print(f"Preprocessing done. Rows: {len(df)}. Saved cleaned CSV.")


if __name__ == "__main__":
    main()
