"""Inicjalizacja bazy SQLite."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path


def initialize_database() -> None:
    path = Path(os.environ.get("DATABASE_PATH", "data/app.db"))
    path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(path)) as connection:
        with connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS app_metadata "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
