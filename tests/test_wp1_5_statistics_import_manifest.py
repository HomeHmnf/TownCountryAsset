import hashlib

import pytest

import tools.database.statistics_import as statistics_import
from tools.database.statistics_import import StatisticsImportError, _validate_manifest


def manifest_for(path):
    payload = path.read_bytes()
    return {
        "manifest_schema_version": 1,
        "work_package": "WP1.5",
        "source_key": "un_wpp_2024",
        "release": "2024",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "local_raw_path": str(path),
        "byte_count": len(payload),
        "final_url": "https://example.test/source.csv",
        "retrieved_at": "2026-10-31T10:00:00Z",
    }


def test_manifest_verifies_raw_byte_count(tmp_path, monkeypatch):
    monkeypatch.setattr(statistics_import, "REPOSITORY_ROOT", tmp_path)
    raw = tmp_path / "raw_data" / "raw.csv"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b"source,data\n")
    manifest = manifest_for(raw)
    manifest["byte_count"] += 1
    with pytest.raises(StatisticsImportError, match="byte count"):
        _validate_manifest(manifest, "un_wpp_2024")


def test_manifest_verifies_raw_checksum(tmp_path, monkeypatch):
    monkeypatch.setattr(statistics_import, "REPOSITORY_ROOT", tmp_path)
    raw = tmp_path / "raw_data" / "raw.csv"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b"source,data\n")
    manifest = manifest_for(raw)
    raw.write_bytes(b"tampered")
    with pytest.raises(StatisticsImportError, match="checksum"):
        _validate_manifest(manifest, "un_wpp_2024")

def test_manifest_rejects_nested_raw_data_directory_outside_repository_raw_root(tmp_path, monkeypatch):
    monkeypatch.setattr(statistics_import, "REPOSITORY_ROOT", tmp_path)
    raw = tmp_path / "nested" / "raw_data" / "raw.csv"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b"source,data\\n")
    manifest = manifest_for(raw)
    with pytest.raises(StatisticsImportError, match="directly under the repository raw_data tree"):
        _validate_manifest(manifest, "un_wpp_2024")
