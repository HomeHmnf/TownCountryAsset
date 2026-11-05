"""Connection and migration configuration for the project source database."""

from __future__ import annotations

from pathlib import Path
import sqlite3

from tools.database.connection import REPOSITORY_ROOT, connect_database

DEFAULT_PROJECT_DATABASE_PATH = (
    REPOSITORY_ROOT / "data" / "project" / "project_data.sqlite"
)
PROJECT_MIGRATIONS_DIR = REPOSITORY_ROOT / "migrations" / "project"


def connect_project_database(
    database_path: str | Path = DEFAULT_PROJECT_DATABASE_PATH,
    *,
    timeout_seconds: float = 5.0,
) -> sqlite3.Connection:
    """Open the project DB without opening or migrating the game database."""
    return connect_database(database_path, timeout_seconds=timeout_seconds)
