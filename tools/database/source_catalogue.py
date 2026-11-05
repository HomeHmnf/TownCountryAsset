"""Idempotent synchronization of config/data_sources.json into the project DB."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.database.connection import REPOSITORY_ROOT
from tools.database.project_connection import (
    DEFAULT_PROJECT_DATABASE_PATH,
    PROJECT_MIGRATIONS_DIR,
    connect_project_database,
)
from tools.database.schema import apply_migrations, utc_now

DEFAULT_SOURCE_CONFIG_PATH = REPOSITORY_ROOT / "config" / "data_sources.json"
MANAGED_BY = "config/data_sources.json"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _url_rows(source: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field, role in (("homepage_url", "homepage"), ("terms_url", "terms")):
        url = source.get(field)
        if isinstance(url, str) and url.strip():
            rows.append({
                "role": role,
                "url": url.strip(),
                "label": field,
                "metadata": {"managed_by": MANAGED_BY, "config_field": field},
            })

    discovery = source.get("release_discovery")
    if isinstance(discovery, dict):
        url = discovery.get("provider_url")
        if isinstance(url, str) and url.strip():
            rows.append({
                "role": "dataset_page",
                "url": url.strip(),
                "label": "release_discovery.provider_url",
                "metadata": {
                    "managed_by": MANAGED_BY,
                    "config_field": "release_discovery.provider_url",
                },
            })

    downloads = source.get("downloads", [])
    if not isinstance(downloads, list):
        raise ValueError("source downloads must be a list")
    for download in downloads:
        if not isinstance(download, dict):
            raise ValueError("each download definition must be an object")
        url = download.get("url")
        if isinstance(url, str) and url.strip():
            download_id = download.get("id")
            rows.append({
                "role": "download",
                "url": url.strip(),
                "label": str(download_id) if download_id is not None else None,
                "metadata": {
                    "managed_by": MANAGED_BY,
                    "config_download": download,
                },
            })
    return rows


def sync_source_catalogue(
    *,
    database_path: str | Path = DEFAULT_PROJECT_DATABASE_PATH,
    config_path: str | Path = DEFAULT_SOURCE_CONFIG_PATH,
) -> dict[str, int]:
    """Upsert all stable source keys and replace only config-managed URL rows."""
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    sources = config.get("sources")
    if not isinstance(sources, dict):
        raise ValueError("source config must contain an object named 'sources'")

    timestamp = utc_now()
    counts = {"sources": 0, "source_urls": 0}
    connection = connect_project_database(database_path)
    try:
        apply_migrations(connection, PROJECT_MIGRATIONS_DIR)
        connection.execute("BEGIN IMMEDIATE")
        for source_key, source in sources.items():
            if not isinstance(source_key, str) or not source_key.strip():
                raise ValueError("source keys must be non-empty strings")
            if not isinstance(source, dict):
                raise ValueError(f"source {source_key!r} must be an object")
            name = source.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"source {source_key!r} has no valid name")

            connection.execute(
                """INSERT INTO sources (
                    source_key, organisation_key, name, description, source_type,
                    metadata_json, created_at, updated_at, domains_json, license_status,
                    attribution, notes, acquisition_mode, release_discovery_json,
                    legacy_source_ids_json, field_ids_json
                ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_key) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    source_type=excluded.source_type,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at,
                    domains_json=excluded.domains_json,
                    license_status=excluded.license_status,
                    attribution=excluded.attribution,
                    notes=excluded.notes,
                    acquisition_mode=excluded.acquisition_mode,
                    release_discovery_json=excluded.release_discovery_json,
                    legacy_source_ids_json=excluded.legacy_source_ids_json,
                    field_ids_json=excluded.field_ids_json""",
                (
                    source_key, name.strip(), source.get("notes"),
                    source.get("acquisition_mode"), _json(source), timestamp, timestamp,
                    _json(source.get("domains", [])), source.get("license_status"),
                    source.get("attribution"), source.get("notes"),
                    source.get("acquisition_mode"), _json(source.get("release_discovery", {})),
                    _json(source.get("legacy_source_ids", [])),
                    _json(source.get("field_ids", [])),
                ),
            )
            counts["sources"] += 1

            # Replace only rows explicitly owned by this config synchronizer.
            connection.execute(
                """DELETE FROM source_urls
                   WHERE source_key = ?
                     AND json_extract(metadata_json, '$.managed_by') = ?""",
                (source_key, MANAGED_BY),
            )
            for url_row in _url_rows(source):
                connection.execute(
                    """INSERT INTO source_urls (
                        source_key, dataset_id, url_role, url, label,
                        metadata_json, created_at
                    ) VALUES (?, NULL, ?, ?, ?, ?, ?)""",
                    (
                        source_key, url_row["role"], url_row["url"], url_row["label"],
                        _json(url_row["metadata"]), timestamp,
                    ),
                )
                counts["source_urls"] += 1

        connection.commit()
        return counts
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
