from __future__ import annotations

import sqlite3

import pytest

from tools.database.connection import DEFAULT_DATABASE_PATH
from tools.database.project_connection import (
    DEFAULT_PROJECT_DATABASE_PATH,
    PROJECT_MIGRATIONS_DIR,
    connect_project_database,
)
from tools.database.schema import (
    MigrationError,
    apply_migrations,
    current_schema_version,
    validate_database,
)


@pytest.fixture
def project_database(tmp_path):
    connection = connect_project_database(tmp_path / "project.sqlite")
    apply_migrations(connection, PROJECT_MIGRATIONS_DIR)
    yield connection
    connection.close()


def test_project_and_game_database_paths_are_distinct():
    assert DEFAULT_PROJECT_DATABASE_PATH != DEFAULT_DATABASE_PATH
    assert DEFAULT_PROJECT_DATABASE_PATH.name == "project_data.sqlite"


def test_project_connection_uses_safe_pragmas_and_migrates_only_project_schema(tmp_path):
    project_path = tmp_path / "project" / "project.sqlite"
    game_path = tmp_path / "canonical" / "game.sqlite"
    with connect_project_database(project_path) as connection:
        assert current_schema_version(connection) == 0
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert apply_migrations(connection, PROJECT_MIGRATIONS_DIR) == 3
        assert validate_database(connection) == []
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {
            "source_organisations",
            "sources",
            "source_urls",
            "datasets",
            "acquisition_streams",
            "acquisitions",
            "acquisition_artifacts",
            "schema_migrations",
        } <= tables
        source_columns = {row[1] for row in connection.execute("PRAGMA table_info(sources)")}
        assert {"domains_json", "license_status", "attribution", "notes", "acquisition_mode", "release_discovery_json", "legacy_source_ids_json", "field_ids_json"} <= source_columns
        acquisition_columns = {row[1] for row in connection.execute("PRAGMA table_info(acquisitions)")}
        assert {"acquisition_event_key", "manifest_sha256", "integrity_status", "evidence_json"} <= acquisition_columns
        assert "countries" not in tables
    assert project_path.is_file()
    assert not game_path.exists()


def test_project_migration_is_idempotent(project_database):
    assert apply_migrations(project_database, PROJECT_MIGRATIONS_DIR) == 3
    assert project_database.execute(
        "SELECT COUNT(*) FROM schema_migrations"
    ).fetchone()[0] == 3


def test_project_schema_enforces_catalogue_relationships(project_database):
    now = "2026-11-05T00:00:00Z"
    project_database.execute(
        "INSERT INTO source_organisations(organisation_key, name, created_at, updated_at) "
        "VALUES ('un', 'United Nations', ?, ?)",
        (now, now),
    )
    project_database.execute(
        "INSERT INTO sources(source_key, organisation_key, name, created_at, updated_at) "
        "VALUES ('un_wpp', 'un', 'World Population Prospects', ?, ?)",
        (now, now),
    )
    project_database.execute(
        "INSERT INTO datasets(source_key, dataset_key, name, created_at, updated_at) "
        "VALUES ('un_wpp', 'demographic_indicators_medium', 'Demographic indicators', ?, ?)",
        (now, now),
    )
    dataset_id = project_database.execute(
        "SELECT dataset_id FROM datasets WHERE dataset_key='demographic_indicators_medium'"
    ).fetchone()[0]
    project_database.execute(
        "INSERT INTO source_urls(source_key, dataset_id, url_role, url, created_at) "
        "VALUES ('un_wpp', ?, 'download', 'https://example.test/data.csv', ?)",
        (dataset_id, now),
    )
    project_database.execute(
        "INSERT INTO acquisition_streams(dataset_id, stream_key, name, created_at, updated_at) "
        "VALUES (?, 'demographic_indicators_medium', 'Demographic indicators', ?, ?)",
        (dataset_id, now, now),
    )
    with pytest.raises(sqlite3.IntegrityError):
        project_database.execute(
            "INSERT INTO source_urls(source_key, dataset_id, url_role, url, created_at) "
            "VALUES ('missing_source', ?, 'download', 'https://example.test/bad.csv', ?)",
            (dataset_id, now),
        )


