import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools.sources.bahrain_unemployment import (
    BahrainAcquisitionError,
    acquire_snapshot,
)


def _response(payload, url):
    return (
        json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        {"content_type": "application/json"},
        url,
    )


def _registry(path, page_size=2):
    path.write_text(json.dumps({
        "sources": {
            "bahrain_open_data": {
                "name": "Bahrain Open Data Portal",
                "homepage_url": "https://data.gov.bh/explore/dataset/03-unemployment-yearly/",
                "license_status": "public_domain_or_unverified",
                "terms_url": "https://data.gov.bh/pages/faq/",
                "attribution": "Bahrain Open Data Portal",
                "api": {
                    "dataset_id": "03-unemployment-yearly",
                    "base_url": "https://data.gov.bh/api/explore/v2.1/catalog/datasets",
                    "page_size": page_size,
                },
            }
        }
    }), encoding="utf-8")
    return path


def test_acquires_all_pages_and_writes_hash_manifest(tmp_path):
    registry = _registry(tmp_path / "registry.json")
    base = "https://data.gov.bh/api/explore/v2.1/catalog/datasets/03-unemployment-yearly"
    calls = []

    def request(url, timeout):
        calls.append(url)
        if url == base:
            return _response({
                "dataset_id": "03-unemployment-yearly",
                "metas": {"metadata_processed": "2026-11-02", "data_processed": "2026-11-01"},
            }, base)
        if "offset=0" in url:
            return _response({"total_count": 3, "results": [{"year": "2023"}, {"year": "2024"}]}, url)
        if "offset=2" in url:
            return _response({"total_count": 3, "results": [{"year": "2025"}]}, url)
        raise AssertionError(url)

    result = acquire_snapshot(
        raw_root=tmp_path / "raw",
        manifest_root=tmp_path / "manifests",
        registry_path=registry,
        request_json=request,
        now=datetime(2026, 11, 2, tzinfo=timezone.utc),
    )
    assert result["total_record_count"] == 3
    assert result["page_count"] == 2
    assert len(calls) == 3
    raw = Path(result["raw_directory"])
    record_file = raw / "records_page_0001.json"
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    first_file = next(item for item in manifest["files"] if item["filename"] == record_file.name)
    assert first_file["sha256"] == hashlib.sha256(record_file.read_bytes()).hexdigest()
    assert json.loads((raw / "records_page_0002.json").read_text())["results"][0]["year"] == "2025"
    assert manifest["side_effects"]["database_written"] is False


def test_refuses_to_overwrite_existing_snapshot(tmp_path):
    registry = _registry(tmp_path / "registry.json")
    base = "https://data.gov.bh/api/explore/v2.1/catalog/datasets/03-unemployment-yearly"

    def request(url, timeout):
        if url == base:
            return _response({"dataset_id": "03-unemployment-yearly"}, url)
        return _response({"total_count": 1, "results": [{"year": "2025"}]}, url)

    kwargs = dict(
        raw_root=tmp_path / "raw",
        manifest_root=tmp_path / "manifests",
        registry_path=registry,
        request_json=request,
        now=datetime(2026, 11, 2, tzinfo=timezone.utc),
    )
    acquire_snapshot(**kwargs)
    with pytest.raises(BahrainAcquisitionError, match="Refusing to overwrite"):
        acquire_snapshot(**kwargs)


def test_rejects_changed_total_count_during_pagination(tmp_path):
    registry = _registry(tmp_path / "registry.json")
    base = "https://data.gov.bh/api/explore/v2.1/catalog/datasets/03-unemployment-yearly"

    def request(url, timeout):
        if url == base:
            return _response({"dataset_id": "03-unemployment-yearly"}, url)
        if "offset=0" in url:
            return _response({"total_count": 3, "results": [{"n": 1}, {"n": 2}]}, url)
        return _response({"total_count": 4, "results": [{"n": 3}]}, url)

    with pytest.raises(BahrainAcquisitionError, match="total_count changed"):
        acquire_snapshot(
            raw_root=tmp_path / "raw",
            manifest_root=tmp_path / "manifests",
            registry_path=registry,
            request_json=request,
            now=datetime(2026, 11, 2, tzinfo=timezone.utc),
        )


def test_rejects_registry_api_mismatch(tmp_path):
    registry = _registry(tmp_path / "registry.json")
    data = json.loads(registry.read_text())
    data["sources"]["bahrain_open_data"]["api"]["dataset_id"] = "other-dataset"
    registry.write_text(json.dumps(data))
    with pytest.raises(BahrainAcquisitionError, match="differ from the central source registry"):
        acquire_snapshot(registry_path=registry)
