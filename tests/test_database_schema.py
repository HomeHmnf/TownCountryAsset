from __future__ import annotations

import sqlite3

import pytest

from tools.database.connection import connect_database
from tools.database.schema import MigrationError, apply_migrations, current_schema_version, validate_database


@pytest.fixture
def database(tmp_path):
    connection = connect_database(tmp_path / "canonical.sqlite")
    apply_migrations(connection)
    yield connection
    connection.close()


def seed_country(connection, game_id="tc_00000000000000000000000000000000"):
    connection.execute(
        "INSERT INTO countries(game_id, created_at, updated_at) VALUES (?, '2026-10-30T00:00:00Z', '2026-10-30T00:00:00Z')",
        (game_id,),
    )
    connection.execute(
        "INSERT INTO dataset_imports(dataset, sha256, imported_at) VALUES ('fixture', ?, '2026-10-30T00:00:00Z')",
        ("a" * 64,),
    )
    return connection.execute("SELECT import_id FROM dataset_imports ORDER BY import_id DESC LIMIT 1").fetchone()[0]


def test_fresh_database_applies_all_migrations_and_integrity_passes(tmp_path):
    path = tmp_path / "nested" / "canonical.sqlite"
    with connect_database(path) as connection:
        assert current_schema_version(connection) == 0
        assert apply_migrations(connection) == 3
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert validate_database(connection) == []
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"countries", "country_sources", "country_geometries", "review_proposals", "current_statistics", "selected_game_data", "schema_migrations"} <= tables


def test_migration_is_idempotent(database):
    assert apply_migrations(database) == 3
    assert database.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 3


def test_game_id_requires_exact_tc_prefix_and_32_lowercase_hex(database):
    for invalid in ("tc_abc", "tc_" + "g" * 32, "TC_" + "a" * 32, "tc_" + "A" * 32):
        with pytest.raises(sqlite3.IntegrityError):
            seed_country(database, invalid)


def test_duplicate_game_id_is_rejected(database):
    seed_country(database)
    with pytest.raises(sqlite3.IntegrityError):
        seed_country(database)


def test_iso_syntax_and_verified_status_constraints(database):
    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "INSERT INTO countries(game_id, iso_alpha2, created_at, updated_at) VALUES (?, 'USA', 'x', 'x')",
            ("tc_" + "1" * 32,),
        )
    with pytest.raises(sqlite3.IntegrityError, match="verified ISO"):
        database.execute(
            "INSERT INTO countries(game_id, iso_assignment_status, created_at, updated_at) VALUES (?, 'verified', 'x', 'x')",
            ("tc_" + "2" * 32,),
        )


def test_source_current_identity_unique_but_historical_source_can_be_reused(database):
    import_id = seed_country(database)
    second_id = "tc_" + "3" * 32
    seed_country(database, second_id)
    database.execute(
        "INSERT INTO country_sources(game_id, dataset, source_id, is_current, import_id) VALUES (?, 'ne', 'AAA', 1, ?)",
        ("tc_" + "0" * 32, import_id),
    )
    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "INSERT INTO country_sources(game_id, dataset, source_id, is_current, import_id) VALUES (?, 'ne', 'AAA', 1, ?)",
            (second_id, import_id),
        )
    database.execute(
        "INSERT INTO country_sources(game_id, dataset, source_id, is_current, import_id) VALUES (?, 'ne', 'AAA', 0, ?)",
        (second_id, import_id),
    )


def test_names_regions_attributes_and_geometry_constraints(database):
    import_id = seed_country(database)
    gid = "tc_" + "0" * 32
    database.execute("INSERT INTO country_names(game_id, language, name, name_type) VALUES (?, 'fa', 'ایران', 'canonical')", (gid,))
    with pytest.raises(sqlite3.IntegrityError):
        database.execute("INSERT INTO country_names(game_id, language, name, name_type) VALUES (?, 'fa', 'ایران', 'canonical')", (gid,))
    database.execute("INSERT INTO country_regions(game_id, region) VALUES (?, 'Asia')", (gid,))
    database.execute("INSERT INTO country_attributes(game_id, attribute_key, attribute_value, value_type) VALUES (?, 'nested', '{\"x\":1}', 'json')", (gid,))
    with pytest.raises(sqlite3.IntegrityError):
        database.execute("INSERT INTO country_attributes(game_id, attribute_key, attribute_value, value_type) VALUES (?, 'bad', '{', 'json')", (gid,))
    for profile in ("low", "medium", "high"):
        database.execute(
            "INSERT INTO country_geometries(game_id, profile, geometry_json, sha256, import_id) VALUES (?, ?, '{}', ?, ?)",
            (gid, profile, "b" * 64, import_id),
        )
    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "INSERT INTO country_geometries(game_id, profile, geometry_json, sha256, import_id) VALUES (?, 'ultra', '{}', ?, ?)",
            (gid, "b" * 64, import_id),
        )


