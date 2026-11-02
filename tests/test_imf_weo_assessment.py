from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from tools import assess_imf_weo as imf


def _write_csv(path: Path) -> None:
    fields = [
        "SERIES_CODE", "COUNTRY", "INDICATOR", "FREQUENCY", "UNIT", "SCALE",
        "LATEST_ACTUAL_ANNUAL_DATA", "START_END_MONTHS_OF_REPORTING_YEAR",
        "2024", "2025", "2026",
    ]
    rows = []
    for code in imf.INDICATORS:
        rows.append({
            "SERIES_CODE": f"USA.{code}.A", "COUNTRY": "United States",
            "INDICATOR": code, "FREQUENCY": "Annual",
            "UNIT": "US dollar" if code in {"NGDPD", "NGDPDPC"} else ("Percent" if code == "PCPIPCH" else ""),
            "SCALE": "Billions" if code in {"NGDPD", "PPPGDP"} else "Units",
            "LATEST_ACTUAL_ANNUAL_DATA": "2025" if code != "PPPGDP" else "",
            "START_END_MONTHS_OF_REPORTING_YEAR": "January/December",
            "2024": "10.5", "2025": "11.5", "2026": "",
        })
    rows.extend([
        {"SERIES_CODE": "G001.NGDPD.A", "COUNTRY": "World", "INDICATOR": "GDP",
         "FREQUENCY": "Annual", "UNIT": "US dollar", "SCALE": "Billions",
         "LATEST_ACTUAL_ANNUAL_DATA": "", "START_END_MONTHS_OF_REPORTING_YEAR": "",
         "2024": "100", "2025": "110", "2026": "120"},
        {"SERIES_CODE": "USA.NGDPD.A", "COUNTRY": "United States", "INDICATOR": "GDP",
         "FREQUENCY": "Annual", "UNIT": "US dollar", "SCALE": "Billions",
         "LATEST_ACTUAL_ANNUAL_DATA": "2025", "START_END_MONTHS_OF_REPORTING_YEAR": "January/December",
         "2024": "10.5", "2025": "11.5", "2026": ""},
    ])
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def assessment_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(imf, "ROOT", tmp_path)
    identity = tmp_path / "identity.json"
    identity.write_text(json.dumps({"records": [{
        "game_id": "tc_123", "iso": {"alpha3": "USA"},
        "source": {"current_source_id": "USA"},
        "names": {"en": "United States", "aliases_en": ["United States of America"]},
    }]}), encoding="utf-8")
    policy = tmp_path / "source_selection.json"
    policy.write_text("{}", encoding="utf-8")
    registry = tmp_path / "data_sources.json"
    registry.write_text("{}", encoding="utf-8")
    csv_path = tmp_path / "weo.csv"
    _write_csv(csv_path)
    pdf_path = tmp_path / "appendix.pdf"
    pdf_path.write_bytes(b"appendix fixture")
    monkeypatch.setattr(imf, "IDENTITY", identity)
    monkeypatch.setattr(imf, "POLICY", policy)
    monkeypatch.setattr(imf, "REGISTRY", registry)
    monkeypatch.setattr(imf, "EXPECTED", {
        "csv": (hashlib.sha256(csv_path.read_bytes()).hexdigest(), csv_path.stat().st_size),
        "appendix": (hashlib.sha256(pdf_path.read_bytes()).hexdigest(), pdf_path.stat().st_size),
    })
    return csv_path, pdf_path, identity


def test_assessment_maps_identity_and_excludes_aggregate_prefix(assessment_inputs):
    csv_path, pdf_path, identity = assessment_inputs
    report = imf.build_assessment(csv_path, pdf_path, 2024, 2026, identity)
    gdp = next(item for item in report["indicators"] if item["indicator_code"] == "NGDPD")
    assert gdp["series_count"] == 3
    assert gdp["unique_series_count"] == 2
    assert gdp["duplicate_series_codes"] == ["USA.NGDPD.A"]
    assert gdp["registry_code_match_count"] == 1
    assert gdp["registry_name_match_count"] == 1
    assert gdp["non_iso_aggregate_prefixes"] == ["G001"]
    assert gdp["populated_observations_by_year"] == {"2024": 2, "2025": 2, "2026": 1}
    assert report["wdi_comparison"]["status"] == "not_assessed"
    assert report["side_effects"]["canonical_database_written"] is False
    assert report["side_effects"]["release_promoted"] is False


def test_latest_actual_metadata_and_unresolved_ppp_status_are_preserved(assessment_inputs):
    csv_path, pdf_path, identity = assessment_inputs
    report = imf.build_assessment(csv_path, pdf_path, 2024, 2026, identity)
    ppp = next(item for item in report["indicators"] if item["indicator_code"] == "PPPGDP")
    assert ppp["latest_actual_annual_data_distribution"] == {"(blank)": 1}
    assert ppp["unit_contract"] == "not_supplied_requires_review"
    lur = next(item for item in report["indicators"] if item["indicator_code"] == "LUR")
    assert lur["unit_contract"] == "not_supplied_requires_review"


def test_rejects_changed_manual_snapshot(assessment_inputs):
    csv_path, pdf_path, identity = assessment_inputs
    csv_path.write_text(csv_path.read_text(encoding="utf-8-sig"), encoding="utf-8")
    with pytest.raises(imf.AssessmentError, match="differs from recorded"):
        imf.build_assessment(csv_path, pdf_path, 2024, 2026, identity)


def test_report_writer_creates_machine_and_human_readable_outputs(assessment_inputs, tmp_path):
    csv_path, pdf_path, identity = assessment_inputs
    report = imf.build_assessment(csv_path, pdf_path, 2024, 2026, identity)
    target = imf.write_reports(report, tmp_path / "reports")
    assert (target / "assessment.json").is_file()
    assert (target / "assessment.md").is_file()
    assert (target / "country_coverage.csv").is_file()
    assert (target / "series_rows.csv").is_file()
