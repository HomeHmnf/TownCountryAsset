from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone

import pytest

from tools.acquire_world_bank_icp_archive import (
    ARCHIVE_URL, EXPECTED_MEMBERS, ICPArchiveError, acquire_archive,
)


def make_archive(members=None):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as zipped:
        for name, body in (members or {
            "ICP_2017_Data.csv": b"Country Name,Country Code,2011,2017\\nZimbabwe,ZWE,0.52,0.51\\n",
            "ICP_2017_Country-Metadata.csv": b"Code,Long Name\\nZWE,Zimbabwe\\n",
            "ICP_2017_Series-Metadata.csv": b"Code,Indicator Name\\n1000000,GDP note\\n",
        }).items():
            zipped.writestr(name, body)
    return payload.getvalue()


def fake_get_factory(body=None):
    calls = []
    def fake_get(url, **kwargs):
        calls.append(url)
        payload = make_archive(body) if isinstance(body, dict) else (body or make_archive())
        return payload, 200, {"Content-Type": "application/zip"}, url
    return fake_get, calls


def test_acquires_archive_and_all_required_members_with_hashes(tmp_path):
    get, calls = fake_get_factory()
    result = acquire_archive(
        repository_root=tmp_path,
        retrieved_at=datetime(2026, 11, 10, tzinfo=timezone.utc),
        request_get=get,
    )
    manifest = json.loads((tmp_path / result["manifest_path"]).read_text())
    assert calls == [ARCHIVE_URL]
    assert manifest["source_id"] == "world_bank_icp"
    assert manifest["dataset_id"] == "0038406"
    assert manifest["release"] == "icp_2017_cycle"
    assert manifest["zip_crc_validation"] == "passed"
    assert {item["artifact_role"] for item in manifest["files"]} == {
        "original_export_archive", *EXPECTED_MEMBERS.values()
    }
    for item in manifest["files"]:
        path = tmp_path / item["local_raw_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    assert result["side_effects"]["game_database_written"] is False


def test_rejects_archive_missing_required_member(tmp_path):
    get, _ = fake_get_factory({"ICP_2017_Data.csv": b"data"})
    with pytest.raises(ICPArchiveError, match="missing required members"):
        acquire_archive(repository_root=tmp_path, request_get=get)


def test_rejects_unexpected_member(tmp_path):
    members = {name: b"x" for name in EXPECTED_MEMBERS}
    members["unexpected.csv"] = b"x"
    get, _ = fake_get_factory(members)
    with pytest.raises(ICPArchiveError, match="Unexpected archive member count"):
        acquire_archive(repository_root=tmp_path, request_get=get)


def test_rejects_invalid_zip(tmp_path):
    get, _ = fake_get_factory(b"not a zip")
    with pytest.raises(ICPArchiveError, match="not a ZIP"):
        acquire_archive(repository_root=tmp_path, request_get=get)


def test_rejects_naive_timestamp(tmp_path):
    get, _ = fake_get_factory()
    with pytest.raises(ValueError, match="timezone-aware"):
        acquire_archive(repository_root=tmp_path, retrieved_at=datetime(2026, 11, 10),
                        request_get=get)