def test_statistics_and_selected_game_data_are_unique_and_json_valid(database):
    seed_country(database)
    gid = "tc_" + "0" * 32
    database.execute("INSERT INTO current_statistics(game_id, statistic_key, value, observed_at) VALUES (?, 'population', 100, '2026-10-30')", (gid,))
    with pytest.raises(sqlite3.IntegrityError):
        database.execute("INSERT INTO current_statistics(game_id, statistic_key, value, observed_at) VALUES (?, 'population', 101, '2026-10-30')", (gid,))
    database.execute("INSERT INTO selected_game_data(game_id, data_category, data_key, payload_json) VALUES (?, 'quiz', 'capital', '{\"value\":\"Tehran\"}')", (gid,))
    with pytest.raises(sqlite3.IntegrityError):
        database.execute("INSERT INTO selected_game_data(game_id, data_category, data_key, payload_json) VALUES (?, 'quiz', 'capital', '{')", (gid,))


def test_statistics_support_explicit_nulls_and_source_observation_metadata(database):
    import_id = seed_country(database)
    gid = "tc_" + "0" * 32
    database.execute(
        """INSERT INTO current_statistics(
            game_id, statistic_key, value, unit, observed_at, observation_period,
            value_status, source_reference, source_version, methodology, retrieved_at, import_id
        ) VALUES (?, 'population_growth', NULL, '%', NULL, '2025', 'unavailable',
                  'https://example.test/source', '2025-release', 'national estimate',
                  '2026-10-31T00:00:00Z', ?)""",
        (gid, import_id),
    )
    row = database.execute(
        "SELECT value, value_status, observation_period, source_version FROM current_statistics WHERE game_id = ?",
        (gid,),
    ).fetchone()
    assert tuple(row) == (None, "unavailable", "2025", "2025-release")

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "INSERT INTO current_statistics(game_id, statistic_key, value, value_status) VALUES (?, 'invalid_null', NULL, 'observed')",
            (gid,),
        )
    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "INSERT INTO current_statistics(game_id, statistic_key, value, value_status) VALUES (?, 'invalid_value', 1, 'unavailable')",
            (gid,),
        )


def test_review_proposal_dedup_and_approval_timestamp(database):
    seed_country(database)
    gid = "tc_" + "0" * 32
    fingerprint = "c" * 64
    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "INSERT INTO review_proposals(game_id, proposal_type, proposal_fingerprint, proposed_json, created_at, review_status) VALUES (?, 'iso', ?, '{}', 'now', 'approved')",
            (gid, fingerprint),
        )
    database.execute(
        "INSERT INTO review_proposals(game_id, proposal_type, proposal_fingerprint, proposed_json, created_at) VALUES (?, 'iso', ?, '{}', 'now')",
        (gid, fingerprint),
    )
    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "INSERT INTO review_proposals(game_id, proposal_type, proposal_fingerprint, proposed_json, created_at) VALUES (?, 'iso', ?, '{}', 'now')",
            (gid, fingerprint),
        )


def test_reviewed_flag_requires_approved_proposal(database):
    seed_country(database)
    gid = "tc_" + "0" * 32
    with pytest.raises(sqlite3.IntegrityError, match="approved flag proposal"):
        database.execute("INSERT INTO country_flags(game_id, mapping_status) VALUES (?, 'reviewed')", (gid,))


def test_failed_migration_rolls_back_ddl_and_ledger(tmp_path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_broken.sql").write_text(
        "CREATE TABLE should_rollback (id INTEGER);\nSELECT * FROM missing_table;",
        encoding="utf-8",
    )
    with connect_database(":memory:") as connection:
        with pytest.raises(MigrationError, match="001_broken.sql"):
            apply_migrations(connection, migrations)
        assert connection.execute("SELECT 1 FROM sqlite_master WHERE name='should_rollback'").fetchone() is None
        assert current_schema_version(connection) == 0


def test_future_database_schema_fails_safely(tmp_path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_initial.sql").write_text("CREATE TABLE sample (id INTEGER);", encoding="utf-8")
    with connect_database(":memory:") as connection:
        apply_migrations(connection, migrations)
        connection.execute("INSERT INTO schema_migrations(version, name, applied_at) VALUES (2, 'future', 'now')")
        with pytest.raises(MigrationError, match="newer than supported"):
            apply_migrations(connection, migrations)
