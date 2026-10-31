import hashlib
import json
import sqlite3

import pytest

from tools.database.connection import connect_database
from tools.database.country_data_import import CountryDataImportError, import_country_data
from tools.database.schema import apply_migrations


ARCHIVE_SHA = "a" * 64
GAME_ID = "tc_" + "1" * 32


def write_candidate(tmp_path):
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    countries = {
        "schema_version": 1,
        "count": 1,
        "countries": [{
            "id": "AAA",
            "game_id": GAME_ID,
            "source_attributes": {
                "text": "value",
                "integer": 7,
                "real": 1.25,
                "boolean": True,
                "json": {"nested": [1, "two"]},
                "null": None,
            },
            "source_geometry_type": "Polygon",
        }],
    }
    files = {"countries.json": json.dumps(countries, sort_keys=True, separators=(",", ":")).encode()}
    for profile in ("low", "medium", "high"):
        payload = {
            "schema_version": 1,
            "profile": profile,
            "key": "game_id",
            "geometries": {
                GAME_ID: {"type": "Point", "coordinates": [float(len(profile)), 2.0]}
            },
        }
        files[f"geometry_game_id_{profile}.json"] = json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode()
    for name, raw in files.items():
        (candidate / name).write_bytes(raw)
    source = {
        "archive_sha256": ARCHIVE_SHA,
        "source_version": "test",
        "url": "https://example.test/natural-earth",
        "retrieval_date": "2026-01-01",
        "attribution": "Fixture",
        "license": "Public domain",
    }
    manifest = {
        "schema_version": 1,
        "source": source,
        "files": {
            name: {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
            for name, raw in files.items()
        },
    }
    (candidate / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return candidate, source


def seed_database(path, source):
    connection = connect_database(path)
    try:
        apply_migrations(connection)
        connection.execute(
            """INSERT INTO dataset_imports (
                dataset, source_version, source_url, retrieval_date, sha256,
                attribution, license, import_status, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'candidate', 'now')""",
            (
                "natural_earth_admin_0", source["source_version"], source["url"],
                source["retrieval_date"], source["archive_sha256"],
                source["attribution"], source["license"],
            ),
        )
        import_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            """INSERT INTO countries (
                game_id, entity_type, record_status, iso_assignment_status,
                localization_status, created_at, updated_at
            ) VALUES (?, 'unreviewed', 'candidate', 'unverified', 'unreviewed', 'now', 'now')""",
            (GAME_ID,),
        )
        connection.execute(
            """INSERT INTO country_sources (game_id, dataset, source_id, is_current, import_id)
               VALUES (?, 'natural_earth_admin_0', 'AAA', 1, ?)""",
            (GAME_ID, import_id),
        )
    finally:
        connection.close()


def test_imports_typed_attributes_and_all_geometry_profiles(tmp_path):
    candidate, source = write_candidate(tmp_path)
    database = tmp_path / "canonical.sqlite"
    seed_database(database, source)

    result = import_country_data(database, candidate)

    assert result == {
        "dataset": "natural_earth_admin_0",
        "import_id": 1,
        "countries": 1,
        "attributes": 7,
        "geometry_profiles": 3,
        "geometries": 3,
    }
    connection = connect_database(database)
    try:
        values = {
            row["attribute_key"]: (row["attribute_value"], row["value_type"])
            for row in connection.execute("SELECT * FROM country_attributes")
        }
        assert values["text"] == ("value", "text")
        assert values["integer"] == ("7", "integer")
        assert values["real"] == ("1.25", "real")
        assert values["boolean"] == ("true", "boolean")
        assert values["json"] == ('{"nested":[1,"two"]}', "json")
        assert values["null"] == (None, "null")
        assert values["source_geometry_type"] == ("Polygon", "text")
        geometries = connection.execute(
            "SELECT profile, sha256, import_id FROM country_geometries ORDER BY profile"
        ).fetchall()
        assert [row["profile"] for row in geometries] == ["high", "low", "medium"]
        assert all(len(row["sha256"]) == 64 and row["import_id"] == 1 for row in geometries)
    finally:
        connection.close()


def test_repeat_import_is_idempotent(tmp_path):
    candidate, source = write_candidate(tmp_path)
    database = tmp_path / "canonical.sqlite"
    seed_database(database, source)
    first = import_country_data(database, candidate)
    second = import_country_data(database, candidate)
    assert first == second


def test_rejects_modified_geometry_manifest_checksum(tmp_path):
    candidate, source = write_candidate(tmp_path)
    database = tmp_path / "canonical.sqlite"
    seed_database(database, source)
    geometry_path = candidate / "geometry_game_id_low.json"
    geometry_path.write_text(geometry_path.read_text() + " ", encoding="utf-8")
    with pytest.raises(CountryDataImportError, match="checksum"):
        import_country_data(database, candidate)
    connection = connect_database(database)
    try:
        assert connection.execute("SELECT COUNT(*) FROM country_attributes").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM country_geometries").fetchone()[0] == 0
    finally:
        connection.close()


def test_rejects_geometry_identity_coverage_mismatch(tmp_path):
    candidate, source = write_candidate(tmp_path)
    database = tmp_path / "canonical.sqlite"
    seed_database(database, source)
    path = candidate / "geometry_game_id_high.json"
    payload = json.loads(path.read_text())
    payload["geometries"] = {}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(raw)
    manifest_path = candidate / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["geometry_game_id_high.json"]["sha256"] = hashlib.sha256(raw).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(CountryDataImportError, match="coverage mismatch"):
        import_country_data(database, candidate)


def test_rejects_conflicting_existing_attribute_and_rolls_back(tmp_path):
    candidate, source = write_candidate(tmp_path)
    database = tmp_path / "canonical.sqlite"
    seed_database(database, source)
    connection = connect_database(database)
    try:
        connection.execute(
            "INSERT INTO country_attributes (game_id, attribute_key, attribute_value, value_type) VALUES (?, 'text', 'different', 'text')",
            (GAME_ID,),
        )
    finally:
        connection.close()
    with pytest.raises(CountryDataImportError, match="attribute conflicts"):
        import_country_data(database, candidate)
    connection = connect_database(database)
    try:
        assert connection.execute("SELECT COUNT(*) FROM country_geometries").fetchone()[0] == 0
        assert connection.execute("SELECT attribute_value FROM country_attributes WHERE attribute_key='text'").fetchone()[0] == "different"
    finally:
        connection.close()


def test_rejects_candidate_database_identity_mismatch(tmp_path):
    candidate, source = write_candidate(tmp_path)
    database = tmp_path / "canonical.sqlite"
    seed_database(database, source)
    path = candidate / "countries.json"
    payload = json.loads(path.read_text())
    payload["countries"][0]["game_id"] = "tc_" + "2" * 32
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(raw)
    manifest_path = candidate / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["countries.json"]["sha256"] = hashlib.sha256(raw).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(CountryDataImportError, match="identity coverage mismatch"):
        import_country_data(database, candidate)
