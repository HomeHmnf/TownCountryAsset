from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.acquire_world_bank_wdi_wp1_5_area import AreaSnapshotError, INDICATORS
from tools import normalize_world_bank_wdi_wp1_5_area as normalizer


@pytest.mark.parametrize("provider_status", [None, ""])
def test_blank_wdi_provider_status_is_unclassified(provider_status):
    assert normalizer._value_status(provider_status) == "unclassified"


@pytest.mark.parametrize("provider_status", ["E", "P", "A", "unknown"])
def test_nonblank_wdi_provider_status_requires_explicit_mapping(provider_status):
    with pytest.raises(AreaSnapshotError, match="requires an explicit canonical status mapping"):
        normalizer._value_status(provider_status)


def test_write_json_pair_does_not_overwrite_existing_second_destination(tmp_path):
    observations = tmp_path / "normalized.json"
    manifest = tmp_path / "manifest.json"
    manifest.write_text("preserve me", encoding="utf-8")

    with pytest.raises(AreaSnapshotError, match="Could not publish"):
        normalizer._write_json_pair(observations, {"rows": []}, manifest, {"sha": "x"})

    assert not observations.exists()
    assert manifest.read_text(encoding="utf-8") == "preserve me"
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob(".*.tmp"))


def test_write_json_pair_rolls_back_first_publication_if_second_fails(tmp_path, monkeypatch):
    observations = tmp_path / "normalized.json"
    manifest = tmp_path / "manifest.json"
    real_link = normalizer.os.link
    calls = 0

    def fail_second_link(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated second publication failure")
        return real_link(source, destination)

    monkeypatch.setattr(normalizer.os, "link", fail_second_link)
    with pytest.raises(AreaSnapshotError, match="simulated second publication failure"):
        normalizer._write_json_pair(observations, {"rows": []}, manifest, {"sha": "x"})

    assert not observations.exists()
    assert not manifest.exists()
    assert not list(tmp_path.glob(".*.tmp"))


def _iso3(index: int) -> str:
    return (
        chr(65 + index // 676)
        + chr(65 + (index // 26) % 26)
        + chr(65 + index % 26)
    )


def test_normalize_snapshot_emits_561_rows_and_complete_provenance(tmp_path, monkeypatch):
    root = tmp_path
    primary_path = root / "raw_data" / "wdi" / "source_metadata.json"
    primary_path.parent.mkdir(parents=True)
    primary_bytes = b'{"source":"World Bank"}'
    primary_path.write_bytes(primary_bytes)
    primary_sha = hashlib.sha256(primary_bytes).hexdigest()

    acquisition_path = root / "data_manifests" / "acquisition.json"
    acquisition_path.parent.mkdir(parents=True)
    acquisition_path.write_text('{"snapshot":"immutable"}', encoding="utf-8")
    acquisition_bytes = acquisition_path.read_bytes()

    artifacts = [{
        "local_raw_path": primary_path.relative_to(root).as_posix(),
        "sha256": primary_sha,
        "byte_count": len(primary_bytes),
    }]
    for index in range(7):
        artifacts.append({
            "local_raw_path": f"raw_data/wdi/extra_{index}.json",
            "sha256": f"{index + 1:064x}",
            "byte_count": index + 1,
        })

    acquisition = {
        "release": "api_snapshot_20261121",
        "source_url": "https://api.worldbank.org/v2",
        "final_url": "https://api.worldbank.org/v2",
        "retrieved_at": "2026-11-21T07:43:57Z",
        "attribution": "World Bank",
        "license_status": "review_required",
        "files": artifacts,
    }

    codes = [_iso3(index) for index in range(187)]
    mappings = [
        SimpleNamespace(source_id=code, game_id=f"tc_{index:032x}")
        for index, code in enumerate(codes)
    ]
    countries = {
        code: {"region": {"id": "ECS"}}
        for code in codes
    }
    observations = {}
    indicator_metadata = {}
    for code in INDICATORS:
        observations[code] = [
            {
                "countryiso3code": iso,
                "date": str(year),
                "value": float(index + year),
                "obs_status": None,
                "country": {"value": f"Country {index}"},
            }
            for index, iso in enumerate(codes)
            for year in (2023, 2024)
        ]
        indicator_metadata[code] = {
            "sourceOrganization": "World Bank",
            "sourceNote": f"Source note for {code}",
            "unit": "provider unit",
        }

    monkeypatch.setattr(
        normalizer,
        "load_snapshot",
        lambda *args, **kwargs: {
            "manifest": acquisition,
            "manifest_path": acquisition_path,
            "manifest_sha256": hashlib.sha256(acquisition_bytes).hexdigest(),
            "countries": countries,
            "indicator_metadata": indicator_metadata,
            "observations": observations,
        },
    )
    monkeypatch.setattr(
        normalizer,
        "load_crosswalk",
        lambda *args, **kwargs: SimpleNamespace(
            source_key=normalizer.SOURCE_KEY,
            mappings=mappings,
        ),
    )

    output = root / "normalized" / "observations.json"
    import_manifest = root / "normalized" / "manifest.json"
    result = normalizer.normalize_snapshot(
        "unused-acquisition-manifest.json",
        "unused-crosswalk.json",
        output,
        import_manifest,
        repository_root=root,
    )
    assert normalizer.SOURCE_KEY == "world_bank_wdi"

    normalized = json.loads(output.read_text(encoding="utf-8"))
    manifest = json.loads(import_manifest.read_text(encoding="utf-8"))
    assert result["observations"] == 561
    assert result["indicator_counts"] == {code: 187 for code in INDICATORS}
    assert len(normalized["observations"]) == 561
    assert {row["field_id"] for row in normalized["observations"]} == {
        spec["field_id"] for spec in INDICATORS.values()
    }
    assert {row["observation_period"] for row in normalized["observations"]} == {"2024"}
    assert {row["value_status"] for row in normalized["observations"]} == {"unclassified"}
    assert normalized["dataset"] == normalizer.CROSSWALK_DATASET
    assert manifest["source_key"] == normalizer.SOURCE_KEY
    assert manifest["dataset"] == normalizer.CROSSWALK_DATASET
    assert manifest["sha256"] == primary_sha
    assert len(manifest["additional_inputs"]) == 7
    assert manifest["upstream_manifests"] == [{
        "path": acquisition_path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(acquisition_bytes).hexdigest(),
    }]
    assert result["side_effects"]["canonical_database_written"] is False
    assert result["side_effects"]["approval_created"] is False
