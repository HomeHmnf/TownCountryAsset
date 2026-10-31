import hashlib
import json
import sqlite3

import pytest

from tools.database.connection import connect_database
from tools.database.identity_import import IdentityImportError, import_identity_registry
from tools.database.schema import apply_migrations, validate_database


ARCHIVE_SHA = "a" * 64


def write_inputs(tmp_path, *, conflict=False):
    registry_dir = tmp_path / "config"
    candidate_dir = tmp_path / "candidate"
    registry_dir.mkdir()
    candidate_dir.mkdir()
    records = [
        {
            "game_id": "tc_" + "1" * 32,
            "source": {"dataset": "fixture", "current_source_id": "AAA", "previous_source_ids": ["OLD_AAA"]},
            "status": "proposed",
            "iso": {"alpha2": None, "alpha3": "AAA", "assignment_status": "unverified"},
            "names": {"en": "Alpha", "fa": None, "aliases_en": ["Alpha Isles"], "aliases_fa": [], "localization_status": "unreviewed"},
            "entity_type": "unreviewed",
            "regions": ["Asia"],
            "geometry_key": "AAA",
        },
        {
            "game_id": "tc_" + "2" * 32,
            "source": {"dataset": "fixture", "current_source_id": "BBB", "previous_source_ids": []},
            "status": "proposed",
            "iso": {"alpha2": None, "alpha3": "BBB", "assignment_status": "unverified"},
            "names": {"en": "Beta", "fa": None, "aliases_en": [], "aliases_fa": [], "localization_status": "unreviewed"},
            "entity_type": "unreviewed",
            "regions": [],
            "geometry_key": "BBB",
        },
    ]
    countries = [
        {"id": "AAA", "game_id": records[0]["game_id"], "iso3": "AAA", "name": "Alpha", "aliases": ["Alpha Isles"], "regions": ["Asia"]},
        {"id": "BBB", "game_id": records[1]["game_id"], "iso3": "BBB", "name": "Beta", "aliases": [], "regions": []},
    ]
    if conflict:
        countries[0]["game_id"] = "tc_" + "3" * 32
    registry = {"schema_version": 1, "dataset": "fixture", "status": "proposal", "records": records}
    candidate = {
        "schema_version": 1,
        "source": {
            "archive_sha256": ARCHIVE_SHA,
            "source_version": "test",
            "url": "https://example.test/source",
            "retrieval_date": "2026-01-01",
            "attribution": "Fixture",
            "license": "Public domain",
        },
        "count": len(countries),
        "countries": countries,
    }
    registry_path = registry_dir / "country_identity_registry.json"
    countries_path = candidate_dir / "countries.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    countries_path.write_text(json.dumps(candidate), encoding="utf-8")
    manifest = {
        "files": {
            "countries.json": {
                "sha256": hashlib.sha256(countries_path.read_bytes()).hexdigest()
            }
        }
    }
    (candidate_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return registry_path, candidate_dir


def test_imports_identity_provenance_names_regions_and_history(tmp_path):
    registry, candidate = write_inputs(tmp_path)
    database = tmp_path / "canonical.sqlite"
    result = import_identity_registry(database, registry, candidate)
    assert result["countries"] == 2
    connection = connect_database(database)
    try:
        assert connection.execute("SELECT COUNT(*) FROM countries").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 1
        assert connection.execute(
            "SELECT is_current FROM country_sources WHERE source_id = 'OLD_AAA'"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT is_current FROM country_sources WHERE source_id = 'AAA'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT name FROM country_names WHERE game_id = ? AND name_type = 'canonical'",
            ("tc_" + "1" * 32,),
        ).fetchone()[0] == "Alpha"
        assert connection.execute("SELECT COUNT(*) FROM country_regions").fetchone()[0] == 1
        country = connection.execute(
            "SELECT record_status, iso_alpha2, iso_alpha3, iso_assignment_status, localization_status "
            "FROM countries WHERE game_id = ?",
            ("tc_" + "1" * 32,),
        ).fetchone()
        assert tuple(country) == ("candidate", None, "AAA", "unverified", "unreviewed")
        assert validate_database(connection) == []
    finally:
        connection.close()


def test_repeat_import_is_idempotent(tmp_path):
    registry, candidate = write_inputs(tmp_path)
    database = tmp_path / "canonical.sqlite"
    first = import_identity_registry(database, registry, candidate)
    second = import_identity_registry(database, registry, candidate)
    assert first["import_id"] == second["import_id"]
    connection = connect_database(database)
    try:
        for table in ("dataset_imports", "countries", "country_sources", "country_names", "country_regions"):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == {
                "dataset_imports": 1,
                "countries": 2,
                "country_sources": 3,
                "country_names": 3,
                "country_regions": 1,
            }[table]
    finally:
        connection.close()


def test_rejects_registry_candidate_game_id_mismatch_without_partial_import(tmp_path):
    registry, candidate = write_inputs(tmp_path, conflict=True)
    database = tmp_path / "canonical.sqlite"
    with pytest.raises(IdentityImportError, match="game_id mismatch"):
        import_identity_registry(database, registry, candidate)
    connection = connect_database(database)
    try:
        assert connection.execute("SELECT COUNT(*) FROM countries").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 0
    finally:
        connection.close()


def test_rejects_manifest_checksum_mismatch(tmp_path):
    registry, candidate = write_inputs(tmp_path)
    manifest_path = candidate / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["countries.json"]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(IdentityImportError, match="checksum"):
        import_identity_registry(tmp_path / "canonical.sqlite", registry, candidate)


def test_rejects_conflicting_existing_country_record_and_rolls_back(tmp_path):
    registry, candidate = write_inputs(tmp_path)
    database = tmp_path / "canonical.sqlite"
    connection = connect_database(database)
    try:
        apply_migrations(connection)
        connection.execute(
            """INSERT INTO countries (
                game_id, entity_type, record_status, iso_alpha3, iso_assignment_status,
                localization_status, created_at, updated_at
            ) VALUES (?, 'unreviewed', 'approved', 'AAA', 'unverified', 'unreviewed', 'x', 'x')""",
            ("tc_" + "1" * 32,),
        )
    finally:
        connection.close()
    with pytest.raises(IdentityImportError, match="conflicts"):
        import_identity_registry(database, registry, candidate)
    connection = connect_database(database)
    try:
        assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 0
        assert connection.execute("SELECT record_status FROM countries").fetchone()[0] == "approved"
    finally:
        connection.close()


def test_rejects_duplicate_current_source_ids(tmp_path):
    registry, candidate = write_inputs(tmp_path)
    data = json.loads(registry.read_text())
    data["records"][1]["source"]["current_source_id"] = "AAA"
    registry.write_text(json.dumps(data))
    with pytest.raises(IdentityImportError, match="Duplicate current source ID"):
        import_identity_registry(tmp_path / "canonical.sqlite", registry, candidate)



def test_reads_provenance_from_production_manifest(tmp_path):
    registry, candidate = write_inputs(tmp_path)
    countries_path = candidate / "countries.json"
    countries = json.loads(countries_path.read_text())
    source = countries.pop("source")
    countries_path.write_text(json.dumps(countries), encoding="utf-8")
    manifest_path = candidate / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["source"] = source
    manifest["files"]["countries.json"]["sha256"] = hashlib.sha256(
        countries_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = import_identity_registry(
        tmp_path / "canonical.sqlite", registry, candidate
    )
    assert result["countries"] == 2
