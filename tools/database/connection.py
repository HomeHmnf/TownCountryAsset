"""SQLite connection configuration for the local canonical database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = REPOSITORY_ROOT / "data" / "canonical" / "town_country_asset.sqlite"


def connect_database(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
    *,
    timeout_seconds: float = 5.0,
) -> sqlite3.Connection:
    """Open a configured SQLite connection; create parent directories as needed."""
    if timeout_seconds < 0:
        raise ValueError("timeout_seconds must be non-negative")
    path = Path(database_path)
    if str(database_path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
        target = str(path)
    else:
        target = ":memory:"

    connection = sqlite3.connect(
        target,
        timeout=timeout_seconds,
        isolation_level=None,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA busy_timeout = {int(timeout_seconds * 1000)}")
    connection.execute("PRAGMA synchronous = FULL")
    if target != ":memory:":
        connection.execute("PRAGMA journal_mode = WAL")
    return connection
