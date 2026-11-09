from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools.acquire_world_bank_icp_snapshot import (
    DATASET_ID, ICPSnapshotError, acquire_snapshot,
)


def fake_get_factory(tmp_path: Path, *, resources=None):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if url.endswith(f"/datasets/{DATASET_ID}"):
            body = json.dumps({"dataset_unique_id": DATASET_ID,
                               "identification": {"title": "ICP 2021"}}).encode()
            content_type = "application/json"
        elif "/resources?" in url:
            body = json.dumps({"count": len(resources or []), "data": resources or []}).encode()
            content_type = "application/json"
        elif url.endswith("/download"):
            body = b"PK\x03\x04ICP workbook bytes"
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            raise AssertionError(url)
        return body, 200, {"Content-Type": content_type}, url

    return fake_get, calls


def test_acquires_metadata_and_all_resources_with_fingerprints(tmp_path):
    resource = {"resource_unique_id": "DR0001", "title": "ICP_2021.xlsx",
                "format": "XLSX"}
    get, calls = fake_get_factory(tmp_path, resources=[resource])
    result = acquire_snapshot(
        repository_root=tmp_path,
        retrieved_at=datetime(2026, 11, 9, tzinfo=timezone.utc),
        request_get=get,
    )
    manifest_path = tmp_path / result["manifest_path"]
    manifest = json.loads(manifest_path.read_text())
    assert result["resource_count"] == 1
    assert len(manifest["files"]) == 3
    resource_record = manifest["files"][2]
    raw = tmp_path / resource_record["local_raw_path"]
    assert raw.read_bytes().startswith(b"PK")
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == resource_record["sha256"]
    assert len(calls) == 3
    assert result["side_effects"]["game_database_written"] is False


def test_rejects_partial_resource_listing(tmp_path):
    get, _ = fake_get_factory(tmp_path, resources=[])
    def partial(url, **kwargs):
        if "/resources?" in url:
            body = json.dumps({"count": 2, "data": [{"resource_unique_id": "DR1"}]}).encode()
            return body, 200, {"Content-Type": "application/json"}, url
        return get(url, **kwargs)
    with pytest.raises(ICPSnapshotError, match="Incomplete resource listing"):
        acquire_snapshot(repository_root=tmp_path,
                         retrieved_at=datetime(2026, 11, 9, tzinfo=timezone.utc),
                         request_get=partial)


def test_rejects_wrong_dataset_identity(tmp_path):
    get, _ = fake_get_factory(tmp_path)
    def wrong(url, **kwargs):
        body, status, headers, final = get(url, **kwargs)
        if url.endswith(f"/datasets/{DATASET_ID}"):
            body = b'{"dataset_unique_id":"wrong"}'
        return body, status, headers, final
    with pytest.raises(ICPSnapshotError, match="does not identify"):
        acquire_snapshot(repository_root=tmp_path,
                         retrieved_at=datetime(2026, 11, 9, tzinfo=timezone.utc),
                         request_get=wrong)


def test_refuses_existing_snapshot(tmp_path):
    raw = tmp_path / "raw_data/sources/world_bank_icp/icp_2021_cycle/icp_2021_20261109T000000000000Z"
    raw.mkdir(parents=True)
    with pytest.raises(ICPSnapshotError, match="already exists"):
        acquire_snapshot(repository_root=tmp_path,
                         retrieved_at=datetime(2026, 11, 9, tzinfo=timezone.utc),
                         request_get=lambda *a, **k: (_ for _ in ()).throw(AssertionError()))


def test_rejects_naive_timestamp(tmp_path):
    with pytest.raises(ValueError, match="timezone-aware"):
        acquire_snapshot(repository_root=tmp_path,
                         retrieved_at=datetime(2026, 11, 9),
                         request_get=lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
