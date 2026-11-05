"""Idempotent synchronization of reviewed dataset and stream definitions."""

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

DEFAULT_DATASET_CONFIG_PATH = REPOSITORY_ROOT / "config" / "project_datasets.json"
MANAGED_BY = "config/project_datasets.json"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sync_dataset_catalogue(
    *,
    database_path: str | Path = DEFAULT_PROJECT_DATABASE_PATH,
    config_path: str | Path = DEFAULT_DATASET_CONFIG_PATH,
) -> dict[str, int]:
    """Upsert reviewed datasets and streams; never creates acquisition records."""
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    datasets = config.get("datasets")
    if not isinstance(datasets, list):
        raise ValueError("dataset config must contain a list named 'datasets'")

    timestamp = utc_now()
    counts = {"datasets": 0, "streams": 0}
    seen_datasets: set[tuple[str, str]] = set()
    seen_streams: set[tuple[str, str, str]] = set()
    connection = connect_project_database(database_path)
    try:
        apply_migrations(connection, PROJECT_MIGRATIONS_DIR)
        connection.execute("BEGIN IMMEDIATE")
        for item in datasets:
            if not isinstance(item, dict):
                raise ValueError("each dataset definition must be an object")
            source_key = item.get("source_key")
            dataset_key = item.get("dataset_key")
            name = item.get("name")
            if not all(isinstance(value, str) and value.strip()
                       for value in (source_key, dataset_key, name)):
                raise ValueError("dataset source_key, dataset_key and name must be non-empty strings")
            identity = (source_key, dataset_key)
            if identity in seen_datasets:
                raise ValueError(f"duplicate dataset definition: {identity!r}")
            seen_datasets.add(identity)
            metadata = dict(item.get("metadata") or {})
            metadata["managed_by"] = MANAGED_BY
            cursor = connection.execute(
                """INSERT INTO datasets (
                    source_key, dataset_key, name, description, data_format,
                    frequency, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_key, dataset_key) DO UPDATE SET
                    name=excluded.name, description=excluded.description,
                    data_format=excluded.data_format, frequency=excluded.frequency,
                    metadata_json=excluded.metadata_json, updated_at=excluded.updated_at
                RETURNING dataset_id""",
                (source_key, dataset_key, name.strip(), item.get("description"),
                 item.get("data_format"), item.get("frequency"), _json(metadata),
                 timestamp, timestamp),
            )
            dataset_id = int(cursor.fetchone()[0])
            counts["datasets"] += 1

            streams = item.get("streams", [])
            if not isinstance(streams, list):
                raise ValueError(f"streams for dataset {identity!r} must be a list")
            for stream in streams:
                if not isinstance(stream, dict):
                    raise ValueError(f"stream for dataset {identity!r} must be an object")
                stream_key = stream.get("stream_key")
                stream_name = stream.get("name")
                if not all(isinstance(value, str) and value.strip()
                           for value in (stream_key, stream_name)):
                    raise ValueError("stream_key and stream name must be non-empty strings")
                stream_identity = (source_key, dataset_key, stream_key)
                if stream_identity in seen_streams:
                    raise ValueError(f"duplicate stream definition: {stream_identity!r}")
                seen_streams.add(stream_identity)
                stream_metadata = dict(stream.get("metadata") or {})
                stream_metadata["managed_by"] = MANAGED_BY
                connection.execute(
                    """INSERT INTO acquisition_streams (
                        dataset_id, stream_key, name, acquisition_mode,
                        validation_contract_json, retention_limit, is_active,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 2, 1, ?, ?)
                    ON CONFLICT(dataset_id, stream_key) DO UPDATE SET
                        name=excluded.name,
                        acquisition_mode=excluded.acquisition_mode,
                        validation_contract_json=excluded.validation_contract_json,
                        updated_at=excluded.updated_at""",
                    (dataset_id, stream_key, stream_name.strip(),
                     stream.get("acquisition_mode"),
                     _json({
                         "contract": stream.get("validation_contract", {}),
                         "metadata": stream_metadata,
                     }), timestamp, timestamp),
                )
                counts["streams"] += 1

        connection.commit()
        return counts
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(DEFAULT_PROJECT_DATABASE_PATH))
    parser.add_argument("--config", default=str(DEFAULT_DATASET_CONFIG_PATH))
    args = parser.parse_args()
    counts = sync_dataset_catalogue(database_path=args.database, config_path=args.config)
    print(f"Project database: {args.database}")
    print(f"Datasets synchronized: {counts['datasets']}")
    print(f"Acquisition streams synchronized: {counts['streams']}")
    print("No acquisitions, artifacts, approvals, retention operations or source-selection settings were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