def test_project_schema_enforces_acquisition_state_and_two_version_limit(project_database):
    now = "2026-11-05T00:00:00Z"
    project_database.execute(
        "INSERT INTO sources(source_key, name, created_at, updated_at) VALUES ('src', 'Source', ?, ?)",
        (now, now),
    )
    project_database.execute(
        "INSERT INTO datasets(source_key, dataset_key, name, created_at, updated_at) "
        "VALUES ('src', 'dataset', 'Dataset', ?, ?)",
        (now, now),
    )
    dataset_id = project_database.execute(
        "SELECT dataset_id FROM datasets WHERE dataset_key='dataset'"
    ).fetchone()[0]
    project_database.execute(
        "INSERT INTO acquisition_streams(dataset_id, stream_key, name, created_at, updated_at) "
        "VALUES (?, 'stream', 'Stream', ?, ?)",
        (dataset_id, now, now),
    )
    stream_id = project_database.execute(
        "SELECT stream_id FROM acquisition_streams WHERE stream_key='stream'"
    ).fetchone()[0]

    def add_acquisition(year: int, status: str = "candidate") -> int:
        cursor = project_database.execute(
            "INSERT INTO acquisitions(stream_id, acquisition_year, acquired_at, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (stream_id, year, now, status, now, now),
        )
        return int(cursor.lastrowid)

    with pytest.raises(sqlite3.IntegrityError, match="validated before retention"):
        add_acquisition(2024, "retained")

    first = add_acquisition(2024)
    second = add_acquisition(2025)
    third = add_acquisition(2026)
    project_database.execute(
        "UPDATE acquisitions SET status='validated' WHERE acquisition_id IN (?, ?)",
        (first, second),
    )
    project_database.execute(
        "UPDATE acquisitions SET status='retained' WHERE acquisition_id IN (?, ?)",
        (first, second),
    )
    project_database.execute(
        "UPDATE acquisitions SET status='validated' WHERE acquisition_id=?",
        (third,),
    )
    with pytest.raises(sqlite3.IntegrityError, match="at most two"):
        project_database.execute(
            "UPDATE acquisitions SET status='retained' WHERE acquisition_id=?",
            (third,),
        )
    project_database.execute(
        "UPDATE acquisitions SET status='superseded' WHERE acquisition_id=?",
        (first,),
    )
    project_database.execute(
        "UPDATE acquisitions SET status='retained' WHERE acquisition_id=?",
        (third,),
    )
    assert project_database.execute(
        "SELECT COUNT(*) FROM acquisitions WHERE stream_id=? AND status='retained'",
        (stream_id,),
    ).fetchone()[0] == 2


def test_project_migration_failure_rolls_back_ddl_and_ledger(tmp_path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_broken.sql").write_text(
        "CREATE TABLE should_rollback (id INTEGER); SELECT * FROM missing_table;",
        encoding="utf-8",
    )
    with connect_project_database(tmp_path / "broken.sqlite") as connection:
        with pytest.raises(MigrationError, match="001_broken.sql"):
            apply_migrations(connection, migrations)
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name='should_rollback'"
        ).fetchone() is None
        assert current_schema_version(connection) == 0


def test_project_migration_rejects_future_schema(tmp_path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_initial.sql").write_text(
        "CREATE TABLE sample (id INTEGER);", encoding="utf-8"
    )
    with connect_project_database(tmp_path / "future.sqlite") as connection:
        apply_migrations(connection, migrations)
        connection.execute(
            "INSERT INTO schema_migrations(version, name, applied_at) VALUES (2, 'future', 'now')"
        )
        with pytest.raises(MigrationError, match="newer than supported"):
            apply_migrations(connection, migrations)
