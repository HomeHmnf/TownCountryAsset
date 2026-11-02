from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from tools import compare_imf_weo_wdi as compare


def _inputs(tmp_path, monkeypatch):
    identity = tmp_path / "identity.json"
    identity.write_text(json.dumps({"records": [{
        "game_id": "tc_123", "iso": {"alpha3": "USA"},
        "source": {"current_source_id": "USA"},
        "names": {"en": "United States", "aliases_en": []},
    }]}), encoding="utf-8")
    csv_path = tmp_path / "weo.csv"
    rows = []
    for code in ("NGDPD", "NGDPDPC", "PPPGDP", "PCPIPCH", "LUR"):
        rows.append({
            "SERIES_CODE": f"USA.{code}.A", "COUNTRY": "United States",
            "FREQUENCY": "Annual",
            "UNIT": "US dollar" if code in {"NGDPD", "NGDPDPC"} else ("Percent" if code == "PCPIPCH" else ""),
            "SCALE": "Billions" if code in {"NGDPD", "PPPGDP"} else "Units",
            "LATEST_ACTUAL_ANNUAL_DATA": "" if code == "PPPGDP" else "2024",
            "START_END_MONTHS_OF_REPORTING_YEAR": "January/December",
            "2024": "2" if code in {"NGDPD", "NGDPDPC", "PPPGDP"} else "3",
        })
    fields = list(rows[0])
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    monkeypatch.setattr(compare.imf, "ROOT", tmp_path)
    monkeypatch.setattr(compare.imf, "EXPECTED", {
        "csv": (hashlib.sha256(csv_path.read_bytes()).hexdigest(), csv_path.stat().st_size),
    })
    monkeypatch.setattr(compare.imf, "CSV_PATH", csv_path)
    monkeypatch.setattr(compare.imf, "IDENTITY", identity)
    return csv_path, identity


def _fake_api(url):
    parsed = urlparse(url)
    if parsed.path.endswith("/country"):
        return [{"pages": 1}, [
            {"id": "USA", "region": {"id": "NAC", "value": "North America"}},
            {"id": "WLD", "region": {"id": "NA", "value": "Aggregates"}},
        ]]
    if "/indicator/" in parsed.path and "/country/" not in parsed.path:
        code = parsed.path.rsplit("/", 1)[-1]
        return [None, [{
            "id": code, "name": f"Indicator {code}", "unit": "test unit",
            "sourceNote": "definition note", "sourceOrganization": "National sources",
            "source": {"id": "2", "value": "WDI"},
            "topics": [],
        }]]
    code = parsed.path.rsplit("/", 1)[-1]
    value = {
        "NY.GDP.MKTP.CD": "2000000000",
        "NY.GDP.PCAP.CD": "2",
        "NY.GDP.MKTP.PP.CD": "2000000000",
        "FP.CPI.TOTL.ZG": "3",
        "SL.UEM.TOTL.ZS": "3",
    }[code]
    return [{"pages": 1}, [{
        "country": {"id": "US", "value": "United States"},
        "countryiso3code": "USA", "date": "2024", "value": value,
    }, {
        "country": {"id": "1W", "value": "World"},
        "countryiso3code": "WLD", "date": "2024", "value": "999",
    }]]


def test_comparison_joins_via_game_identity_and_scales_billions(tmp_path, monkeypatch):
    csv_path, identity = _inputs(tmp_path, monkeypatch)
    report = compare.build_comparison(csv_path, identity, 2024, 2024, _fake_api)
    assert len(report["indicators"]) == 5
    gdp = next(item for item in report["indicators"] if item["field_id"] == 15)
    row = gdp["country_year_comparisons"][0]
    assert row["game_id"] == "tc_123"
    assert row["imf_value_canonical_unit"] == 2_000_000_000
    assert row["wdi_value_canonical_unit"] == 2_000_000_000
    assert row["relative_difference_percent"] == 0
    assert gdp["matched_country_year_count"] == 1
    assert row["imf_status_hint"] == "actual_per_weo_metadata"
    assert report["side_effects"]["canonical_database_written"] is False
    assert report["side_effects"]["source_selection_policy_changed"] is False


def test_signed_and_absolute_differences_are_distinct(tmp_path, monkeypatch):
    csv_path, identity = _inputs(tmp_path, monkeypatch)

    def api_with_larger_wdi_gdp(url):
        response = _fake_api(url)
        if urlparse(url).path.endswith("/NY.GDP.MKTP.CD"):
            response[1][0]["value"] = "2100000000"
        return response

    report = compare.build_comparison(csv_path, identity, 2024, 2024, api_with_larger_wdi_gdp)
    gdp = next(item for item in report["indicators"] if item["field_id"] == 15)
    row = gdp["country_year_comparisons"][0]
    assert row["signed_difference"] == -100_000_000
    assert row["absolute_difference"] == 100_000_000
    assert row["relative_difference_percent"] < 0
    assert row["absolute_relative_difference_percent"] > 0
    assert gdp["country_years_over_20_percent_difference"] == 0
    assert gdp["calendar_year_sensitivity"]["matched_country_year_count"] == 1


def test_fiscal_year_rows_are_excluded_from_calendar_sensitivity(tmp_path, monkeypatch):
    csv_path, identity = _inputs(tmp_path, monkeypatch)
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        if row["SERIES_CODE"] == "USA.NGDPD.A":
            row["START_END_MONTHS_OF_REPORTING_YEAR"] = "April/March"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    monkeypatch.setattr(compare.imf, "EXPECTED", {
        "csv": (hashlib.sha256(csv_path.read_bytes()).hexdigest(), csv_path.stat().st_size),
    })

    report = compare.build_comparison(csv_path, identity, 2024, 2024, _fake_api)
    gdp = next(item for item in report["indicators"] if item["field_id"] == 15)
    row = gdp["country_year_comparisons"][0]
    assert row["imf_reporting_period_classification"] == "non_calendar_fiscal_year"
    assert gdp["imf_reporting_period_counts"]["non_calendar_fiscal_year"] == 1
    assert gdp["calendar_year_sensitivity"]["matched_country_year_count"] == 0
    assert gdp["calendar_year_sensitivity"]["excluded_non_calendar_fiscal_year_count"] == 1


def test_ppp_and_unemployment_status_are_not_inferred(tmp_path, monkeypatch):
    csv_path, identity = _inputs(tmp_path, monkeypatch)
    report = compare.build_comparison(csv_path, identity, 2024, 2024, _fake_api)
    ppp = next(item for item in report["indicators"] if item["field_id"] == 18)
    lur = next(item for item in report["indicators"] if item["field_id"] == 21)
    assert ppp["country_year_comparisons"][0]["imf_status_hint"] == "status_unclassified"
    assert lur["wdi_metadata"]["source_note"] == "definition note"
    assert lur["country_year_comparisons"][0]["wdi_status"] == "not_classified_by_this_comparison"


def test_report_writer_creates_machine_readable_and_csv_outputs(tmp_path, monkeypatch):
    csv_path, identity = _inputs(tmp_path, monkeypatch)
    report = compare.build_comparison(csv_path, identity, 2024, 2024, _fake_api)
    target = compare.write_reports(report, tmp_path / "reports")
    assert (target / "assessment.json").is_file()
    assert (target / "assessment.md").is_file()
    text = (target / "country_year_comparison.csv").read_text()
    assert "tc_123" in text
    assert "NY.GDP.MKTP.CD" in text
