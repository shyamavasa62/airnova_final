from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from backend.config.settings import settings


@dataclass(frozen=True)
class DbStats:
    n_rows: int


_SCHEMA = """
CREATE TABLE IF NOT EXISTS aqi_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  city TEXT NOT NULL,
  date TEXT NOT NULL,
  aqi REAL NOT NULL,
  pm25 REAL NOT NULL,
  pm10 REAL NOT NULL,
  no2 REAL NOT NULL,
  so2 REAL NOT NULL,
  co REAL NOT NULL,
  o3 REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_aqi_records_city_date ON aqi_records(city, date);
"""


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or settings.DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()


def replace_all(records: Sequence[Tuple[str, str, float, float, float, float, float, float, float]], db_path: Optional[str] = None) -> int:
    """
    Replace full dataset in DB. Records tuple is:
      (city, date_iso, aqi, pm25, pm10, no2, so2, co, o3)
    """
    init_db(db_path)
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM aqi_records")
        conn.executemany(
            """
            INSERT INTO aqi_records(city, date, aqi, pm25, pm10, no2, so2, co, o3)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            list(records),
        )
        conn.commit()
        cur = conn.execute("SELECT COUNT(*) AS n FROM aqi_records")
        return int(cur.fetchone()["n"])


def insert_many(records: Sequence[Tuple[str, str, float, float, float, float, float, float, float]], db_path: Optional[str] = None) -> int:
    init_db(db_path)
    with _connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO aqi_records(city, date, aqi, pm25, pm10, no2, so2, co, o3)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            list(records),
        )
        conn.commit()
        return len(records)


def get_stats(db_path: Optional[str] = None) -> DbStats:
    init_db(db_path)
    with _connect(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM aqi_records").fetchone()
        return DbStats(n_rows=int(row["n"]))


def fetch_all_as_rows(db_path: Optional[str] = None) -> List[sqlite3.Row]:
    init_db(db_path)
    with _connect(db_path) as conn:
        return list(
            conn.execute(
                """
                SELECT city, date, aqi, pm25, pm10, no2, so2, co, o3
                FROM aqi_records
                ORDER BY city ASC, date ASC
                """
            ).fetchall()
        )

