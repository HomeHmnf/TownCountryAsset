import hashlib
import json

import pytest

from tools.database.connection import connect_database
from tools.database.country_data_import import CountryDataImportError, import_country_data
from tools.database.schema import apply_migrations

GAME_ID = "tc_" + "1" * 32
ARCHIVE_SHA = "a" * 64


def make_inputs(tmp_path):
    root = tmp_path / "candidate"
    root.mkdir()
    countries = {
        "schema_version": 1, "count": 1,
        "countries": [{
            "id": "AAA", "game_id": GAME_ID,
            "source_attributes": {
                "text": "value", "integer": 7, "real": 1.25,
                "boolean": True, "json": {"nested": [1, "two"]}, "null": None,
            },
            "source_geometry_type": "Polygon",
        }],
    }
    files = {"countries.json": json.dumps(countries, sort_keys=True, separators=(",", ":")).encode()}
    for profile in ("low", "medium", "high"):
        geometry = {
            "schema_version": 1, "profile": profile, "key": "game_id",
            "geometries": {GAME_ID: {"type": "Point", "coordinates": [1.0, 2.0]}},
        }
        files[f"geometry_game_id_{profile}.json"] = json.dumps(
            geometry, sort_keys=True, separators=(",", ":")
        ).encode()
    for filename, raw in files.items():
        (root / filename).write_bytes(raw)
    source = {
        "archive_sha256": ARCHIVE_SHA, "source_version": "test",
        "url": "https://example.test/source", "retrieval_date": "2026-01-01",
        "attribution": "Fixture", "license": "Public domain",
    }
    manifest = {
        "schema_version": 1, "source": source,
        "files": {name: {"sha256": hashlib.sha256(raw).hexdigest()} for name, raw in files.items()},
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root, source


def seed_database(path, source):
    db = connect_database(path)
    try:
        apply_migrations(db)
        db.execute(
            """INSERT INTO dataset_imports (
                dataset, source_version, source_url, retrieval_date, sha256,
                attribution, license, import_status, imported_at
            ) VALUES ('natural_earth_admin_0', ?, ?, ?, ?, ?, ?, 'candidate', 'now')""",
            (source["source_version"], source["url"], source["retrieval_date"],
             source["archive_sha256"], source["attribution"], source["license"]),
        )
        import_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            """INSERT INTO countries (
                game_id, entity_type, record_status, iso_assignment_status,
                localization_status, created_at, updated_at
            ) VALUES (?, 'unreviewed', 'candidate', 'unverified', 'unreviewed', 'now', 'now')""",
            (GAME_ID,),
        )
        db.execute(
            """INSERT INTO country_sources (game_id, dataset, source_id, is_current, import_id)
               VALUES (?, 'natural_earth_admin_0', 'AAA', 1, ?)""",
            (GAME_ID, import_id),
        )
    finally:
        db.close()


def test_imports_typed_attributes_and_three_geometry_profiles(tmp_path):
    candidate, source = make_inputs(tmp_path)
    database = tmp_path / "canonical.sqlite"
    seed_database(database, source)
    result = import_country_data(database, candidate)
    assert result["countries"] == 1
    assert result["attributes"] == 7
    assert result["geometries"] == 3
    db = connect_database(database)
    try:
        values = {r["attribute_key"]: (r["attribute_value"], r["value_type"])
                  for r in db.execute("SELECT * FROM country_attributes")}
        assert values["text"] == ("value", "text")
        assert values["integer"] == ("7", "integer")
        assert values["real"] == ("1.25", "real")
        assert values["boolean"] == ("true", "boolean")
        assert values["json"] == ('{"nested":[1,"two"]}', "json")
        assert values["null"] == (None, "null")
        assert values["source_geometry_type"] == ("Polygon", "text")
        rows = db.execute("SELECT profile, sha256 FROM country_geometries ORDER BY profile").fetchall()
        assert [r["profile"] for r in rows] == ["high", "low", "medium"]
        assert all(len(r["sha256"]) == 64 for r in rows)
    finally:
        db.close()


def test_repeat_import_is_idempotent(tmp_path):
    candidate, source = make_inputs(tmp_path)
    database = tmp_path / "canonical.sqlite"
    seed_database(database, source)
    assert import_country_data(database, candidate) == import_country_data(database, candidate)


def test_rejects_changed_file_checksum_without_writing(tmp_path):
    candidate, source = make_inputs(tmp_path)
    database = tmp_path / "canonical.sqlite"
    seed_database(database, source)
    path = candidate / "geometry_game_id_low.json"
    path.write_text(path.read_text() + " ", encoding="utf-8")
    with pytest.raises(CountryDataImportError, match="checksum"):
        import_country_data(database, candidate)
    db = connect_database(database)
    try:
        assert db.execute("SELECT COUNT(*) FROM country_attributes").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM country_geometries").fetchone()[0] == 0
    finally:
        db.close()


def test_rejects_geometry_coverage_mismatch(tmp_path):
    candidate, source = make_inputs(tmp_path)
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


def test_rejects_conflicting_attribute_and_rolls_back_geometry(tmp_path):
    candidate, source = make_inputs(tmp_path)
    database = tmp_path / "canonical.sqlite"
    seed_database(database, source)
    db = connect_database(database)
    try:
        db.execute(
            """INSERT INTO country_attributes (game_id, attribute_key, attribute_value, value_type)
               VALUES (?, 'text', 'different', 'text')""", (GAME_ID,)
        )
    finally:
        db.close()
    with pytest.raises(CountryDataImportError, match="attribute conflicts"):
        import_country_data(database, candidate)
    db = connect_database(database)
    try:
        assert db.execute("SELECT COUNT(*) FROM country_geometries").fetchone()[0] == 0
    finally:
        db.close()


def test_rejects_candidate_identity_mismatch(tmp_path):
    candidate, source = make_inputs(tmp_path)
    database = tmp_path / "canonical.sqlite"
    seed_database(database, source)
    manifest_path = candidate / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    countries_path = candidate / "countries.json"
    countries = json.loads(countries_path.read_text())
    replacement_id = "tc_" + "2" * 32
    countries["countries"][0]["game_id"] = replacement_id
    raw = json.dumps(countries, sort_keys=True, separators=(",", ":")).encode()
    countries_path.write_bytes(raw)
    manifest["files"]["countries.json"]["sha256"] = hashlib.sha256(raw).hexdigest()

    for profile in ("low", "medium", "high"):
        geometry_path = candidate / f"geometry_game_id_{profile}.json"
        geometry = json.loads(geometry_path.read_text())
        geometry["geometries"][replacement_id] = geometry["geometries"].pop(GAME_ID)
        geometry_raw = json.dumps(geometry, sort_keys=True, separators=(",", ":")).encode()
        geometry_path.write_bytes(geometry_raw)
        manifest["files"][geometry_path.name]["sha256"] = hashlib.sha256(geometry_raw).hexdigest()

    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(CountryDataImportError, match="identity coverage mismatch"):
        import_country_data(database, candidate)
