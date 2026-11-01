from __future__ import annotations

import csv
import gzip
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

import tools.sources.wpp as wpp


GAME = "tc_" + "a" * 32
COLUMNS_DEMO = [
    "LocID", "ISO3_code", "LocTypeName", "VarID", "Variant", "Time",
    "TPopulation1July", "TPopulationMale1July", "TPopulationFemale1July",
    "PopGrowthRate", "MedianAgePop", "NetMigrations",
]
COLUMNS_AGE = [
    "LocID", "ISO3_code", "LocTypeName", "VarID", "Variant", "Time",
    "AgeGrp", "PopMale", "PopFemale", "PopTotal",
]


def _write_gzip_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _age_rows(loc_id: str, iso3: str, total: float) -> list[dict[str, str]]:
    per_sex = total / (2 * len(wpp.AGE_GROUPS))
    rows = []
    for age in wpp.AGE_GROUPS:
        male = per_sex
        female = per_sex
        rows.append({
            "LocID": loc_id, "ISO3_code": iso3, "LocTypeName": "Country/Area",
            "VarID": "2", "Variant": "Medium", "Time": "2026", "AgeGrp": age,
            "PopMale": str(male), "PopFemale": str(female), "PopTotal": str(male + female),
        })
    return rows


def _demo_row(loc_id: str, iso3: str, total: float) -> dict[str, str]:
    return {
        "LocID": loc_id, "ISO3_code": iso3, "LocTypeName": "Country/Area",
        "VarID": "2", "Variant": "Medium", "Time": "2026",
        "TPopulation1July": str(total), "TPopulationMale1July": str(total / 2),
        "TPopulationFemale1July": str(total / 2), "PopGrowthRate": "2.1",
        "MedianAgePop": "19.2", "NetMigrations": "-12.6",
    }


def _manifest(path: Path, download_id: str) -> Path:
    raw = path.read_bytes()
    manifest = {
        "manifest_schema_version": 1, "download_id": download_id,
        "source_url": "https://population.un.org/wpp/test",
        "final_url": "https://population.un.org/wpp/test",
        "retrieved_at": "2026-10-31T12:00:00+00:00",
        "local_raw_path": str(path.resolve()), "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "attribution": "United Nations DESA Population Division",
        "license_status": "CC BY 3.0 IGO",
    }
    target = path.with_suffix(path.suffix + ".manifest.json")
    target.write_text(json.dumps(manifest), encoding="utf-8")
    return target


def _inputs(tmp_path: Path):
    raw_root = tmp_path / "raw_data"
    demographic = raw_root / "demographic.csv.gz"
    age = raw_root / "age.csv.gz"
    togo_zip = raw_root / "togo.zip"
    _write_gzip_csv(
        demographic, COLUMNS_DEMO,
        [_demo_row("768", "TGO", 10000), _demo_row("124", "CAN", 40000)],
    )
    _write_gzip_csv(
        age, COLUMNS_AGE,
        _age_rows("768", "TGO", 10000) + _age_rows("124", "CAN", 40000),
    )
    togo_demo = [_demo_row("768", "TGO", 8800)]
    togo_age = _age_rows("768", "TGO", 8800)
    with zipfile.ZipFile(togo_zip, "w") as archive:
        for name, columns, rows in (
            ("WPP2024_Demographic_Indicators_Medium_Update.csv", COLUMNS_DEMO, togo_demo),
            ("WPP2024_PopulationByAge5GroupSex_Medium_Update.csv", COLUMNS_AGE, togo_age),
        ):
            import io
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
            archive.writestr(name, buffer.getvalue())
    manifests = [
        _manifest(demographic, "demographic_indicators_medium"),
        _manifest(age, "population_by_age_5_group_sex_medium"),
        _manifest(togo_zip, "interim_update_togo"),
    ]
    crosswalk = tmp_path / "crosswalk.json"
    crosswalk.write_text(json.dumps({
        "schema_version": 1, "dataset": "un_wpp", "source_key": "un_wpp",
        "mappings": [{
            "game_id": GAME, "source_id": "768", "match_method": "authoritative_identifier",
            "evidence_url": "https://unstats.un.org/unsd/methodology/m49/",
        }],
    }), encoding="utf-8")
    return demographic, manifests[0], age, manifests[1], togo_zip, manifests[2], crosswalk


def test_prepares_1_july_candidate_and_uses_togo_interim_only_for_togo(tmp_path, monkeypatch):
    monkeypatch.setattr(wpp, "REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(wpp, "EXPECTED_COUNTRY_AREA_COUNT", 2)
    inputs = _inputs(tmp_path)
    output = tmp_path / "candidate"
    result = wpp.prepare_un_wpp(
        demographic_path=inputs[0], demographic_manifest_path=inputs[1],
        age_path=inputs[2], age_manifest_path=inputs[3],
        togo_zip_path=inputs[4], togo_manifest_path=inputs[5],
        crosswalk_path=inputs[6], output_dir=output,
    )

    normalized = json.loads((output / "normalized_observations.json").read_text())
    manifest = json.loads((output / "application_manifest.json").read_text())
    assert result["source_country_area_count"] == 2
    assert result["crosswalk_mapped_count"] == 1
    assert result["crosswalk_unmapped_count"] == 1
    assert result["togo_supplement_applied"] is True
    assert result["sqlite_written"] is False
    assert len(normalized["observations"]) == 6

    by_field = {row["field_id"]: row for row in normalized["observations"]}
    assert by_field[1]["value"] == pytest.approx(8_800_000)
    assert by_field[1]["value_status"] == "projected"
    assert by_field[2]["value"] == pytest.approx(2.1)
    assert by_field[6]["value"] == pytest.approx(19.2)
    assert by_field[14]["value"] == pytest.approx(-12_600)
    assert by_field[13]["value"] == pytest.approx({"male": 4_400_000, "female": 4_400_000})
    assert len(by_field[12]["value"]) == 21
    assert by_field[12]["value"][0]["age_band"] == "0-4"
    assert len(manifest["additional_inputs"]) == 2
    assert len(manifest["upstream_manifests"]) == 3
    assert manifest["release"] == "2024-main-demographic+2026-01-19-togo-update"


def test_rejects_togo_supplement_with_non_togo_country(tmp_path, monkeypatch):
    monkeypatch.setattr(wpp, "REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(wpp, "EXPECTED_COUNTRY_AREA_COUNT", 2)
    inputs = list(_inputs(tmp_path))
    bad_zip = tmp_path / "raw_data" / "bad-togo.zip"
    with zipfile.ZipFile(bad_zip, "w") as archive:
        for name, columns, rows in (
            ("WPP2024_Demographic_Indicators_Medium_Update.csv", COLUMNS_DEMO, [_demo_row("124", "CAN", 40000)]),
            ("WPP2024_PopulationByAge5GroupSex_Medium_Update.csv", COLUMNS_AGE, _age_rows("124", "CAN", 40000)),
        ):
            import io
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
            archive.writestr(name, buffer.getvalue())
    inputs[4] = bad_zip
    inputs[5] = _manifest(bad_zip, "interim_update_togo")
    with pytest.raises(wpp.WPPAdapterError, match="Togo supplement must contain Togo"):
        wpp.prepare_un_wpp(
            demographic_path=inputs[0], demographic_manifest_path=inputs[1],
            age_path=inputs[2], age_manifest_path=inputs[3],
            togo_zip_path=inputs[4], togo_manifest_path=inputs[5],
            crosswalk_path=inputs[6], output_dir=tmp_path / "candidate",
        )
