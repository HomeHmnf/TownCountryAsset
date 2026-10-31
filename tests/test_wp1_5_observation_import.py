from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

import tools.database.statistics_import as importer
from tools.database.schema import apply_migrations
from tools.database.statistics_import import StatisticsImportError, import_wp1_5_dataset

GAME_A = "tc_" + "a" * 32
GAME_B = "tc_" + "b" * 32


def _database(tmp_path):
    path = tmp_path / "canonical.sqlite"
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    apply_migrations(connection)
    connection.executemany(
        "INSERT INTO countries(game_id, created_at, updated_at) VALUES (?, 'now', 'now')",
        [(GAME_A,), (GAME_B,)],
    )
    connection.commit()
    connection.close()
    return path


def _inputs(tmp_path, monkeypatch, *, field_id=1, value=1234000, status="projected"):
    monkeypatch.setattr(importer, "REPOSITORY_ROOT", tmp_path)
    raw = tmp_path / "raw_data" / "wp1_5" / "un_wpp_2024" / "2024-test" / "wpp.csv"
    raw.parent.mkdir(parents=True)
    raw.write_text("Location,Value\n4,1234\n", encoding="utf-8")
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    manifest = {
        "manifest_schema_version": 1,
        "work_package": "WP1.5",
        "source_key": "un_wpp_2024",
        "release": "2024-test",
        "source_url": "https://population.un.org/wpp/test.csv",
        "final_url": "https://population.un.org/wpp/test.csv",
        "terms_url": "https://population.un.org/wpp/",
        "attribution": "United Nations",
        "license_status": "CC BY 3.0 IGO",
        "retrieved_at": "2026-10-31T10:00:00Z",
        "filename": "wpp.csv",
        "local_raw_path": str(raw),
        "content_type": "text/csv",
        "byte_count": raw.stat().st_size,
        "sha256": digest,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    crosswalk = {
        "schema_version": 1,
        "dataset": "un_wpp_2024",
        "source_key": "un_wpp_2024",
        "mappings": [
            {"game_id": GAME_A, "source_id": "4", "match_method": "authoritative_identifier"},
            {"game_id": GAME_B, "source_id": "5", "match_method": "authoritative_identifier"},
        ],
    }
    crosswalk_path = tmp_path / "crosswalk.json"
    crosswalk_path.write_text(json.dumps(crosswalk), encoding="utf-8")
    field = {1: ("people", 1234000), 12: ("age_band_share_or_count", [{"age_band": "0-4", "sex": "both", "people": 1000}])}
    unit, default_value = field[field_id]
    observation = {
        "game_id": GAME_A,
        "source_id": "4",
        "field_id": field_id,
        "value": default_value if value == "default" else value,
        "unit": unit,
        "value_status": status,
        "observation_period": "2026",
        "source_reference": "WPP2024:2026",
    }
    batch = {
        "schema_version": 1,
        "work_package": "WP1.5",
        "source_key": "un_wpp_2024",
        "release": "2024-test",
        "source_sha256": digest,
        "observations": [observation],
    }
    batch_path = tmp_path / "observations.json"
    batch_path.write_text(json.dumps(batch), encoding="utf-8")
    return path, batch_path, crosswalk_path, manifest_path, observation


def _run(paths, **kwargs):
    database, batch, crosswalk, manifest, _ = paths
    return import_wp1_5_dataset(
        observations_path=batch,
        crosswalk_path=crosswalk,
        manifest_path=manifest,
        database_path=database,
        **kwargs,
    )


def _connect(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def test_imports_scalar_provenance_and_is_idempotent(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    first = _run(paths)
    assert first["scalar_observations"] == 1
    assert first["observations"] == 1
    with _connect(paths[0]) as connection:
        row = connection.execute("SELECT * FROM current_statistics").fetchone()
        assert row["value"] == 1234000
        assert row["value_status"] == "projected"
        assert row["observation_period"] == "2026"
        assert row["source_version"] == "2024-test"
        assert connection.execute("SELECT COUNT(*) FROM country_sources WHERE dataset='un_wpp_2024'").fetchone()[0] == 2
    second = _run(paths)
    assert second["import_id"] == first["import_id"]
    assert second["observations"] == 1


def test_imports_structured_observation(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch, field_id=12, value="default")
    result = _run(paths)
    assert result["structured_observations"] == 1
    with _connect(paths[0]) as connection:
        row = connection.execute("SELECT * FROM selected_game_data").fetchone()
        payload = json.loads(row["payload_json"])
        assert payload["unit"] == "age_band_share_or_count"
        assert payload["value"][0]["age_band"] == "0-4"


def test_explicit_unavailable_null_is_preserved(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch, value=None, status="unavailable")
    result = _run(paths)
    assert result["scalar_observations"] == 1
    with _connect(paths[0]) as connection:
        row = connection.execute("SELECT value, value_status FROM current_statistics").fetchone()
        assert row["value"] is None
        assert row["value_status"] == "unavailable"


def test_rejects_primary_source_mismatch_before_writes(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    batch = json.loads(paths[1].read_text(encoding="utf-8"))
    batch["observations"][0]["field_id"] = 15
    paths[1].write_text(json.dumps(batch), encoding="utf-8")
    with pytest.raises(StatisticsImportError, match="not the contracted primary source"):
        _run(paths)
    with _connect(paths[0]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM current_statistics").fetchone()[0] == 0


def test_rejects_tampered_raw_snapshot(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    raw = tmp_path / "raw_data" / "wp1_5" / "un_wpp_2024" / "2024-test" / "wpp.csv"
    raw.write_text("tampered", encoding="utf-8")
    with pytest.raises(StatisticsImportError, match="checksum"):
        _run(paths)
    with _connect(paths[0]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 0


def test_conflicting_same_release_batch_rolls_back(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    _run(paths)
    batch = json.loads(paths[1].read_text(encoding="utf-8"))
    batch["observations"][0]["value"] = 987
    paths[1].write_text(json.dumps(batch), encoding="utf-8")
    with pytest.raises(StatisticsImportError, match="Refusing non-newer"):
        _run(paths)
    with _connect(paths[0]) as connection:
        row = connection.execute("SELECT value FROM current_statistics").fetchone()
        assert row["value"] == 1234000
        assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 1
