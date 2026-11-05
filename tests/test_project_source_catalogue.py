from __future__ import annotations

import json
import sqlite3

from tools.database.project_connection import (
    PROJECT_MIGRATIONS_DIR,
    connect_project_database,
)
from tools.database.schema import apply_migrations
from tools.database.source_catalogue import sync_source_catalogue


def _config():
    return {
        "schema_version": 1,
        "sources": {
            "sample_source": {
                "name": "Sample Source",
                "homepage_url": "https://example.test/",
                "terms_url": "https://example.test/terms",
                "domains": ["economy", "labour"],
                "license_status": "unclear_or_unverified",
                "attribution": "Sample attribution",
                "notes": "Preserve complete source metadata.",
                "acquisition_mode": "manual",
                "field_ids": [12, 13],
                "legacy_source_ids": ["legacy_sample"],
                "release_discovery": {
                    "mode": "manual_review",
                    "provider_url": "https://example.test/releases",
                    "latest_validated": None,
                },
                "downloads": [
                    {
                        "id": "annual_csv",
                        "release": "rolling",
                        "url": "https://example.test/data.csv",
                        "format": "csv",
                    }
                ],
            }
        },
    }


def test_source_catalogue_sync_preserves_metadata_and_typed_urls(tmp_path):
    config_path = tmp_path / "data_sources.json"
    config_path.write_text(json.dumps(_config()), encoding="utf-8")
    database_path = tmp_path / "project.sqlite"

    result = sync_source_catalogue(database_path=database_path, config_path=config_path)
    assert result == {"sources": 1, "source_urls": 4}

    with connect_project_database(database_path) as connection:
        source = connection.execute(
            "SELECT * FROM sources WHERE source_key='sample_source'"
        ).fetchone()
        assert source["organisation_key"] is None
        assert json.loads(source["metadata_json"]) == _config()["sources"]["sample_source"]
        assert json.loads(source["domains_json"]) == ["economy", "labour"]
        assert source["license_status"] == "unclear_or_unverified"
        assert source["attribution"] == "Sample attribution"
        assert json.loads(source["field_ids_json"]) == [12, 13]
        assert json.loads(source["legacy_source_ids_json"]) == ["legacy_sample"]
        urls = connection.execute(
            "SELECT url_role, url, metadata_json FROM source_urls ORDER BY url_role"
        ).fetchall()
        assert {(row["url_role"], row["url"]) for row in urls} == {
            ("homepage", "https://example.test/"),
            ("terms", "https://example.test/terms"),
            ("dataset_page", "https://example.test/releases"),
            ("download", "https://example.test/data.csv"),
        }
        assert connection.execute("SELECT COUNT(*) FROM datasets").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM acquisition_streams").fetchone()[0] == 0


def test_source_catalogue_sync_is_idempotent_and_updates_managed_urls(tmp_path):
    config = _config()
    config_path = tmp_path / "data_sources.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    database_path = tmp_path / "project.sqlite"

    first = sync_source_catalogue(database_path=database_path, config_path=config_path)
    with connect_project_database(database_path) as connection:
        connection.execute(
            "INSERT INTO source_urls(source_key, url_role, url, metadata_json, created_at) "
            "VALUES ('sample_source', 'evidence', 'https://manual.example.test/evidence', '{\"managed_by\":\"manual\"}', 'now')"
        )
    second = sync_source_catalogue(database_path=database_path, config_path=config_path)
    assert first == second == {"sources": 1, "source_urls": 4}

    config["sources"]["sample_source"]["homepage_url"] = "https://example.test/new-home"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    sync_source_catalogue(database_path=database_path, config_path=config_path)

    with connect_project_database(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 1
        homepage = connection.execute(
            "SELECT url FROM source_urls WHERE url_role='homepage'"
        ).fetchone()[0]
        assert homepage == "https://example.test/new-home"
        assert connection.execute("SELECT COUNT(*) FROM source_urls").fetchone()[0] == 5
        assert connection.execute(
            "SELECT COUNT(*) FROM source_urls WHERE url='https://manual.example.test/evidence'"
        ).fetchone()[0] == 1


def test_source_catalogue_sync_rolls_back_invalid_config(tmp_path):
    config = _config()
    config["sources"]["broken"] = {"name": ""}
    config_path = tmp_path / "data_sources.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    database_path = tmp_path / "project.sqlite"

    try:
        sync_source_catalogue(database_path=database_path, config_path=config_path)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid source configuration should fail")

    with connect_project_database(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM source_urls").fetchone()[0] == 0


def test_repository_source_registry_maps_all_stable_keys_and_configured_urls(tmp_path):
    from tools.database.source_catalogue import DEFAULT_SOURCE_CONFIG_PATH

    config = json.loads(DEFAULT_SOURCE_CONFIG_PATH.read_text(encoding="utf-8"))
    expected_source_count = len(config["sources"])
    expected_url_count = sum(
        int(bool(source.get("homepage_url")))
        + int(bool(source.get("terms_url")))
        + int(bool((source.get("release_discovery") or {}).get("provider_url")))
        + sum(bool(download.get("url")) for download in source.get("downloads", []))
        for source in config["sources"].values()
    )

    result = sync_source_catalogue(
        database_path=tmp_path / "project.sqlite",
        config_path=DEFAULT_SOURCE_CONFIG_PATH,
    )
    assert result == {
        "sources": expected_source_count,
        "source_urls": expected_url_count,
    }
    assert expected_source_count == 31
    assert expected_url_count == 92
