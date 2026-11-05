from __future__ import annotations

import hashlib
import json

import pytest

from tools import assess_imf_weo
from tools.register_imf_weo_manual_acquisition import register_imf_weo_manual_acquisition
from tools.database.project_connection import (
    PROJECT_MIGRATIONS_DIR,
    connect_project_database,
)
from tools.database.schema import apply_migrations


def _seed_catalogue(database):
    with connect_project_database(database) as connection:
        apply_migrations(connection, PROJECT_MIGRATIONS_DIR)
        connection.execute(
            """INSERT INTO sources(source_key, name, created_at, updated_at)
               VALUES ('imf_weo', 'IMF WEO', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"""
        )
        connection.execute(
            """INSERT INTO datasets(source_key, dataset_key, name, created_at, updated_at)
               VALUES ('imf_weo', 'world_economic_outlook', 'World Economic Outlook',
                       '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"""
        )
        dataset_id = connection.execute("SELECT dataset_id FROM datasets").fetchone()[0]
        connection.execute(
            """INSERT INTO acquisition_streams(dataset_id, stream_key, name, created_at, updated_at)
               VALUES (?, 'manual_vintage_bundle', 'Manual vintage bundles',
                       '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')""",
            (dataset_id,),
        )


def _write_snapshot(root, monkeypatch):
    csv_path = root / "raw_data" / "weo.csv"
    pdf_path = root / "raw_data" / "appendix.pdf"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_bytes(b"SERIES_CODE,2026\nUSA.NGDPD.A,100\n")
    pdf_path.write_bytes(b"%PDF-1.4 fixture")
    expected = {
        "csv": (hashlib.sha256(csv_path.read_bytes()).hexdigest(), csv_path.stat().st_size),
        "appendix": (hashlib.sha256(pdf_path.read_bytes()).hexdigest(), pdf_path.stat().st_size),
    }
    monkeypatch.setattr(assess_imf_weo, "EXPECTED", expected)
    doc = root / "docs" / "manual-record.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "Manual download date: 2026-11-02\n"
        f"{csv_path.name} {expected['csv'][0]}\n"
        f"{pdf_path.name} {expected['appendix'][0]}\n",
        encoding="utf-8",
    )
    return csv_path, pdf_path, doc


def test_manual_bundle_registration_is_byte_verified_idempotent_and_read_only_to_game_db(
    tmp_path, monkeypatch
):
    root = tmp_path / "repo"
    root.mkdir()
    csv_path, pdf_path, doc = _write_snapshot(root, monkeypatch)
    database = tmp_path / "project.sqlite"
    _seed_catalogue(database)

    kwargs = {
        "database_path": database,
        "repository_root": root,
        "csv_path": csv_path,
        "appendix_path": pdf_path,
        "manual_record_path": doc,
    }
    dry = register_imf_weo_manual_acquisition(**kwargs, dry_run=True)
    assert len(dry["registered"]) == 1
    with connect_project_database(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM acquisitions").fetchone()[0] == 0

    first = register_imf_weo_manual_acquisition(**kwargs)
    assert first["registered"][0]["artifact_count"] == 2
    replay = register_imf_weo_manual_acquisition(**kwargs)
    assert replay["unchanged"][0]["acquisition_id"] == first["registered"][0]["acquisition_id"]

    with connect_project_database(database) as connection:
        row = connection.execute(
            """SELECT provider_release_id, acquisition_year, acquired_at,
                      provider_published_at, status, integrity_status,
                      acquisition_event_key, manifest_sha256, evidence_json
               FROM acquisitions"""
        ).fetchone()
        assert row["provider_release_id"] == "october_2026"
        assert row["acquisition_year"] == 2026
        assert row["acquired_at"] == "2026-11-02"
        assert row["provider_published_at"] == "2026-10-13"
        assert row["status"] == "acquired"
        assert row["integrity_status"] == "verified"
        assert row["acquisition_event_key"] == "manual:october_2026:2026-11-02"
        assert row["manifest_sha256"] is None
        evidence = json.loads(row["evidence_json"])
        assert evidence["formal_manifest_present"] is False
        assert evidence["acquisition_date_precision"] == "day"
        assert "not an" in evidence["timestamp_limitation"]
        artifacts = connection.execute(
            """SELECT artifact_role, relative_path, media_type
               FROM acquisition_artifacts ORDER BY artifact_role"""
        ).fetchall()
        assert [(a["artifact_role"], a["media_type"]) for a in artifacts] == [
            ("dataset", "text/csv"),
            ("supporting_document", "application/pdf"),
        ]
        assert connection.execute("SELECT COUNT(*) FROM acquisitions").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM acquisition_artifacts").fetchone()[0] == 2


def test_manual_bundle_rejects_changed_snapshot_without_writing(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    csv_path, pdf_path, doc = _write_snapshot(root, monkeypatch)
    database = tmp_path / "project.sqlite"
    _seed_catalogue(database)
    csv_path.write_bytes(csv_path.read_bytes() + b"changed")

    with pytest.raises(ValueError, match="does not match the recorded"):
        register_imf_weo_manual_acquisition(
            database_path=database, repository_root=root,
            csv_path=csv_path, appendix_path=pdf_path, manual_record_path=doc,
        )
    with connect_project_database(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM acquisitions").fetchone()[0] == 0


def test_manual_bundle_defers_when_exact_stream_is_missing(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    csv_path, pdf_path, doc = _write_snapshot(root, monkeypatch)
    database = tmp_path / "project.sqlite"
    with connect_project_database(database) as connection:
        apply_migrations(connection, PROJECT_MIGRATIONS_DIR)

    result = register_imf_weo_manual_acquisition(
        database_path=database, repository_root=root,
        csv_path=csv_path, appendix_path=pdf_path, manual_record_path=doc,
    )
    assert result["errors"]
    with connect_project_database(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM acquisitions").fetchone()[0] == 0
