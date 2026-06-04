from __future__ import annotations

import pandas as pd

from backend.config.settings import settings
from backend.db import replace_all
from ml.src.data_source import export_effective_dataset_csv, load_effective_dataset


def test_ml_data_source_reads_from_db(tmp_path):
    settings.DB_PATH = str(tmp_path / "airnova_ml.sqlite3")

    n = replace_all(
        records=[
            ("Delhi", "2018-01-01", 120.0, 55.0, 110.0, 22.0, 6.0, 1.2, 18.0),
            ("Delhi", "2018-01-02", 130.0, 60.0, 115.0, 24.0, 7.0, 1.1, 20.0),
        ]
    )
    assert n == 2

    df = load_effective_dataset()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert set(["City", "Date", "AQI", "PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]).issubset(df.columns)

    path = export_effective_dataset_csv()
    out = pd.read_csv(path)
    assert len(out) == 2

