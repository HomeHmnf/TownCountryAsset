from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from tools.acquire_world_bank_icp_2011_workbook import (
    SOURCE_URL, ICPWorkbookError, acquire_workbook,
)


def xlsx_bytes() -> bytes:
    stream = io.BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/workbook.xml", "<workbook/>")
        archive.writestr("xl/worksheets/sheet1.xml", "<worksheet/>")
    return stream.getvalue()


def fake_get(body=None, status=200):
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return body if body is not None else xlsx_bytes(), status, {
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }, url
    return get, calls


def test_acquires_and_manifests_original_workbook(tmp_path):
    fetch, calls = fake_get()
    result = acquire_workbook(
        repository_root=tmp_path,
        retrieved_at=datetime(2026, 11, 10, tzinfo=timezone.utc),
        get=fetch,
    )
    manifest = json.loads((tmp_path / result["manifest_path"]).read_text())
    artifact = manifest["files"][0]
    assert calls[0][0] == SOURCE_URL
    assert manifest["release"] == "icp_2011_cycle"
    assert manifest["release_kind"] == "original_benchmark_release"
    assert artifact["byte_count"] == result["workbook_bytes"]
    assert artifact["sha256"] == result["workbook_sha256"]
    assert (tmp_path / artifact["local_raw_path"]).read_bytes() == xlsx_bytes()
    assert result["side_effects"]["game_database_written"] is False


@pytest.mark.parametrize("body", [b"", b"not-xlsx", b"PK\x03\x04broken"])
def test_rejects_invalid_workbook_packages(tmp_path, body):
    fetch, _ = fake_get(body=body)
    with pytest.raises(ICPWorkbookError):
        acquire_workbook(repository_root=tmp_path, get=fetch)


def test_rejects_non_200_response(tmp_path):
    fetch, _ = fake_get(status=503)
    with pytest.raises(ICPWorkbookError, match="HTTP 503"):
        acquire_workbook(repository_root=tmp_path, get=fetch)


def test_requires_timezone_aware_capture_time(tmp_path):
    fetch, _ = fake_get()
    with pytest.raises(ValueError, match="timezone-aware"):
        acquire_workbook(repository_root=tmp_path, retrieved_at=datetime(2026, 11, 10),
                          get=fetch)
