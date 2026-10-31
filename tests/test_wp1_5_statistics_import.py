from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

from tools.database.connection import connect_database
from tools.database.schema import apply_migrations
import tools.database.statistics_import as statistics_import
from tools.database.statistics_import import StatisticsImportError, import_wp1_5_dataset

GAME = "tc_" + "a" * 32
GAME_B = "tc_" + "b" * 32
SOURCE = "un_wpp_2024"

@pytest.fixture(autouse=True)
def repository_root_for_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(statistics_import, "REPOSITORY_ROOT", tmp_path)


def setup_inputs(tmp_path, *, field_id=1, value=1234, status="observed", source_key=SOURCE, release="2024-r1"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    raw = tmp_path / "raw_data" / "wp1_5" / source_key / release / "provider.csv"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("provider,captured\n" + release + "\n", encoding="utf-8")
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    manifest = {
        "manifest_schema_version": 1, "work_package": "WP1.5",
        "source_key": source_key, "release": release,
        "source_url": "https://example.test/source.csv",
        "final_url": "https://example.test/source.csv",
        "retrieved_at": "2026-10-31T10:00:00Z",
        "local_raw_path": str(raw), "byte_count": raw.stat().st_size, "sha256": digest,
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
        }, {
            "game_id": GAME_B, "source_id": "provider-2",
            "match_method": "reviewed_manual",
            "evidence_url": "https://example.test/country/provider-2",
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
            "unit": "people" if field_id == 1 else "age_band_share", "methodology": "provider reported",
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
           VALUES (?, '2026-10-31T00:00:00Z', '2026-10-31T00:00:00Z'),
                  (?, '2026-10-31T00:00:00Z', '2026-10-31T00:00:00Z')""",
        (GAME, GAME_B),
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
    assert result["idempotent"] is False
    assert repeated["idempotent"] is True
    connection = sqlite3.connect(database)
    row = connection.execute(
        "SELECT value, observed_at, observation_period, source_version, value_status, methodology FROM current_statistics"
    ).fetchone()
    assert row == (1234.0, None, "2024", "2024-r1", "observed", "provider reported")
    assert connection.execute("SELECT game_id, dataset, source_id, is_current FROM country_sources").fetchone() == (GAME, SOURCE, "provider-1", 1)
    connection.close()


def test_imports_structured_data_and_explicit_null_scalar(tmp_path):
    database = tmp_path / "canonical.sqlite"
    setup_database(database)
    result = run_import(tmp_path, database, field_id=12, value={"0-4": 100, "5-9": 90})
    assert result["structured_observations"] == 1
    connection = sqlite3.connect(database)
    payload = json.loads(connection.execute("SELECT payload_json FROM selected_game_data").fetchone()[0])
    assert payload == {"unit": "age_band_share", "value": {"0-4": 100, "5-9": 90}}
    connection.close()

    # This explicit unavailable value is stored as SQL NULL with its declared status.
    null_result = run_import(
        tmp_path / "nullcase", database, field_id=1, value=None,
        status="unavailable", release="2024-r2",
    )
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


def test_new_release_from_same_provider_replaces_current_value(tmp_path):
    database = tmp_path / "canonical.sqlite"
    setup_database(database)
    run_import(tmp_path, database, value=100)
    raw = tmp_path / "raw_data" / "wp1_5" / SOURCE / "2025-r1" / "provider.csv"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("provider,captured\nnew-release\n", encoding="utf-8")
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["release"] = "2025-r1"
    manifest["sha256"] = digest
    manifest["local_raw_path"] = str(raw)
    manifest["byte_count"] = raw.stat().st_size
    manifest["retrieved_at"] = "2026-10-31T11:00:00Z"
    manifest_path.write_text(json.dumps(manifest))
    observations_path = tmp_path / "normalized.json"
    observations = json.loads(observations_path.read_text())
    observations["release"] = "2025-r1"
    observations["source_sha256"] = digest
    observations["observations"][0]["value"] = 200
    observations["observations"][0]["observation_period"] = "2025"
    observations_path.write_text(json.dumps(observations))
    result = import_wp1_5_dataset(
        observations_path=observations_path,
        crosswalk_path=tmp_path / "crosswalk.json",
        manifest_path=manifest_path,
        database_path=database,
    )
    assert result["release"] == "2025-r1"
    connection = sqlite3.connect(database)
    assert connection.execute(
        "SELECT value, observation_period, source_version FROM current_statistics"
    ).fetchone() == (200.0, "2025", "2025-r1")
    assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 2
    connection.close()


def test_rejects_non_string_value_status_without_partial_import(tmp_path):
    database = tmp_path / "canonical.sqlite"
    setup_database(database)
    observations, crosswalk, manifest = setup_inputs(tmp_path)
    payload = json.loads(observations.read_text())
    payload["observations"][0]["value_status"] = ["observed"]
    observations.write_text(json.dumps(payload))
    with pytest.raises(StatisticsImportError, match="value_status is invalid"):
        import_wp1_5_dataset(
            observations_path=observations,
            crosswalk_path=crosswalk,
            manifest_path=manifest,
            database_path=database,
        )
    connection = sqlite3.connect(database)
    assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 0
    connection.close()


def test_persists_crosswalk_even_when_observation_subset_is_smaller(tmp_path):
    database = tmp_path / "canonical.sqlite"
    setup_database(database)
    observations, crosswalk, manifest = setup_inputs(tmp_path)
    result = import_wp1_5_dataset(
        observations_path=observations, crosswalk_path=crosswalk,
        manifest_path=manifest, database_path=database,
    )
    assert result["crosswalk_mappings"] == 2
    connection = connect_database(database)
    assert connection.execute("SELECT COUNT(*) FROM country_sources WHERE dataset = ?", (SOURCE,)).fetchone()[0] == 2
    connection.close()


def test_rejects_timezone_naive_retrieval_timestamp(tmp_path):
    database = tmp_path / "canonical.sqlite"
    setup_database(database)
    observations, crosswalk, manifest = setup_inputs(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["retrieved_at"] = "2026-10-31T10:00:00"
    manifest.write_text(json.dumps(payload))
    with pytest.raises(StatisticsImportError, match="include a timezone"):
        import_wp1_5_dataset(
            observations_path=observations, crosswalk_path=crosswalk,
            manifest_path=manifest, database_path=database,
        )


def test_uses_contract_methodology_when_row_omits_it(tmp_path):
    database = tmp_path / "canonical.sqlite"
    setup_database(database)
    observations, crosswalk, manifest = setup_inputs(tmp_path)
    payload = json.loads(observations.read_text())
    payload["observations"][0].pop("methodology")
    observations.write_text(json.dumps(payload))
    import_wp1_5_dataset(
        observations_path=observations, crosswalk_path=crosswalk,
        manifest_path=manifest, database_path=database,
    )
    connection = sqlite3.connect(database)
    method = connection.execute("SELECT methodology FROM current_statistics").fetchone()[0]
    assert method and method.strip()
    connection.close()


def test_rejects_unit_outside_field_contract(tmp_path):
    database = tmp_path / "canonical.sqlite"
    setup_database(database)
    observations, crosswalk, manifest = setup_inputs(tmp_path)
    payload = json.loads(observations.read_text())
    payload["observations"][0]["unit"] = "percent"
    observations.write_text(json.dumps(payload))
    with pytest.raises(StatisticsImportError, match="not permitted by field contract"):
        import_wp1_5_dataset(
            observations_path=observations, crosswalk_path=crosswalk,
            manifest_path=manifest, database_path=database,
        )
    connection = sqlite3.connect(database)
    assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 0
    connection.close()


def test_older_snapshot_cannot_roll_back_current_observation(tmp_path):
    database = tmp_path / "canonical.sqlite"
    setup_database(database)
    run_import(tmp_path, database, value=200)
    raw = tmp_path / "raw_data" / "wp1_5" / SOURCE / "older" / "provider.csv"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("provider,older-snapshot\n", encoding="utf-8")
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update({
        "release": "older", "sha256": digest, "local_raw_path": str(raw),
        "byte_count": raw.stat().st_size, "retrieved_at": "2026-10-30T09:00:00Z",
    })
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    observations_path = tmp_path / "normalized.json"
    observations = json.loads(observations_path.read_text())
    observations.update({"release": "older", "source_sha256": digest})
    observations["observations"][0]["value"] = 100
    observations_path.write_text(json.dumps(observations), encoding="utf-8")
    with pytest.raises(StatisticsImportError, match="non-newer source snapshot"):
        import_wp1_5_dataset(
            observations_path=observations_path, crosswalk_path=tmp_path / "crosswalk.json",
            manifest_path=manifest_path, database_path=database,
        )
    connection = sqlite3.connect(database)
    assert connection.execute("SELECT value FROM current_statistics").fetchone()[0] == 200
    assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 1
    connection.close()


@pytest.mark.parametrize("remove_key, expected", [
    ("value_status", "value_status is invalid"),
    ("value", "value must be present"),
    ("unit", "unit must be a non-empty string"),
])
def test_requires_explicit_value_status_value_and_unit(tmp_path, remove_key, expected):
    database = tmp_path / "canonical.sqlite"
    setup_database(database)
    observations, crosswalk, manifest = setup_inputs(tmp_path)
    payload = json.loads(observations.read_text())
    del payload["observations"][0][remove_key]
    observations.write_text(json.dumps(payload))
    with pytest.raises(StatisticsImportError, match=expected):
        import_wp1_5_dataset(
            observations_path=observations, crosswalk_path=crosswalk,
            manifest_path=manifest, database_path=database,
        )
    connection = sqlite3.connect(database)
    assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 0
    connection.close()

def test_late_batch_conflict_rolls_back_earlier_rows_and_provenance(tmp_path, monkeypatch):
    paths = _inputs(tmp_path, monkeypatch)
    connection = sqlite3.connect(paths[0])
    connection.execute(
        """INSERT INTO dataset_imports
           (dataset, source_version, source_url, retrieval_date, sha256, import_status, imported_at)
           VALUES ('another_provider', 'v1', 'https://example.test/old', '2025-01-01T00:00:00Z',
                   ?, 'candidate', '2025-01-01T00:00:00Z')""",
        ("1" * 64,),
    )
    other_import = connection.execute("SELECT import_id FROM dataset_imports").fetchone()[0]
    connection.execute(
        """INSERT INTO current_statistics
           (game_id, statistic_key, value, unit, observed_at, observation_period,
            value_status, source_reference, source_version, retrieved_at, import_id)
           VALUES (?, 'population_growth', 0.5, 'percent_per_year', '2025', '2025',
                   'observed', 'https://example.test/old', 'v1', '2025-01-01T00:00:00Z', ?)""",
        (GAME_B, other_import),
    )
    connection.commit()
    connection.close()

    batch = json.loads(paths[1].read_text(encoding="utf-8"))
    batch["observations"].append({
        "game_id": GAME_B,
        "source_id": "provider-2",
        "field_id": 2,
        "value": 1.2,
        "unit": "percent_per_year",
        "value_status": "projected",
        "observation_period": "2026",
        "source_reference": "WPP2024:population-growth",
    })
    paths[1].write_text(json.dumps(batch), encoding="utf-8")
    with pytest.raises(StatisticsImportError, match="conflicts with a different source"):
        _run(paths)
    with _connect(paths[0]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM dataset_imports").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM country_sources WHERE dataset = ?", (SOURCE,)).fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM current_statistics WHERE game_id = ?", (GAME,)).fetchone()[0] == 0
        assert connection.execute("SELECT value FROM current_statistics WHERE game_id = ?", (GAME_B,)).fetchone()[0] == 0.5

