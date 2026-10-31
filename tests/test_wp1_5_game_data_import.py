from __future__ import annotations

import json

import pytest

from tools.database.connection import connect_database
from tools.database.game_data_import import GameDataImportError, import_wp1_5_snapshot
from tools.database.schema import apply_migrations

G1 = "tc_" + "1" * 32
G2 = "tc_" + "2" * 32
SHA = "a" * 64


@pytest.fixture
def database(tmp_path):
    connection = connect_database(tmp_path / "test.sqlite")
    apply_migrations(connection)
    for gid in (G1, G2):
        connection.execute(
            "INSERT INTO countries(game_id,created_at,updated_at) VALUES(?,'2026-10-31T00:00:00Z','2026-10-31T00:00:00Z')",
            (gid,),
        )
    yield connection
    connection.close()


@pytest.fixture
def inputs(tmp_path):
    contract = tmp_path / "contract.json"
    contract.write_text(json.dumps({
        "schema_version": 1,
        "sources": {"un_wpp_2024": {"name": "WPP"}},
        "fields": [
            {"id": 1, "key": "population", "storage": "scalar", "unit": "people", "primary_source": "un_wpp_2024"},
            {"id": 12, "key": "age_distribution", "storage": "structured", "unit": "age_bands", "primary_source": "un_wpp_2024"},
            {"id": 48, "key": "religions", "storage": "structured", "unit": "shares", "primary_source": "pew_religion_2020"}
        ]
    }), encoding="utf-8")
    crosswalk = tmp_path / "crosswalk.json"
    crosswalk.write_text(json.dumps({
        "schema_version": 1, "dataset": "un_wpp_2024", "source_key": "un_wpp_2024",
        "mappings": [
            {"game_id": G1, "source_id": "4", "match_method": "authoritative_identifier"},
            {"game_id": G2, "source_id": "8", "match_method": "reviewed_manual"}
        ]
    }), encoding="utf-8")
    raw = tmp_path / "wpp.csv"
    raw.write_bytes(b"source-id,population\\n4,41000000\\n8,35000000\\n")
    import hashlib
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "manifest_schema_version": 1, "work_package": "WP1.5",
        "source_key": "un_wpp_2024", "release": "WPP2024",
        "source_url": "https://population.un.org/wpp/",
        "final_url": "https://population.un.org/wpp/data/wpp.csv",
        "retrieved_at": "2026-10-31T10:00:00Z",
        "local_raw_path": str(raw), "byte_count": raw.stat().st_size,
        "sha256": digest, "attribution": "UN DESA", "license_status": "unclear_or_unverified"
    }), encoding="utf-8")
    return contract, crosswalk, manifest, raw


def scalar(value=41000000, source_id="4"):
    return {
        "source_id": source_id, "field_key": "population", "value": value,
        "observation_period": "2025", "value_status": "estimated",
        "observed_at": "2025-07-01T00:00:00Z"
    }


def call(database, inputs, observations):
    return import_wp1_5_snapshot(
        database, manifest_path=inputs[2], crosswalk_path=inputs[1],
        observations=observations, contract_path=inputs[0]
    )


def test_imports_scalar_and_structured_data_with_provenance(database, inputs):
    result = call(database, inputs, [
        scalar(),
        {"source_id": "8", "field_key": "age_distribution",
         "value": [{"age_group": "0-4", "count": 500000}],
         "observation_period": "2025", "value_status": "projected"}
    ])
    assert result == {
        "import_id": 1, "country_mappings": 2, "observations": 2,
        "inserted_observations": 2, "idempotent": False
    }
    row = database.execute(
        "SELECT value,value_status,observation_period,source_version FROM current_statistics"
    ).fetchone()
    assert tuple(row) == (41000000.0, "estimated", "2025", "WPP2024")
    row = database.execute(
        "SELECT payload_json,value_status,data_key FROM selected_game_data"
    ).fetchone()
    assert tuple(row) == ('[{"age_group":"0-4","count":500000}]', "projected", "age_distribution")


def test_repeat_is_idempotent_and_changed_value_conflicts(database, inputs):
    assert call(database, inputs, [scalar()])["inserted_observations"] == 1
    assert call(database, inputs, [scalar()])["inserted_observations"] == 0
    with pytest.raises(GameDataImportError, match="Conflicting scalar"):
        call(database, inputs, [scalar(value=42000000)])


def test_rejects_source_mismatch_and_unmapped_id(database, inputs):
    with pytest.raises(GameDataImportError, match="assigned to another source"):
        call(database, inputs, [{
            "source_id": "4", "field_key": "religions", "value": {"x": 1},
            "observation_period": "2020"
        }])
    with pytest.raises(GameDataImportError, match="absent from explicit crosswalk"):
        call(database, inputs, [scalar(source_id="999")])


def test_rejects_null_status_nonfinite_and_duplicate_rows(database, inputs):
    with pytest.raises(GameDataImportError, match="null scalar"):
        call(database, inputs, [scalar(value=None)])
    with pytest.raises(GameDataImportError, match="finite numeric"):
        call(database, inputs, [scalar(value=float("nan"))])
    with pytest.raises(GameDataImportError, match="Duplicate observation"):
        call(database, inputs, [scalar(), scalar()])


def test_rejects_new_release_without_replacement_policy(database, inputs):
    call(database, inputs, [scalar()])
    manifest = json.loads(inputs[2].read_text(encoding="utf-8"))
    manifest["release"] = "WPP2025"
    manifest["sha256"] = "b" * 64
    inputs[2].write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(GameDataImportError, match="Raw snapshot SHA-256"):
        call(database, inputs, [scalar()])
    assert database.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 1


def test_unknown_crosswalk_identity_fails_before_writes(database, inputs):
    inputs[1].write_text(json.dumps({
        "schema_version": 1, "dataset": "un_wpp_2024", "source_key": "un_wpp_2024",
        "mappings": [{"game_id": "tc_" + "f" * 32, "source_id": "4", "match_method": "reviewed_manual"}]
    }), encoding="utf-8")
    with pytest.raises(GameDataImportError, match="absent from"):
        call(database, inputs, [scalar()])
    assert database.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 0


def test_rejects_raw_snapshot_checksum_tampering(database, inputs):
    inputs[3].write_bytes(b"tampered")
    with pytest.raises(GameDataImportError, match="SHA-256 does not match"):
        call(database, inputs, [scalar()])
    assert database.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 0
