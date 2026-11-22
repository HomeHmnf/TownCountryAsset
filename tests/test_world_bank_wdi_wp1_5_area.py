from __future__ import annotations

import hashlib
import json
from itertools import product
from string import ascii_uppercase
from urllib.parse import parse_qs, urlparse

import pytest

from tools import acquire_world_bank_wdi_wp1_5_area as area
from tools import normalize_world_bank_wdi_wp1_5_area as normalizer
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
        payload = [{"page": 1, "pages": 1, "total": 3}, [
            {"id": "USA", "name": "United States", "region": {"id": "NAC", "value": "North America"}},
            {"id": "CAN", "name": "Canada", "region": {"id": "NAC", "value": "North America"}},
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
        payload = [{"page": int(params["page"][0]), "pages": 1, "total": 3,
                    "lastupdated": "2026-10-08"}, [
            {"indicator": {"id": code, "value": code}, "country": {"id": "US", "value": "United States"},
             "countryiso3code": "USA", "date": "2024", "value": value, "obs_status": ""},
            {"indicator": {"id": code, "value": code}, "country": {"id": "CA", "value": "Canada"},
             "countryiso3code": "CAN", "date": "2024", "value": value, "obs_status": ""},
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
    assert report["artifact_count"] == 8
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
    assert result["candidate_rows"] == 6
    assert result["coverage"]["EN.POP.DNST"]["mapped_candidate_count"] == 1
    assert result["coverage"]["EN.POP.DNST"]["unmapped_candidate_count"] == 1
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

def test_normalizer_uses_crosswalk_dataset_not_acquisition_storage_key(tmp_path, monkeypatch):
    iso3_codes = [
        "".join(chars)
        for chars in product(ascii_uppercase, repeat=3)
    ][:187]
    mappings = [
        {
            "game_id": "tc_" + f"{index:032x}",
            "source_id": iso3,
            "match_method": "reviewed_manual",
        }
        for index, iso3 in enumerate(iso3_codes, start=1)
    ]
    crosswalk_path = tmp_path / "crosswalk.json"
    crosswalk_path.write_text(json.dumps({
        "schema_version": 1,
        "dataset": area.CROSSWALK_DATASET,
        "source_key": area.SOURCE_KEY,
        "mappings": mappings,
    }), encoding="utf-8")

    raw_root = tmp_path / "raw_data" / "sources" / "world_bank_wdi" / area.DATASET_KEY / "snapshot"
    artifact_names = [
        "source_metadata.json",
        "country_metadata_page_001.json",
        "indicator_metadata_EN.POP.DNST.json",
        "observations_EN.POP.DNST_page_001.json",
        "indicator_metadata_AG.SRF.TOTL.K2.json",
        "observations_AG.SRF.TOTL.K2_page_001.json",
        "indicator_metadata_AG.LND.TOTL.K2.json",
        "observations_AG.LND.TOTL.K2_page_001.json",
    ]
    artifacts = []
    for index, name in enumerate(artifact_names):
        raw_path = raw_root / name
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_bytes = f"captured artifact {index}".encode()
        raw_path.write_bytes(raw_bytes)
        artifacts.append({
            "local_raw_path": raw_path.relative_to(tmp_path).as_posix(),
            "sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "byte_count": len(raw_bytes),
        })

    acquisition_manifest_path = (
        tmp_path / "data_manifests" / "sources" / "world_bank_wdi"
        / area.DATASET_KEY / "snapshot.json"
    )
    acquisition_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    acquisition_manifest_path.write_text("{}", encoding="utf-8")
    acquisition = {
        "download_id": area.DATASET_KEY,
        "dataset_id": area.DATASET_KEY,
        "release": "api_snapshot_test",
        "source_url": "https://api.worldbank.org/v2",
        "final_url": "https://api.worldbank.org/v2",
        "retrieved_at": "2026-11-21T00:00:00Z",
        "attribution": "World Bank Group",
        "license_status": "review_required",
        "files": artifacts,
    }

    countries = {
        iso3: {"region": {"id": "NAC"}}
        for iso3 in iso3_codes
    }
    observations = {
        indicator: [
            {
                "countryiso3code": iso3,
                "date": "2024",
                "value": "12.5",
                "obs_status": "",
                "country": {"value": iso3},
            }
            for iso3 in iso3_codes
        ]
        for indicator in area.INDICATORS
    }
    indicator_metadata = {
        indicator: {
            "sourceOrganization": "FAO; World Bank",
            "sourceNote": "Captured provider methodology.",
            "unit": "",
        }
        for indicator in area.INDICATORS
    }
    loaded = {
        "manifest": acquisition,
        "manifest_path": acquisition_manifest_path,
        "manifest_sha256": "a" * 64,
        "countries": countries,
        "indicator_metadata": indicator_metadata,
        "observations": observations,
    }
    monkeypatch.setattr(normalizer, "load_snapshot", lambda *args, **kwargs: loaded)

    observations_path = tmp_path / "normalized" / "observations.json"
    import_manifest_path = tmp_path / "normalized" / "import_manifest.json"
    result = normalizer.normalize_snapshot(
        acquisition_manifest_path,
        crosswalk_path,
        observations_path,
        import_manifest_path,
        repository_root=tmp_path,
    )

    normalized = json.loads(observations_path.read_text(encoding="utf-8"))
    import_manifest = json.loads(import_manifest_path.read_text(encoding="utf-8"))
    assert normalized["dataset"] == area.CROSSWALK_DATASET
    assert import_manifest["dataset"] == area.CROSSWALK_DATASET
    assert normalized["source_key"] == import_manifest["source_key"] == area.SOURCE_KEY
    assert result["dataset"] == area.CROSSWALK_DATASET
    assert result["acquisition_dataset"] == area.DATASET_KEY
    assert result["observations"] == 187 * len(area.INDICATORS)

