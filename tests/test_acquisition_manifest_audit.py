from __future__ import annotations

import hashlib
import json

import pytest

from tools.audit_acquisition_manifests import audit_manifests


def _write_manifest(root, relative_path, payload):
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _artifact(root, relative_path, *, aliases=False):
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    content = b"sample acquisition artifact"
    path.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    if aliases:
        return {
            "file_id": "sample",
            "path": relative_path,
            "repository_path": relative_path,
            "expected_byte_count": len(content),
            "byte_count": len(content),
            "expected_sha256": digest,
            "sha256": digest,
        }
    return {
        "filename": path.name,
        "local_raw_path": relative_path,
        "byte_count": len(content),
        "sha256": digest,
    }


def test_audit_supports_file_list_and_legacy_single_artifact_layout(tmp_path):
    listed = _artifact(tmp_path, "raw/listed.bin")
    legacy = _artifact(tmp_path, "raw/legacy.bin", aliases=True)
    _write_manifest(tmp_path, "data_manifests/sources/sample/list.json", {
        "manifest_schema_version": 1,
        "source_id": "sample",
        "download_id": "listed_dataset",
        "release": "2026-01",
        "files": [listed],
    })
    _write_manifest(tmp_path, "data_manifests/sources/sample/legacy.json", {
        "source_id": "sample",
        "download_id": "legacy_dataset",
        "release": "rolling",
        **legacy,
    })

    result = audit_manifests(repository_root=tmp_path)
    assert result["status"] == "ok"
    assert result["manifest_count"] == 2
    assert result["artifact_count"] == 2
    assert result["valid_manifest_count"] == 2
    assert result["read_only"] is True
    assert result["database_written"] is False
    assert result["retention_applied"] is False


def test_audit_reports_missing_file_and_checksum_mismatch(tmp_path):
    payload = _artifact(tmp_path, "raw/present.bin")
    (tmp_path / "raw/present.bin").write_bytes(b"tampered")
    payload["local_raw_path"] = "raw/missing.bin"
    _write_manifest(tmp_path, "data_manifests/sources/sample/bad.json", {
        "source_id": "sample",
        "download_id": "bad",
        "release": "r1",
        "files": [payload],
    })

    result = audit_manifests(repository_root=tmp_path)
    assert result["status"] == "error"
    codes = {issue["code"] for issue in result["manifests"][0]["artifacts"][0]["issues"]}
    assert "missing_file" in codes


def test_audit_detects_hash_and_size_mismatch(tmp_path):
    payload = _artifact(tmp_path, "raw/file.bin")
    (tmp_path / "raw/file.bin").write_bytes(b"changed bytes")
    _write_manifest(tmp_path, "data_manifests/sources/sample/bad.json", {
        "source_id": "sample",
        "download_id": "bad",
        "release": "r1",
        "files": [payload],
    })

    result = audit_manifests(repository_root=tmp_path)
    codes = {issue["code"] for issue in result["manifests"][0]["artifacts"][0]["issues"]}
    assert "byte_count_mismatch" in codes
    assert "sha256_mismatch" in codes


@pytest.mark.parametrize("unsafe", ["../outside.bin", "/tmp/outside.bin", "C:\\outside.bin"])
def test_audit_rejects_unsafe_artifact_paths(tmp_path, unsafe):
    _write_manifest(tmp_path, "data_manifests/sources/sample/bad.json", {
        "source_id": "sample",
        "download_id": "bad",
        "release": "r1",
        "files": [{
            "path": unsafe,
            "byte_count": 0,
            "sha256": "0" * 64,
        }],
    })
    result = audit_manifests(repository_root=tmp_path)
    assert result["status"] == "error"
    assert result["manifests"][0]["artifacts"][0]["issues"][0]["code"] == "unsafe_path"


def test_repository_manifests_have_supported_layouts_and_valid_artifact_fingerprints():
    result = audit_manifests()
    assert result["manifest_count"] == 10
    assert result["artifact_count"] == 15
    assert result["status"] == "ok", result
