from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.database.connection import connect_database
from tools.database.game_data_import import GameDataImportError, import_normalized_batch
from tools.database.schema import apply_migrations

ROOT = Path(__file__).resolve().parents[1]
G1 = "tc_" + "1" * 32
G2 = "tc_" + "2" * 32


def setup_inputs(tmp_path, connection, observations, *, source_key="un_wpp_2024", release="2024"):
    raw = tmp_path / "provider.csv"
    raw.write_text("source_id,value\n4,100\n", encoding="utf-8")
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    retrieved = "2026-10-31T10:00:00Z"
    manifest = {
        "manifest_schema_version": 1,
        "work_package": "WP1.5",
        "source_key": source_key,
        "source_name": "UN WPP",
        "release": release,
        "source_url": "https://population.un.org/wpp/file.csv",
        "final_url": "https://population.un.org/wpp/file.csv",
        "terms_url": "https://population.un.org/wpp/",
        "attribution": "UN DESA",
        "license_status": "CC BY 3.0 IGO",
        "retrieved_at": retrieved,
        "filename": "provider.csv",
        "local_raw_path": str(raw),
        "content_type": "text/csv",
        "byte_count": raw.stat().st_size,
        "sha256": digest,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    crosswalk_path = tmp_path / "crosswalk.json"
    crosswalk_path.write_text(json.dumps({
        "schema_version": 1,
        "dataset": source_key,
        "source_key": source_key,
        "mappings": [
            {"game_id": G1, "source_id": "4", "match_method": "authoritative_identifier"},
            {"game_id": G2, "source_id": "5", "match_method": "reviewed_manual"},
        ],
    }), encoding="utf-8")
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(json.dumps({
        "schema_version": 1,
        "source_key": source_key,
        "release": release,
        "observations": observations,
    }), encoding="utf-8")
    return batch_path, manifest_path, crosswalk_path


def seed_database(tmp_path):
    connection = connect_database(tmp_path / "test.sqlite")
    apply_migrations(connection)
    connection.execute(
        "INSERT INTO countries(game_id, created_at, updated_at) VALUES (?, 'now', 'now'), (?, 'now', 'now')",
        (G1, G2),
    )
    return connection


def scalar(source_id="4", key="population", value=100000, status="observed"):
    return {
        "source_id": source_id,
        "field_key": key,
        "value": value,
        "value_status": status,
        "unit": "people",
        "observation_period": "2026-07-01",
        "source_reference": "WPP2024:population",
        "methodology": "Converted from thousands to people",
    }


def invoke(connection, paths):
    batch, manifest, crosswalk = paths
    return import_normalized_batch(
        connection,
        batch_path=batch,
        manifest_path=manifest,
        crosswalk_path=crosswalk,
        config_path=ROOT / "config" / "wp1_5_data_sources.json",
    )


def test_imports_scalar_and_structured_rows_transactionally(tmp_path):
    connection = seed_database(tmp_path)
    paths = setup_inputs(tmp_path, connection, [
        scalar(),
        {
            "source_id": "5",
            "field_key": "age_distribution",
            "value": [{"age_band": "0-4", "sex": "both", "people": 1200}],
            "value_status": "projected",
            "unit": "age_band_share_or_count",
            "observation_period": "2026",
            "source_reference": "WPP2024:age",
            "methodology": "Source counts converted to people",
        },
    ])
    result = invoke(connection, paths)
    assert (result.scalar_rows, result.structured_rows, result.idempotent) == (1, 1, False)
    assert connection.execute("SELECT value, value_status FROM current_statistics").fetchone() == (100000.0, "observed")
    structured = connection.execute("SELECT payload_json, value_status FROM selected_game_data").fetchone()
    assert json.loads(structured["payload_json"])[0]["age_band"] == "0-4"
    assert structured["value_status"] == "projected"
    assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 1
    connection.close()


def test_explicit_unavailable_scalar_is_stored_as_null(tmp_path):
    connection = seed_database(tmp_path)
    paths = setup_inputs(tmp_path, connection, [
        scalar(value=None, status="unavailable"),
    ])
    invoke(connection, paths)
    row = connection.execute("SELECT value, value_status FROM current_statistics").fetchone()
    assert row["value"] is None
    assert row["value_status"] == "unavailable"
    connection.close()


def test_identical_import_is_idempotent(tmp_path):
    connection = seed_database(tmp_path)
    paths = setup_inputs(tmp_path, connection, [scalar()])
    first = invoke(connection, paths)
    second = invoke(connection, paths)
    assert first.idempotent is False
    assert second.idempotent is True
    assert first.import_id == second.import_id
    assert connection.execute("SELECT COUNT(*) FROM current_statistics").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 1
    connection.close()


@pytest.mark.parametrize("bad_row, message", [
    ({**scalar(), "field_key": "gdp"}, "assigned to"),
    ({**scalar(), "value": float("nan")}, "finite number"),
    ({**scalar(), "value": None, "value_status": "observed"}, "NULL scalar"),
    ({**scalar(), "unit": ""}, "canonical unit"),
    ({**scalar(), "observation_period": ""}, "observation_period"),
    ({**scalar(), "source_reference": ""}, "source_reference"),
])
def test_rejects_invalid_observations_before_writes(tmp_path, bad_row, message):
    connection = seed_database(tmp_path)
    paths = setup_inputs(tmp_path, connection, [bad_row])
    with pytest.raises(GameDataImportError, match=message):
        invoke(connection, paths)
    assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM current_statistics").fetchone()[0] == 0
    connection.close()


def test_rejects_manifest_checksum_mismatch(tmp_path):
    connection = seed_database(tmp_path)
    paths = setup_inputs(tmp_path, connection, [scalar()])
    batch, manifest, crosswalk = paths
    payload = json.loads(manifest.read_text())
    payload["sha256"] = "0" * 64
    manifest.write_text(json.dumps(payload))
    with pytest.raises(GameDataImportError, match="checksum"):
        invoke(connection, paths)
    assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 0
    connection.close()


def test_rejects_unmapped_provider_id_and_rolls_back_duplicate_key_conflict(tmp_path):
    connection = seed_database(tmp_path)
    paths = setup_inputs(tmp_path, connection, [scalar(source_id="missing")])
    with pytest.raises(GameDataImportError, match="crosswalk"):
        invoke(connection, paths)
    assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 0

    paths = setup_inputs(tmp_path, connection, [scalar()], release="2025")
    connection.execute(
        "INSERT INTO current_statistics(game_id, statistic_key, value, unit, value_status) VALUES (?, 'population', 1, 'people', 'observed')",
        (G1,),
    )
    with pytest.raises(GameDataImportError, match="Database rejected"):
        invoke(connection, paths)
    assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 0
    assert connection.execute("SELECT value FROM current_statistics WHERE game_id = ?", (G1,)).fetchone()[0] == 1.0
    connection.close()


def test_rejects_repeated_game_field_in_batch(tmp_path):
    connection = seed_database(tmp_path)
    paths = setup_inputs(tmp_path, connection, [scalar(), scalar(value=200000)])
    with pytest.raises(GameDataImportError, match="Duplicate observation"):
        invoke(connection, paths)
    assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 0
    connection.close()
