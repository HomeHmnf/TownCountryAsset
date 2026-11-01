from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.sources.refresh import run_refresh
from tools.sources.registry import load_registry


def _registry(tmp_path: Path) -> dict:
    config = {
        "schema_version": 1,
        "storage": {"raw_root": "raw", "manifest_root": "manifests", "reports_root": "reports"},
        "release_management": {
            "selection_policy": "latest_validated",
            "discovery_modes": {"manual_review": "manual"},
        },
        "sources": {
            "sample": {
                "name": "Sample",
                "release_discovery": {
                    "mode": "manual_review", "provider_url": "https://example.test/releases",
                    "automation_status": "not_implemented",
                    "latest_available": None, "latest_validated": None, "latest_applied": None,
                },
                "downloads": [{
                    "id": "dataset", "release": "v1", "release_kind": "edition_or_snapshot",
                    "filename": "data.csv", "url": "https://example.test/data.csv", "format": "csv",
                }],
            },
            "manual": {
                "name": "Manual source",
                "release_discovery": {
                    "mode": "manual_review", "provider_url": "https://example.test/manual",
                    "automation_status": "not_implemented",
                    "latest_available": None, "latest_validated": None, "latest_applied": None,
                },
                "downloads": [],
            },
        },
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return load_registry(path)


def _manifest(registry: dict, payload: bytes) -> None:
    root = registry["_root"]
    raw = root / "raw/sample/dataset/v1/data.csv"
    manifest = root / "manifests/sample/dataset/v1.json"
    raw.parent.mkdir(parents=True)
    manifest.parent.mkdir(parents=True)
    raw.write_bytes(payload)
    manifest.write_text(json.dumps({
        "source_id": "sample", "download_id": "dataset",
        "sha256": hashlib.sha256(payload).hexdigest(), "byte_count": len(payload),
    }), encoding="utf-8")


def test_refresh_skips_valid_snapshots_and_reports_manual_sources(tmp_path):
    registry = _registry(tmp_path)
    _manifest(registry, b"existing")
    report = run_refresh(registry, report_root=tmp_path / "reports")
    item = report["sources"][0]["downloads"][0]
    assert item["status"] == "unchanged"
    assert report["sources"][1]["discovery_status"] == "manual_review_required"
    assert report["database_imported"] is False
    assert Path(report["report_paths"]["json"]).is_file()
    assert Path(report["report_paths"]["markdown"]).is_file()


def test_refresh_dry_run_does_not_acquire_missing_snapshot(tmp_path):
    registry = _registry(tmp_path)
    report = run_refresh(registry, dry_run=True, report_root=tmp_path / "reports")
    assert report["sources"][0]["downloads"][0]["status"] == "would_acquire"
    assert not (tmp_path / "raw/sample/dataset/v1/data.csv").exists()


def test_refresh_does_not_overwrite_invalid_snapshot(tmp_path):
    registry = _registry(tmp_path)
    _manifest(registry, b"original")
    raw = tmp_path / "raw/sample/dataset/v1/data.csv"
    raw.write_bytes(b"tampered")
    report = run_refresh(registry, report_root=tmp_path / "reports")
    assert report["sources"][0]["downloads"][0]["status"] == "validation_error"
    assert raw.read_bytes() == b"tampered"
