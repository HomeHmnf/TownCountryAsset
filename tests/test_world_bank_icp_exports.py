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
