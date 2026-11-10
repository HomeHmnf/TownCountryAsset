from __future__ import annotations

import csv
from pathlib import Path

from tools.assess_world_bank_icp_exports import inspect


def test_wide_databank_export_selects_latest_per_country_and_indicator(tmp_path):
    raw = tmp_path / "raw_data/sources/world_bank_icp/manual_exports"
    raw.mkdir(parents=True)
    path = raw / "icp_export.csv"
    headers = [
        "Classification Name", "Classification Code", "Time", "Time Code",
        "Country Name", "Country Code",
        "1000000:GROSS DOMESTIC PRODUCT [1000000]",
        "9020000:ACTUAL INDIVIDUAL CONSUMPTION [9020000]",
    ]
    rows = [
        ["Purchasing power parity", "PPPGlob", 2017, "YR2017", "Zimbabwe", "ZWE", "0.48", "0.43"],
        ["Purchasing power parity", "PPPGlob", 2021, "YR2021", "Zimbabwe", "ZWE", "0.62", ""],
        ["Purchasing power parity", "PPPGlob", 2023, "YR2023", "Example", "EXM", "1.2", "0.9"],
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)

    result = inspect(tmp_path)
    report = tmp_path / "reports/sources/world-bank-icp" / result["report_id"]
    with (report / "latest_available_by_country_indicator.csv").open(encoding="utf-8") as stream:
        latest = list(csv.DictReader(stream))
    zwe_gdp = next(row for row in latest if row["country_code"] == "ZWE"
                   and row["indicator_code"] == "1000000")
    zwe_aic = next(row for row in latest if row["country_code"] == "ZWE"
                   and row["indicator_code"] == "9020000")
    assert zwe_gdp["year"] == "2021"
    assert zwe_gdp["value"] == "0.62"
    assert zwe_aic["year"] == "2017"
    assert result["observation_count_including_missing"] == 6


def test_long_export_keeps_missing_rows_out_of_latest_selection(tmp_path):
    raw = tmp_path / "raw_data/sources/world_bank_icp/manual_exports"
    raw.mkdir(parents=True)
    path = raw / "long.csv"
    path.write_text(
        "Country,Country Code,Time,Classification,Classification Code,Series,Series Code,Value\n"
        "Zimbabwe,ZWE,2021,PPP,PPPGlob,GDP,1000000,\n"
        "Zimbabwe,ZWE,2017,PPP,PPPGlob,GDP,1000000,0.49\n",
        encoding="utf-8",
    )
    result = inspect(tmp_path)
    report = tmp_path / "reports/sources/world-bank-icp" / result["report_id"]
    with (report / "latest_available_by_country_indicator.csv").open(encoding="utf-8") as stream:
        latest = list(csv.DictReader(stream))
    assert len(latest) == 1
    assert latest[0]["year"] == "2017"



