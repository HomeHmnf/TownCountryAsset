from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest

from tools import acquire_world_bank_wdi_snapshot as snapshot


def _fake_request(url):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if parsed.path.endswith("/sources/2"):
        payload = [{"page": 1, "pages": 1, "lastupdated": "2026-10-01"}, [
            {"id": "2", "name": "World Development Indicators"},
        ]]
    elif parsed.path.endswith("/country"):
        payload = [{"page": 1, "pages": 1, "total": 2}, [
            {"id": "USA", "name": "United States", "region": {"id": "NAC", "value": "North America"}, "specialNotes": "Country metadata note", "incomeLevel": {"value": "High income"}},
            {"id": "WLD", "name": "World", "region": {"id": "NA", "value": "Aggregates"}},
        ]]
    elif "/country/all/indicator/" in parsed.path:
        code = parsed.path.rsplit("/", 1)[-1]
        payload = [{"page": int(params["page"][0]), "pages": 1, "total": 1, "lastupdated": "2026-10-01"}, [{
            "indicator": {"id": code, "value": f"Indicator {code}"},
            "country": {"id": "US", "value": "United States"},
            "countryiso3code": "USA", "date": "2024", "value": "123.5",
            "obs_status": "F" if code == "SL.UEM.TOTL.ZS" else "",
        }]]
    elif "/indicator/" in parsed.path:
        code = parsed.path.rsplit("/", 1)[-1]
        payload = [{"page": 1, "pages": 1, "lastupdated": "2026-10-01"}, [{
            "id": code, "name": f"Indicator {code}", "unit": "unit",
            "source": {"id": "2", "value": "World Development Indicators"},
            "sourceNote": "definition", "sourceOrganization": "Originating body", "topics": [],
        }]]
    else:
        raise AssertionError(f"Unexpected API URL: {url}")
    return json.dumps(payload, separators=(",", ":")).encode(), 200, {
        "Content-Type": "application/json", "ETag": '"snapshot-test"',
    }, url


def test_capture_and_load_preserve_complete_immutable_response_bundle(tmp_path):
    report = snapshot.capture_snapshot(
        repository_root=tmp_path, start_year=2024, end_year=2024,
        retrieved_at="2026-11-07T12:00:00Z", request_get=_fake_request,
    )
    loaded = snapshot.load_snapshot(tmp_path / report["manifest_path"], repository_root=tmp_path)
    assert report["artifact_count"] == 26
    assert report["side_effects"]["project_database_written"] is False
    assert loaded["start_year"] == 2024 and loaded["end_year"] == 2024
    assert set(loaded["observations"]) == set(snapshot.CAPTURE_INDICATORS)
    assert "PA.NUS.ATLS" in loaded["observations"]
    assert loaded["indicator_metadata"]["PA.NUS.PPP"]["sourceOrganization"] == "Originating body"
    assert loaded["country_regions"]["USA"]["special_notes"] == "Country metadata note"
    assert loaded["country_regions"]["USA"]["income_level"] == "High income"
    assert loaded["observations"]["NY.GDP.MKTP.CD"][0]["value"] == "123.5"
    assert loaded["observations"]["SL.UEM.TOTL.ZS"][0]["obs_status"] == "F"
    assert loaded["indicator_metadata"]["NY.GDP.MKTP.CD"]["sourceOrganization"] == "Originating body"
    assert loaded["indicator_metadata_api_metadata"]["NY.GDP.MKTP.CD"]["lastupdated"] == "2026-10-01"
    assert loaded["country_regions"]["USA"]["region_id"] == "NAC"
    assert loaded["country_regions"]["WLD"]["region_id"] == "NA"


def test_snapshot_loader_rejects_changed_raw_bytes(tmp_path):
    report = snapshot.capture_snapshot(
        repository_root=tmp_path, start_year=2024, end_year=2024,
        retrieved_at="2026-11-07T12:00:00Z", request_get=_fake_request,
    )
    manifest_path = tmp_path / report["manifest_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_path = tmp_path / manifest["files"][0]["local_raw_path"]
    raw_path.write_bytes(raw_path.read_bytes() + b" ")
    with pytest.raises(snapshot.SnapshotError, match="integrity mismatch"):
        snapshot.load_snapshot(manifest_path, repository_root=tmp_path)


def test_capture_refuses_snapshot_identity_overwrite(tmp_path):
    args = {
        "repository_root": tmp_path, "start_year": 2024, "end_year": 2024,
        "retrieved_at": "2026-11-07T12:00:00Z", "request_get": _fake_request,
    }
    snapshot.capture_snapshot(**args)
    with pytest.raises(snapshot.SnapshotError, match="already exists"):
        snapshot.capture_snapshot(**args)


def test_capture_rejects_non_wdi_indicator_metadata(tmp_path):
    def wrong_source(url):
        body, status, headers, final_url = _fake_request(url)
        if "/indicator/NY.GDP.MKTP.CD" in url:
            payload = json.loads(body)
            payload[1][0]["source"]["id"] = "3"
            body = json.dumps(payload).encode()
        return body, status, headers, final_url

    with pytest.raises(snapshot.SnapshotError, match="not confirmed as a WDI indicator"):
        snapshot.capture_snapshot(
            repository_root=tmp_path, start_year=2024, end_year=2024,
            retrieved_at="2026-11-07T12:00:00Z", request_get=wrong_source,
        )



def test_loader_remains_compatible_with_historical_six_indicator_snapshots(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "SUPPORTING_INDICATORS", ())
    monkeypatch.setattr(snapshot, "CAPTURE_INDICATORS", snapshot.INDICATORS)
    report = snapshot.capture_snapshot(
        repository_root=tmp_path, start_year=2024, end_year=2024,
        retrieved_at="2026-11-07T12:00:00Z", request_get=_fake_request,
    )
    loaded = snapshot.load_snapshot(tmp_path / report["manifest_path"], repository_root=tmp_path)
    assert set(loaded["observations"]) == set(snapshot.INDICATORS)
    assert not set(snapshot.SUPPORTING_INDICATORS) & set(loaded["observations"])


def test_loader_rejects_incomplete_optional_supporting_bundle(tmp_path):
    report = snapshot.capture_snapshot(
        repository_root=tmp_path, start_year=2024, end_year=2024,
        retrieved_at="2026-11-07T12:00:00Z", request_get=_fake_request,
    )
    manifest_path = tmp_path / report["manifest_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = [
        item for item in manifest["files"]
        if not item["filename"].startswith("observations_PA.NUS.PPP_")
    ]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(snapshot.SnapshotError, match="incomplete optional supporting indicator bundle"):
        snapshot.load_snapshot(manifest_path, repository_root=tmp_path)
