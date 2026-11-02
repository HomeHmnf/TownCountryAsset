from __future__ import annotations

import csv

import pytest

from tools import investigate_imf_weo_wdi_discrepancies as investigate


def _row(field=15, country="Guinea", year=2015, imf=13.0, wdi=10.0):
    signed = imf - wdi
    relative = signed / wdi * 100
    return {
        "field_id": field, "wdi_indicator": "NY.GDP.MKTP.CD",
        "imf_indicator": "NGDPD", "game_id": "tc_123", "year": year,
        "imf_country": country, "wdi_country": country, "imf_source_code": "GIN",
        "wdi_iso3": "GIN", "imf_value_canonical_unit": imf,
        "wdi_value_canonical_unit": wdi, "signed_difference": signed,
        "absolute_difference": abs(signed),
        "relative_difference_percent": relative,
        "absolute_relative_difference_percent": abs(relative),
        "imf_status_hint": "actual_per_weo_metadata",
        "imf_latest_actual_annual_data": "2024",
        "imf_reporting_year_months": "January/December",
        "imf_reporting_period_classification": "calendar_year",
        "wdi_status": "not_classified_by_this_comparison",
    }


def test_reads_and_validates_comparison_csv(tmp_path):
    path = tmp_path / "comparison.csv"
    row = _row()
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    rows = investigate.read_comparisons(path)
    assert len(rows) == 1
    assert rows[0]["signed_difference"] == 3
    assert rows[0]["absolute_difference"] == 3


def test_rejects_inconsistent_difference_formula(tmp_path):
    path = tmp_path / "comparison.csv"
    row = _row()
    row["absolute_difference"] = 99
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    with pytest.raises(investigate.InvestigationError, match="Absolute difference mismatch"):
        investigate.read_comparisons(path)


def test_investigation_reports_persistent_direction_and_year_values():
    rows = [_row(year=year, imf=13 + year - 2015, wdi=10 + year - 2015) for year in range(2015, 2018)]
    report = investigate.build_investigation(rows)
    item = next(x for x in report["investigations"] if x["field_id"] == 15 and x["country"] == "Guinea")
    assert item["observation_count"] == 3
    assert item["direction"] == "IMF consistently higher"
    assert [x["year"] for x in item["observations"]] == [2015, 2016, 2017]
    assert report["side_effects"]["canonical_database_written"] is False


def test_reports_targets_not_present():
    report = investigate.build_investigation([])
    assert report["selected_country_field_groups"] == 0
    assert len(report["targets_not_found"]) == sum(len(x) for x in investigate.TARGETS.values())


def test_writer_creates_json_markdown_and_csv(tmp_path):
    report = investigate.build_investigation([_row()])
    target = investigate.write_reports(report, tmp_path)
    assert (target / "assessment.json").is_file()
    assert (target / "assessment.md").is_file()
    assert (target / "targeted_country_years.csv").is_file()