def test_cp1252_databank_csv_is_decoded_without_losing_country_names(tmp_path):
    raw = tmp_path / "raw_data/sources/world_bank_icp/manual_exports"
    raw.mkdir(parents=True)
    path = raw / "windows_1252.csv"
    path.write_bytes(
        "Country Name,Country Code,Time,Classification Code,"
        "1000000:GROSS DOMESTIC PRODUCT [1000000]\r\n"
        "Côte d’Ivoire,CIV,2021,PPPGlob,0.55\r\n".encode("cp1252")
    )

    result = inspect(tmp_path)
    report = tmp_path / "reports/sources/world-bank-icp" / result["report_id"]
    with (report / "observations_long.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1
    assert rows[0]["country_name"] == "Côte d’Ivoire"
    assert rows[0]["value"] == "0.55"
    assert rows[0]["sheet"] == "csv (cp1252)"



def test_databank_series_metadata_is_not_counted_as_observations_and_releases_are_separate(tmp_path):
    raw = tmp_path / "raw_data/sources/world_bank_icp/databank_exports/export_1/contents"
    raw.mkdir(parents=True)
    headers = [
        "Classification Name", "Classification Code", "Time", "Time Code",
        "Country Name", "Country Code",
        "1000000:GROSS DOMESTIC PRODUCT [1000000]",
    ]
    observations = [
        ["Purchasing power parity", "PPPGlob", 2017, "YR2017", "Zimbabwe", "ZWE", "0.49"],
        ["Purchasing power parity", "PPPGlob", 2021, "YR2021", "Zimbabwe", "ZWE", "0.54"],
        ["", "", "", "", "", "", ""],
        ["Data from database: ICP 2021", "", "", "", "", "", ""],
        ["Last Updated: 08/04/2024", "", "", "", "", "", ""],
    ]
    data_path = raw / "sample_Data.csv"
    with data_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(observations)
    metadata_path = raw / "sample_Series_-_Metadata.csv"
    with metadata_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(observations)
        writer.writerow(["Code", "Indicator Name", "", "", "", "", ""])
        writer.writerow(["1000000", "GDP definition", "", "", "", "", ""])

    result = inspect(tmp_path)
    report = tmp_path / "reports/sources/world-bank-icp" / result["report_id"]
    with (report / "observations_long.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    with (report / "series_metadata.csv").open(encoding="utf-8") as stream:
        definitions = list(csv.DictReader(stream))
    assert len(rows) == 2
    assert {row["source_release"] for row in rows} == {"icp_2021_saved_report"}
    assert len(definitions) == 1
    assert definitions[0]["indicator_code"] == "1000000"
    assert definitions[0]["indicator_definition"] == "GDP definition"
    assert result["observation_count_including_missing"] == 2
    assert result["series_metadata_definition_count"] == 1
    assert result["source_release_count"] == 1



def test_latest_selection_is_scoped_to_source_release(tmp_path):
    headers = [
        "Classification Name", "Classification Code", "Time", "Time Code",
        "Country Name", "Country Code",
        "1000000:GROSS DOMESTIC PRODUCT [1000000]",
    ]
    for release_dir, year, value in [
        ("icp_2017_cycle/export", 2017, "0.48"),
        ("icp_2021_cycle/export", 2021, "0.54"),
    ]:
        raw = tmp_path / "raw_data/sources/world_bank_icp" / release_dir
        raw.mkdir(parents=True)
        with (raw / "data.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(headers)
            writer.writerow(["PPP", "PPPGlob", year, f"YR{year}", "Zimbabwe", "ZWE", value])

    result = inspect(tmp_path)
    report = tmp_path / "reports/sources/world-bank-icp" / result["report_id"]
    with (report / "latest_available_by_country_indicator.csv").open(encoding="utf-8") as stream:
        latest = list(csv.DictReader(stream))
    assert len(latest) == 2
    assert {(row["source_release"], row["year"], row["value"]) for row in latest} == {
        ("icp_2017_cycle", "2017", "0.48"),
        ("icp_2021_cycle", "2021", "0.54"),
    }


def test_icp_2017_archive_wide_year_rows_preserve_missing_and_metadata(tmp_path):
    base = tmp_path / "raw_data/sources/world_bank_icp/icp_2017_cycle/acquisition/contents"
    base.mkdir(parents=True)
    data_path = base / "ICP_2017_Data.csv"
    headers = [
        "Country Name", "Country Code", "Classification Name", "Classification Code",
        "Series Name", "Series Code", "2011", "2012", "2013", "2014", "2015", "2016", "2017",
    ]
    with data_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerow([
            "Zimbabwe", "ZWE", "Expenditure (PPP)", "PPPGlob",
            "GROSS DOMESTIC PRODUCT", "1000000",
            "0.52", "..", "0.55", "", "0.54", "0.52", "0.51",
        ])

    country_path = base / "ICP_2017_Country-Metadata.csv"
    country_path.write_text(
        "Code,Long Name,ICP Participation,Currency Unit,System of National Accounts\n"
        "ZWE,Zimbabwe,Full participation,USD,2008 SNA\n",
        encoding="utf-8",
    )
    series_path = base / "ICP_2017_Series-Metadata.csv"
    series_path.write_text(
        "Code,Indicator Name\n1000000,GDP definition note\n",
        encoding="utf-8",
    )

    result = inspect(tmp_path)
    report = tmp_path / "reports/sources/world-bank-icp" / result["report_id"]
    with (report / "observations_long.csv").open(encoding="utf-8", newline="") as stream:
        observations = list(csv.DictReader(stream))
    with (report / "latest_available_by_country_indicator.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        latest = list(csv.DictReader(stream))
    with (report / "series_metadata.csv").open(encoding="utf-8", newline="") as stream:
        series = list(csv.DictReader(stream))
    with (report / "country_metadata.csv").open(encoding="utf-8", newline="") as stream:
        countries = list(csv.DictReader(stream))

    assert len(observations) == 7
    assert {row["source_release"] for row in observations} == {"icp_2017_cycle"}
    assert [row["year"] for row in observations] == [
        "2011", "2012", "2013", "2014", "2015", "2016", "2017"
    ]
    assert observations[1]["value"] == ""
    assert observations[1]["observation_status"] == "missing"
    assert len(latest) == 1
    assert latest[0]["year"] == "2017"
    assert latest[0]["indicator_name"] == "GROSS DOMESTIC PRODUCT"
    assert len(series) == 1
    assert series[0]["indicator_name"] == "GROSS DOMESTIC PRODUCT"
    assert series[0]["indicator_definition"] == "GDP definition note"
    assert len(countries) == 1
    assert countries[0]["code"] == "ZWE"
    assert countries[0]["currency_unit"] == "USD"
    assert result["country_metadata_row_count"] == 1
    assert result["observed_series_count"] == 1



def test_original_icp2011_workbook_is_inspected_without_false_observation_harmonization(tmp_path):
    from openpyxl import Workbook
    import json

    base = tmp_path / "raw_data/sources/world_bank_icp/icp_2011_cycle/acquisition"
    base.mkdir(parents=True)
    workbook = Workbook()
    summary = workbook.active
    summary.title = "R1 Summary"
    summary.append(["Country", "GDP PPP", "GDP PLI"])
    summary.append(["Zimbabwe", 0.52, 85.4])
    detail = workbook.create_sheet("D3 PPPs")
    detail.append(["Country", "Measure", "Unit", "Value"])
    detail.append(["Zimbabwe", "GDP", "US dollars per unit", 0.51])
    detail.append(["Example", "GDP", None, "US dollars per unit"])
    supplementary = workbook.create_sheet("S1 Supplementary")
    supplementary.append(["Notes", "Source"])
    supplementary.append(["Published table", "ICP 2011"])
    path = base / "2011-International-Comparison-Program-results.xlsx"
    workbook.save(path)
    workbook.close()

    result = inspect(tmp_path)
    report = tmp_path / "reports/sources/world-bank-icp" / result["report_id"]
    with (report / "icp_2011_workbook_sheets.csv").open(encoding="utf-8", newline="") as stream:
        sheets = list(csv.DictReader(stream))
    with (report / "icp_2011_workbook_cells.csv").open(encoding="utf-8", newline="") as stream:
        cells = list(csv.DictReader(stream))
    with (report / "icp_2011_workbook_rows.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    assert {row["source_release"] for row in sheets} == {"icp_2011_cycle"}
    assert [(row["sheet"], row["table_id"], row["table_category"]) for row in sheets] == [
        ("R1 Summary", "R1", "summary_results"),
        ("D3 PPPs", "D3", "detailed_results"),
        ("S1 Supplementary", "S1", "supplementary_results"),
    ]
    assert any(row["cell"] == "C2" and row["value"] == "85.4" for row in cells)
    detail_row = next(row for row in rows if row["sheet"] == "D3 PPPs" and row["source_row"] == "3")
    assert json.loads(detail_row["row_values_json"]) == [
        "Example", "GDP", "US dollars per unit", None
    ]
    assert result["icp_2011_workbook_sheet_count"] == 3
    assert result["icp_2011_workbook_nonempty_cell_count"] == len(cells)
    assert result["observation_count_including_missing"] == 0
    assert result["source_release_count"] == 1
    assert "icp_2011_cycle" in {
        row["source_release"] for row in sheets
    }
