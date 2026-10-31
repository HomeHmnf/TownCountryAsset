from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

from tools.database.connection import connect_database
from tools.database.schema import apply_migrations
from tools.database.statistics_import import StatisticsImportError, import_wp1_5_dataset

GAME = "tc_" + "a" * 32
SOURCE = "un_wpp_2024"


def setup_inputs(tmp_path, *, field_id=1, value=1234, status="observed", source_key=SOURCE):
    tmp_path.mkdir(parents=True, exist_ok=True)
    raw = tmp_path / "provider.csv"
    raw.write_text("provider,captured\n", encoding="utf-8")
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    manifest = {
        "manifest_schema_version": 1, "work_package": "WP1.5",
        "source_key": source_key, "release": "2024-r1",
        "source_url": "https://example.test/source.csv",
        "final_url": "https://example.test/source.csv",
        "retrieved_at": "2026-10-31T10:00:00Z",
        "local_raw_path": str(raw), "sha256": digest,
        "attribution": "Example attribution", "license_status": "unclear_or_unverified",
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    crosswalk = {
        "schema_version": 1, "dataset": source_key, "source_key": source_key,
        "mappings": [{
            "game_id": GAME, "source_id": "provider-1",
            "match_method": "authoritative_identifier",
            "evidence_url": "https://example.test/country/provider-1",
        }],
    }
    crosswalk_path = tmp_path / "crosswalk.json"
    crosswalk_path.write_text(json.dumps(crosswalk), encoding="utf-8")
    observations = {
        "schema_version": 1, "work_package": "WP1.5", "source_key": source_key,
        "release": manifest["release"], "source_sha256": digest,
        "observations": [{
            "game_id": GAME, "source_id": "provider-1", "field_id": field_id,
            "value": value, "value_status": status, "observation_period": "2024",
            "unit": "people", "methodology": "provider reported",
        }],
    }
    observations_path = tmp_path / "normalized.json"
    observations_path.write_text(json.dumps(observations), encoding="utf-8")
    return observations_path, crosswalk_path, manifest_path


def setup_database(path):
    connection = connect_database(path)
    apply_migrations(connection)
    connection.execute(
        """INSERT INTO countries (game_id, created_at, updated_at)
           VALUES (?, '2026-10-31T00:00:00Z', '2026-10-31T00:00:00Z')""",
        (GAME,),
    )
    connection.close()


def run_import(tmp_path, database, **kwargs):
    observations, crosswalk, manifest = setup_inputs(tmp_path, **kwargs)
    return import_wp1_5_dataset(
        observations_path=observations, crosswalk_path=crosswalk,
        manifest_path=manifest, database_path=database,
    )


def test_imports_scalar_observation_with_provenance_and_is_idempotent(tmp_path):
    database = tmp_path / "canonical.sqlite"
    setup_database(database)
    result = run_import(tmp_path, database)
    assert result["scalar_observations"] == 1
    assert result["integrity"] == result["foreign_keys"] == "ok"
    repeated = import_wp1_5_dataset(
        observations_path=tmp_path / "normalized.json",
        crosswalk_path=tmp_path / "crosswalk.json",
        manifest_path=tmp_path / "manifest.json",
        database_path=database,
    )
    assert repeated["import_id"] == result["import_id"]
    connection = sqlite3.connect(database)
    row = connection.execute(
        "SELECT value, observation_period, source_version, value_status FROM current_statistics"
    ).fetchone()
    assert row == (1234.0, "2024", "2024-r1", "observed")
    connection.close()


def test_imports_structured_data_and_explicit_null_scalar(tmp_path):
    database = tmp_path / "canonical.sqlite"
    setup_database(database)
    result = run_import(tmp_path, database, field_id=12, value={"0-4": 100, "5-9": 90})
    assert result["structured_observations"] == 1
    connection = sqlite3.connect(database)
    payload = json.loads(connection.execute("SELECT payload_json FROM selected_game_data").fetchone()[0])
    assert payload == {"unit": "people", "value": {"0-4": 100, "5-9": 90}}
    connection.close()

    # A second source record is not silently synthesized; this explicit null uses a valid status.
    null_result = run_import(tmp_path / "nullcase", database, field_id=1, value=None, status="unavailable")
    assert null_result["scalar_observations"] == 1


def test_rejects_source_field_mismatch_and_invalid_null_status(tmp_path):
    database = tmp_path / "canonical.sqlite"
    setup_database(database)
    with pytest.raises(StatisticsImportError, match="not the contracted primary source"):
        run_import(tmp_path, database, field_id=15)
    with pytest.raises(StatisticsImportError, match="NULL value requires"):
        run_import(tmp_path / "nullcase", database, value=None)


def test_rejects_checksum_mismatch_and_crosswalk_pair_mismatch(tmp_path):
    database = tmp_path / "canonical.sqlite"
    setup_database(database)
    observations, crosswalk, manifest = setup_inputs(tmp_path)
    manifest_data = json.loads(manifest.read_text())
    manifest_data["sha256"] = "0" * 64
    manifest.write_text(json.dumps(manifest_data))
    with pytest.raises(StatisticsImportError, match="checksum"):
        import_wp1_5_dataset(observations_path=observations, crosswalk_path=crosswalk, manifest_path=manifest, database_path=database)

    setup_inputs(tmp_path / "paircase")
    pair_dir = tmp_path / "paircase"
    observations_data = json.loads((pair_dir / "normalized.json").read_text())
    observations_data["observations"][0]["source_id"] = "wrong-id"
    (pair_dir / "normalized.json").write_text(json.dumps(observations_data))
    with pytest.raises(StatisticsImportError, match="absent from the explicit crosswalk"):
        import_wp1_5_dataset(
            observations_path=pair_dir / "normalized.json",
            crosswalk_path=pair_dir / "crosswalk.json",
            manifest_path=pair_dir / "manifest.json",
            database_path=database,
        )


def test_rejects_duplicate_country_field_rows_without_writes(tmp_path):
    database = tmp_path / "canonical.sqlite"
    setup_database(database)
    observations, crosswalk, manifest = setup_inputs(tmp_path)
    payload = json.loads(observations.read_text())
    payload["observations"].append(dict(payload["observations"][0]))
    observations.write_text(json.dumps(payload))
    with pytest.raises(StatisticsImportError, match="Duplicate country/field"):
        import_wp1_5_dataset(observations_path=observations, crosswalk_path=crosswalk, manifest_path=manifest, database_path=database)
    connection = sqlite3.connect(database)
    assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 0
    connection.close()



def test_rejects_conflict_from_a_different_source_and_rolls_back(tmp_path):
    database = tmp_path / "canonical.sqlite"
    setup_database(database)
    connection = sqlite3.connect(database)
    connection.execute(
        """INSERT INTO dataset_imports
           (dataset, source_version, source_url, retrieval_date, sha256, import_status, imported_at)
           VALUES ('different_source', 'v1', 'https://example.test/old', '2025-01-01T00:00:00Z',
                   ?, 'candidate', '2025-01-01T00:00:00Z')""",
        ("1" * 64,),
    )
    import_id = connection.execute("SELECT import_id FROM dataset_imports").fetchone()[0]
    connection.execute(
        """INSERT INTO current_statistics
           (game_id, statistic_key, value, unit, observed_at, observation_period,
            value_status, source_reference, source_version, retrieved_at, import_id)
           VALUES (?, 'population', 10, 'people', '2025', '2025', 'observed',
                   'https://example.test/old', 'v1', '2025-01-01T00:00:00Z', ?)""",
        (GAME, import_id),
    )
    connection.commit()
    connection.close()
    with pytest.raises(StatisticsImportError, match="conflicts with a different source"):
        run_import(tmp_path, database)
    connection = sqlite3.connect(database)
    assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 1
    assert connection.execute("SELECT value FROM current_statistics").fetchone()[0] == 10
    connection.close()
