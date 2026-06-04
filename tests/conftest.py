from __future__ import annotations

import io
from typing import Iterator

import pytest

from backend.app import create_app
from backend.config.settings import settings
from backend.db import init_db


@pytest.fixture()
def app(tmp_path) -> Iterator[object]:
    db_path = tmp_path / "airnova_test.sqlite3"
    settings.DB_PATH = str(db_path)
    init_db()

    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


def make_csv_bytes(rows: str) -> io.BytesIO:
    return io.BytesIO(rows.encode("utf-8"))

