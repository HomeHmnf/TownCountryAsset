"""Transactional, local-only SQLite schema migration management."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from tools.database.connection import REPOSITORY_ROOT

DEFAULT_MIGRATIONS_DIR = REPOSITORY_ROOT / "migrations"
MIGRATION_PATTERN = re.compile(r"^(\d{3})_([a-z0-9_]+)\.sql$")


class MigrationError(RuntimeError):
    """Raised when the local database cannot be safely migrated."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _migration_files(migrations_dir: str | Path) -> list[tuple[int, str, Path]]:
    directory = Path(migrations_dir)
    if not directory.is_dir():
        raise MigrationError(f"Migration directory does not exist: {directory}")
    migrations = []
    for path in directory.iterdir():
        match = MIGRATION_PATTERN.fullmatch(path.name)
        if match and path.is_file():
            migrations.append((int(match.group(1)), path.name, path))
    migrations.sort(key=lambda item: item[0])
    versions = [item[0] for item in migrations]
    if len(versions) != len(set(versions)):
        raise MigrationError("Migration filenames contain duplicate version numbers")
    if versions and versions != list(range(1, max(versions) + 1)):
        raise MigrationError("Migration versions must be contiguous starting at 001")
    return migrations


def current_schema_version(connection: sqlite3.Connection) -> int:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
    ).fetchone()
    if exists is None:
        return 0
    row = connection.execute("SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations").fetchone()
    return int(row["version"])


def apply_migrations(
    connection: sqlite3.Connection,
    migrations_dir: str | Path = DEFAULT_MIGRATIONS_DIR,
) -> int:
    """Apply pending migrations in order, one SQLite transaction per migration."""
    migrations = _migration_files(migrations_dir)
    connection.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY CHECK (version > 0),
            name TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL
        )"""
    )
    applied_version = current_schema_version(connection)
    latest_available = migrations[-1][0] if migrations else 0
    if applied_version > latest_available:
        raise MigrationError(
            f"Database schema version {applied_version} is newer than supported version {latest_available}"
        )

    applied_rows = connection.execute(
        "SELECT version, name FROM schema_migrations ORDER BY version"
    ).fetchall()
    applied_versions = [int(row["version"]) for row in applied_rows]
    if applied_versions != list(range(1, applied_version + 1)):
        raise MigrationError("Applied migration ledger is not contiguous starting at version 1")
    for row in applied_rows:
        matching = next((item for item in migrations if item[0] == row["version"]), None)
        if matching is None or matching[1] != row["name"]:
            raise MigrationError(
                f"Applied migration {row['version']} ({row['name']}) does not match available migration files"
            )

    for version, name, path in migrations:
        if version <= applied_version:
            continue
        sql = path.read_text(encoding="utf-8")
        try:
            connection.executescript(
                "BEGIN IMMEDIATE;\n"
                + sql
                + "\nINSERT INTO schema_migrations(version, name, applied_at) VALUES ("
                + str(version)
                + ", "
                + "'"
                + name.replace("'", "''")
                + "', '"
                + utc_now()
                + "');\nCOMMIT;"
            )
        except sqlite3.Error as exc:
            if connection.in_transaction:
                connection.rollback()
            raise MigrationError(f"Migration {name} failed: {exc}") from exc
        applied_version = version
    return applied_version


def validate_database(connection: sqlite3.Connection) -> list[str]:
    """Return SQLite integrity and foreign-key violations, if any."""
    issues: list[str] = []
    integrity = connection.execute("PRAGMA integrity_check").fetchall()
    issues.extend(str(row[0]) for row in integrity if row[0] != "ok")
    foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    issues.extend(
        f"foreign key violation: table={row[0]} rowid={row[1]} parent={row[2]}"
        for row in foreign_keys
    )
    return issues
