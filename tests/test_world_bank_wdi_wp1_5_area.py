from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest

from tools import acquire_world_bank_wdi_wp1_5_area as area
from tools.database.source_crosswalk import CrosswalkError


G1 = "tc_" + "1" * 32


def fake_request(url):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if parsed.path.endswith("/sources/2"):
        payload = [{"page": 1, "pages": 1, "lastupdated": "2026-10-08"}, [
            {"id": "2", "name": "World Development Indicators"},
        ]]
    elif parsed.path.endswith("/country"):
        payload = [{"page": 1, "pages": 1, "total": 2}, [
            {"id": "USA", "name": "United States", "region": {"id": "NAC", "value": "North America"}},
            {"id": "WLD", "name": "World", "region": {"id": "NA", "value": "Aggregates"}},
        ]]
    elif "/indicator/" in parsed.path and "/country/all/" not in parsed.path:
        code = parsed.path.rsplit("/", 1)[-1]
        payload = [{"page": 1, "pages": 1, "lastupdated": "2026-10-08"}, [{
            "id": code, "name": {
                "EN.POP.DNST": "Population density (people per sq. km of land area)",
                "AG.SRF.TOTL.K2": "Surface area (sq. km)",
                "AG.LND.TOTL.K2": "Land area (sq. km)",
            }[code],
            "unit": "", "source": {"id": "2", "value": "World Development Indicators"},
            "sourceNote": area.INDICATORS[code]["meaning"],
            "sourceOrganization": "FAO; World Bank", "topics": [],
        }]]
    elif "/country/all/indicator/" in parsed.path:
        code = parsed.path.rsplit("/", 1)[-1]
        value = {"EN.POP.DNST": "36.5", "AG.SRF.TOTL.K2": "9833520", "AG.LND.TOTL.K2": "9161968"}[code]
        payload = [{"page": int(params["page"][0]), "pages": 1, "total": 2,
                    "lastupdated": "2026-10-08"}, [
            {"indicator": {"id": code, "value": code}, "country": {"id": "US", "value": "United States"},
             "countryiso3code": "USA", "date": "2024", "value": value, "obs_status": ""},
            {"indicator": {"id": code, "value": code}, "country": {"id": "1W", "value": "World"},
             "countryiso3code": "WLD", "date": "2024", "value": "100", "obs_status": ""},
        ]]
    else:
        raise AssertionError(url)
    return json.dumps(payload, separators=(",", ":")).encode(), 200, {
        "Content-Type": "application/json", "ETag": '"area-test"',
    }, url


def test_area_capture_is_separate_and_loads_complete_immutable_bundle(tmp_path):
    report = area.capture_snapshot(repository_root=tmp_path, start_year=2020, end_year=2025,
        retrieved_at="2026-11-21T07:00:00Z", request_get=fake_request)
    loaded = area.load_snapshot(report["manifest_path"], repository_root=tmp_path)
    assert report["artifact_count"] == 11
    assert loaded["manifest"]["download_id"] == "wdi_wp1_5_area"
    assert loaded["manifest"]["snapshot_scope"]["field_ids"] == [3, 33, 34]
    assert set(loaded["observations"]) == set(area.INDICATORS)
    assert loaded["observations"]["AG.SRF.TOTL.K2"][0]["value"] == "9833520"
    assert report["side_effects"]["game_database_written"] is False


def test_area_capture_refuses_overwrite(tmp_path):
    args = {"repository_root": tmp_path, "start_year": 2024, "end_year": 2024,
            "retrieved_at": "2026-11-21T07:00:00Z", "request_get": fake_request}
    area.capture_snapshot(**args)
    with pytest.raises(area.AreaSnapshotError, match="already exists"):
        area.capture_snapshot(**args)


def test_area_loader_rejects_raw_byte_mutation(tmp_path):
    report = area.capture_snapshot(repository_root=tmp_path, start_year=2024, end_year=2024,
        retrieved_at="2026-11-21T07:00:00Z", request_get=fake_request)
    manifest = json.loads((tmp_path / report["manifest_path"]).read_text())
    raw = tmp_path / manifest["files"][0]["local_raw_path"]
    raw.write_bytes(raw.read_bytes() + b" ")
    with pytest.raises(area.AreaSnapshotError, match="integrity mismatch"):
        area.load_snapshot(report["manifest_path"], repository_root=tmp_path)


def test_validation_uses_explicit_iso3_crosswalk_and_keeps_unmapped_candidates(tmp_path):
    report = area.capture_snapshot(repository_root=tmp_path, start_year=2024, end_year=2024,
        retrieved_at="2026-11-21T07:00:00Z", request_get=fake_request)
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"records": [{"game_id": G1}]}), encoding="utf-8")
    crosswalk = tmp_path / "crosswalk.json"
    crosswalk.write_text(json.dumps({
        "schema_version": 1, "dataset": "world_bank_wdi_wp1_5_area",
        "source_key": "world_bank_wdi",
        "mappings": [{"game_id": G1, "source_id": "USA",
            "match_method": "reviewed_manual", "evidence_url": "https://example.org/usa"}],
    }), encoding="utf-8")
    result = area.validate_candidates(report["manifest_path"], crosswalk, registry, repository_root=tmp_path)
    assert result["candidate_rows"] == 3
    assert result["coverage"]["EN.POP.DNST"]["mapped_candidate_count"] == 1
    assert result["coverage"]["EN.POP.DNST"]["unmapped_candidate_count"] == 0
    assert result["side_effects"]["canonical_database_written"] is False


def test_validation_rejects_crosswalk_dataset_mismatch(tmp_path):
    report = area.capture_snapshot(repository_root=tmp_path, start_year=2024, end_year=2024,
        retrieved_at="2026-11-21T07:00:00Z", request_get=fake_request)
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"records": [{"game_id": G1}]}), encoding="utf-8")
    crosswalk = tmp_path / "crosswalk.json"
    crosswalk.write_text(json.dumps({"schema_version": 1, "dataset": "wrong",
        "source_key": "world_bank_wdi", "mappings": [{
            "game_id": G1, "source_id": "USA", "match_method": "reviewed_manual"}]}), encoding="utf-8")
    with pytest.raises(CrosswalkError, match="dataset mismatch"):
        area.validate_candidates(report["manifest_path"], crosswalk, registry, repository_root=tmp_path)
