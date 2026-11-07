from __future__ import annotations

import json

from tools.database.dataset_catalogue import sync_dataset_catalogue
from tools.database.project_connection import connect_project_database
from tools.database.source_catalogue import sync_source_catalogue


def _source_config():
    return {"schema_version": 1, "sources": {
        "sample": {"name": "Sample source"}
    }}


def _dataset_config():
    return {"schema_version": 1, "datasets": [
        {
            "source_key": "sample",
            "dataset_key": "annual_series",
            "name": "Annual series",
            "data_format": "csv",
            "frequency": "annual",
            "metadata": {"provider_id": "A"},
            "streams": [{
                "stream_key": "rolling_csv",
                "name": "Rolling CSV captures",
                "acquisition_mode": "https_download",
                "validation_contract": {"required_columns": ["year", "value"]},
                "metadata": {"release_semantics": "rolling"},
            }],
        },
        {
            "source_key": "sample",
            "dataset_key": "supporting_reference",
            "name": "Supporting reference",
            "data_format": "html",
            "frequency": "current_reference",
            "metadata": {},
            "streams": [],
        },
    ]}


def test_dataset_catalogue_sync_registers_datasets_and_streams_idempotently(tmp_path):
    database = tmp_path / "project.sqlite"
    source_path = tmp_path / "sources.json"
    dataset_path = tmp_path / "datasets.json"
    source_path.write_text(json.dumps(_source_config()), encoding="utf-8")
    dataset_path.write_text(json.dumps(_dataset_config()), encoding="utf-8")
    sync_source_catalogue(database_path=database, config_path=source_path)

    expected = {"datasets": 2, "streams": 1}
    assert sync_dataset_catalogue(database_path=database, config_path=dataset_path) == expected
    assert sync_dataset_catalogue(database_path=database, config_path=dataset_path) == expected

    with connect_project_database(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM datasets").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM acquisition_streams").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM acquisitions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM acquisition_artifacts").fetchone()[0] == 0
        stream = connection.execute(
            "SELECT validation_contract_json, retention_limit FROM acquisition_streams"
        ).fetchone()
        payload = json.loads(stream["validation_contract_json"])
        assert payload["contract"]["required_columns"] == ["year", "value"]
        assert payload["metadata"]["release_semantics"] == "rolling"
        assert stream["retention_limit"] == 2


def test_dataset_catalogue_rejects_duplicate_identity_and_rolls_back(tmp_path):
    database = tmp_path / "project.sqlite"
    source_path = tmp_path / "sources.json"
    dataset_path = tmp_path / "datasets.json"
    source_path.write_text(json.dumps(_source_config()), encoding="utf-8")
    config = _dataset_config()
    config["datasets"].append(config["datasets"][0])
    dataset_path.write_text(json.dumps(config), encoding="utf-8")
    sync_source_catalogue(database_path=database, config_path=source_path)

    try:
        sync_dataset_catalogue(database_path=database, config_path=dataset_path)
    except ValueError as exc:
        assert "duplicate dataset definition" in str(exc)
    else:
        raise AssertionError("duplicate dataset identity should fail")

    with connect_project_database(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM datasets").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM acquisition_streams").fetchone()[0] == 0


def test_repository_dataset_registry_has_only_evidenced_streams(tmp_path):
    from tools.database.dataset_catalogue import DEFAULT_DATASET_CONFIG_PATH

    config = json.loads(DEFAULT_DATASET_CONFIG_PATH.read_text(encoding="utf-8"))
    database = tmp_path / "project.sqlite"
    sync_source_catalogue(database_path=database)
    counts = sync_dataset_catalogue(database_path=database)
    assert counts == {
        "datasets": len(config["datasets"]),
        "streams": sum(len(item.get("streams", [])) for item in config["datasets"]),
    }
    assert counts == {"datasets": 6, "streams": 4}
    with connect_project_database(database) as connection:
        wpp = connection.execute(
            "SELECT COUNT(*) FROM datasets WHERE source_key='un_wpp'"
        ).fetchone()[0]
        wpp_streams = connection.execute(
            """SELECT COUNT(*) FROM acquisition_streams AS s
               JOIN datasets AS d USING(dataset_id) WHERE d.source_key='un_wpp'"""
        ).fetchone()[0]
        assert wpp == 2
        assert wpp_streams == 0
