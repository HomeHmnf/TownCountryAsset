from __future__ import annotations

import hashlib
import json

from tools.database.acquisition_registration import register_manifest_acquisitions
from tools.database.project_connection import connect_project_database
from tools.database.schema import apply_migrations
from tools.database.project_connection import PROJECT_MIGRATIONS_DIR


def _seed_catalogue(database):
    with connect_project_database(database) as connection:
        apply_migrations(connection, PROJECT_MIGRATIONS_DIR)
        connection.execute(
            """INSERT INTO sources(source_key, name, created_at, updated_at)
               VALUES ('sample', 'Sample source', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"""
        )
        connection.execute(
            """INSERT INTO datasets(source_key, dataset_key, name, created_at, updated_at)
               VALUES ('sample', 'annual_series', 'Annual series', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"""
        )
        dataset_id = connection.execute("SELECT dataset_id FROM datasets").fetchone()[0]
        connection.execute(
            """INSERT INTO acquisition_streams(dataset_id, stream_key, name, created_at, updated_at)
               VALUES (?, 'rolling_csv', 'Rolling CSV', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')""",
            (dataset_id,),
        )


def _write_manifest(root, release, acquired_at, payload_bytes=b"year,value\n2025,10\n"):
    raw = root / "raw_data" / f"{release}.csv"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(payload_bytes)
    manifest = {
        "manifest_schema_version": 1,
        "source_id": "sample",
        "dataset_id": "annual_series",
        "release": release,
        "retrieved_at": acquired_at,
        "files": [{
            "filename": raw.name,
            "url": "https://example.test/data.csv",
            "final_url": "https://example.test/data.csv",
            "content_type": "text/csv",
            "byte_count": raw.stat().st_size,
            "sha256": hashlib.sha256(payload_bytes).hexdigest(),
            "local_raw_path": raw.relative_to(root).as_posix(),
        }],
    }
    manifest_path = root / "data_manifests" / f"{release}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_manifest_registration_is_transactional_idempotent_and_preserves_distinct_events(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    first = _write_manifest(root, "capture-a", "2026-11-01T10:00:00+00:00")
    second = _write_manifest(root, "capture-b", "2026-11-02T10:00:00+00:00")
    database = tmp_path / "project.sqlite"
    _seed_catalogue(database)

    dry = register_manifest_acquisitions(
        database_path=database, repository_root=root,
        manifest_dir="data_manifests", dry_run=True,
    )
    assert len(dry["registered"]) == 2
    with connect_project_database(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM acquisitions").fetchone()[0] == 0

    first_run = register_manifest_acquisitions(
        database_path=database, repository_root=root, manifest_dir="data_manifests",
    )
    assert len(first_run["registered"]) == 2
    assert not first_run["errors"]
    replay = register_manifest_acquisitions(
        database_path=database, repository_root=root, manifest_dir="data_manifests",
    )
    assert len(replay["unchanged"]) == 2

    with connect_project_database(database) as connection:
        acquisitions = connection.execute(
            """SELECT acquisition_event_key, status, integrity_status, acquisition_year,
                      manifest_sha256, evidence_json
               FROM acquisitions ORDER BY acquired_at"""
        ).fetchall()
        assert len(acquisitions) == 2
        assert [row["status"] for row in acquisitions] == ["acquired", "acquired"]
        assert [row["integrity_status"] for row in acquisitions] == ["verified", "verified"]
        assert [row["acquisition_year"] for row in acquisitions] == [2026, 2026]
        assert [row["acquisition_event_key"] for row in acquisitions] == [
            first.relative_to(root).as_posix(), second.relative_to(root).as_posix()
        ]
        assert json.loads(acquisitions[0]["evidence_json"])["manifest_payload"]["release"] == "capture-a"
        assert connection.execute("SELECT COUNT(*) FROM acquisition_artifacts").fetchone()[0] == 2


def test_manifest_registration_defers_unregistered_stream_without_writing(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _write_manifest(root, "capture-a", "2026-11-01T10:00:00+00:00")
    database = tmp_path / "project.sqlite"
    with connect_project_database(database) as connection:
        apply_migrations(connection, PROJECT_MIGRATIONS_DIR)
        connection.execute(
            """INSERT INTO sources(source_key, name, created_at, updated_at)
               VALUES ('sample', 'Sample source', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"""
        )
    result = register_manifest_acquisitions(
        database_path=database, repository_root=root, manifest_dir="data_manifests",
    )
    assert len(result["deferred"]) == 1
    with connect_project_database(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM acquisitions").fetchone()[0] == 0


def test_changed_manifest_evidence_conflicts_with_existing_event(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    manifest = _write_manifest(root, "capture-a", "2026-11-01T10:00:00+00:00")
    database = tmp_path / "project.sqlite"
    _seed_catalogue(database)
    register_manifest_acquisitions(
        database_path=database, repository_root=root, manifest_dir="data_manifests",
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["operator_note"] = "changed after registration"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    result = register_manifest_acquisitions(
        database_path=database, repository_root=root, manifest_dir="data_manifests",
    )
    assert result["errors"]
    assert "changed evidence" in result["errors"][0]["reason"]
    with connect_project_database(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM acquisitions").fetchone()[0] == 1
