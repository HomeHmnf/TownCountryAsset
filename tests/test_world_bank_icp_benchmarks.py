from __future__ import annotations

import csv

from openpyxl import Workbook

from tools.assess_world_bank_icp_benchmarks import (
    benchmark_role,
    compare,
    extract_workbook_semantics,
    country_name_index,
    column_code,
)


def _fixture(root):
    raw = root / "raw_data/sources/world_bank_icp"
    workbook_dir = raw / "icp_2011_cycle/acquisition"
    workbook_dir.mkdir(parents=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "D3 PPPs"
    sheet["A1"] = "TABLE D3 DETAILED RESULT: PPPs"
    sheet["A2"] = "Economy"
    sheet["B2"] = "Gross domestic product"
    sheet["C2"] = "Actual individual consumption"
    sheet["A3"] = "(00)"
    sheet["B3"] = "(01)"
    sheet["C3"] = "(02)"
    sheet["A4"] = "Zimbabwe"
    sheet["B4"] = 0.50
    sheet["C4"] = 0.40
    sheet["A5"] = "Unmapped Economy"
    sheet["B5"] = 0.60
    sheet["C5"] = 0.45

    summary = workbook.create_sheet("R1 GDP")
    summary["A1"] = "TABLE R1 SUMMARY RESULT: GDP"
    summary["A2"] = "Economy"
    summary["B2"] = "Expenditure based on PPPs"
    summary["A3"] = "(00)"
    summary["B3"] = "(01)"
    summary["A4"] = "Zimbabwe"
    summary["B4"] = 18.0

    path = workbook_dir / "2011-International-Comparison-Program-results.xlsx"
    workbook.save(path)
    workbook.close()

    metadata_dir = raw / "icp_2017_cycle/acquisition/contents"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "ICP_2017_Country-Metadata.csv").write_text(
        "Code,Long Name\nZWE,Zimbabwe\n",
        encoding="utf-8",
    )

    inspection = root / "reports/sources/world-bank-icp/inspection_20261110T090000Z"
    inspection.mkdir(parents=True)
    observations = [
        {
            "source_release": "icp_2017_cycle", "country_name": "Zimbabwe",
            "country_code": "ZWE", "classification_code": "PPPGlob",
            "indicator_code": "1000000", "indicator_name": "GROSS DOMESTIC PRODUCT",
            "year": "2011", "value": "0.52", "source_file": "icp2017.csv",
            "source_row": "2",
        },
        {
            "source_release": "icp_2017_cycle", "country_name": "Zimbabwe",
            "country_code": "ZWE", "classification_code": "PPPGlob",
            "indicator_code": "9020000", "indicator_name": "ACTUAL INDIVIDUAL CONSUMPTION",
            "year": "2011", "value": "0.44", "source_file": "icp2017.csv",
            "source_row": "3",
        },
        {
            "source_release": "icp_2017_cycle", "country_name": "Zimbabwe",
            "country_code": "ZWE", "classification_code": "PPPGlob",
            "indicator_code": "1000000", "indicator_name": "GROSS DOMESTIC PRODUCT",
            "year": "2017", "value": "0.51", "source_file": "icp2017.csv",
            "source_row": "4",
        },
        {
            "source_release": "icp_2021_saved_report", "country_name": "Zimbabwe",
            "country_code": "ZWE", "classification_code": "PPPGlob",
            "indicator_code": "1000000", "indicator_name": "GROSS DOMESTIC PRODUCT",
            "year": "2017", "value": "0.55", "source_file": "icp2021.csv",
            "source_row": "5",
        },
    ]
    with (inspection / "observations_long.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(observations[0]))
        writer.writeheader()
        writer.writerows(observations)
    return path


def test_extracts_table_specific_measures_and_only_exact_country_names(tmp_path):
    workbook = _fixture(tmp_path)
    rows = extract_workbook_semantics(workbook, country_name_index(tmp_path))

    gdp = next(row for row in rows if row["table_id"] == "D3" and row["column_code"] == "01")
    assert gdp["table_family"] == "ppp_conversion_factor"
    assert gdp["unit"] == "local currency units per international dollar (US$=1)"
    assert gdp["aggregate_key"] == "GDP"
    assert gdp["country_code"] == "ZWE"
    assert gdp["country_identity_status"] == "exact_unique_country_name_match"
    assert gdp["value"] == 0.5
    assert gdp["direct_ppp_comparison_candidate"] is True

    unmatched = next(row for row in rows if row["country_name_raw"] == "Unmapped Economy")
    assert unmatched["country_code"] == ""
    assert unmatched["country_identity_status"] == "no_exact_country_name_match"

    summary = next(row for row in rows if row["table_id"] == "R1")
    assert summary["measure_name"] == "Expenditure based on PPPs"
    assert summary["unit"] == "US dollars, billions"
    assert summary["aggregate_key"] == "GDP"
    assert summary["reference_year"] == 2011


def test_compares_original_and_revised_2011_and_2017_benchmarks(tmp_path):
    _fixture(tmp_path)
    result = compare(tmp_path)
    report = tmp_path / "reports/sources/world-bank-icp-benchmarks" / result["report_id"]
    with (report / "benchmark_comparisons.csv").open(encoding="utf-8", newline="") as stream:
        comparisons = list(csv.DictReader(stream))
    with (report / "icp_2011_workbook_semantic_observations.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        semantic = list(csv.DictReader(stream))

    original_2011 = [row for row in comparisons
                     if row["comparison_type"] == "original_2011_vs_revised_2011"]
    assert len(original_2011) == 2
    gdp = next(row for row in original_2011 if row["aggregate_key"] == "GDP")
    assert gdp["country_code"] == "ZWE"
    assert float(gdp["source_a_value"]) == 0.5
    assert float(gdp["source_b_value"]) == 0.52
    assert float(gdp["percent_difference"]) > 0

    revised_2017 = [row for row in comparisons
                    if row["comparison_type"] == "original_2017_vs_revised_2017"]
    assert len(revised_2017) == 1
    assert revised_2017[0]["source_a_role"] == "original_2017_benchmark"
    assert revised_2017[0]["source_b_role"] == "revised_2017_benchmark"
    assert float(revised_2017[0]["source_b_value"]) == 0.55

    assert result["workbook_table_count"] == 2
    assert result["original_2011_vs_revised_2011_comparison_count"] == 2
    assert result["original_2017_vs_revised_2017_comparison_count"] == 1
    assert any(row["country_identity_status"] == "no_exact_country_name_match"
               for row in semantic)



def test_benchmark_roles_do_not_mislabel_non_gdp_extrapolations():
    assert benchmark_role("icp_2017_cycle", 2011) == "revised_2011_benchmark"
    assert benchmark_role("icp_2017_cycle", 2017) == "original_2017_benchmark"
    assert benchmark_role(
        "icp_2021_saved_report", 2018, "GROSS DOMESTIC PRODUCT"
    ) == "interpolation_per_ICP_2021_publication"
    assert benchmark_role(
        "icp_2021_saved_report", 2021, "GROSS DOMESTIC PRODUCT"
    ) == "2021_benchmark"
    assert benchmark_role(
        "icp_2021_saved_report", 2022, "GROSS DOMESTIC PRODUCT"
    ) == "GDP_PPP_extrapolation_per_ICP_2021_publication"
    assert benchmark_role(
        "icp_2021_saved_report", 2022, "ACTUAL INDIVIDUAL CONSUMPTION"
    ) == "annual_series_role_not_inferred"



def test_column_code_parser_accepts_published_footnote_markers():
    assert column_code("(00)") == "00"
    assert column_code("(13)b") == "13"
    assert column_code("(10)a") == "10"
