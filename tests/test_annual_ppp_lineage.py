from __future__ import annotations

import csv

from tools import assess_annual_ppp_lineage as lineage


def _write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_icp_lineage_preserves_releases_and_only_documented_annual_roles(tmp_path):
    inspection = tmp_path / "inspection"
    benchmark = tmp_path / "benchmark"
    _write(inspection / "observations_long.csv", [
        {"source_release": "icp_2017_cycle", "country_code": "ZWE",
         "country_name": "Zimbabwe", "classification_code": "PPPGlob",
         "indicator_code": "1000000", "indicator_name": "GROSS DOMESTIC PRODUCT",
         "year": "2011", "value": "0.50", "observation_status": "reported_value",
         "source_file": "icp2017.csv", "source_row": "2"},
        {"source_release": "icp_2017_cycle", "country_code": "ZWE",
         "country_name": "Zimbabwe", "classification_code": "PPPGlob",
         "indicator_code": "1000000", "indicator_name": "GROSS DOMESTIC PRODUCT",
         "year": "2015", "value": "0.51", "observation_status": "reported_value",
         "source_file": "icp2017.csv", "source_row": "3"},
        {"source_release": "icp_2017_cycle", "country_code": "ZWE",
         "country_name": "Zimbabwe", "classification_code": "PPPGlob",
         "indicator_code": "1000000", "indicator_name": "GROSS DOMESTIC PRODUCT",
         "year": "2017", "value": "0.52", "observation_status": "reported_value",
         "source_file": "icp2017.csv", "source_row": "4"},
        {"source_release": "icp_2021_saved_report", "country_code": "ZWE",
         "country_name": "Zimbabwe", "classification_code": "PPPGlob",
         "indicator_code": "1000000", "indicator_name": "GROSS DOMESTIC PRODUCT",
         "year": "2018", "value": "0.53", "observation_status": "reported_value",
         "source_file": "icp2021.csv", "source_row": "5"},
        {"source_release": "icp_2021_saved_report", "country_code": "ZWE",
         "country_name": "Zimbabwe", "classification_code": "PPPGlob",
         "indicator_code": "1000000", "indicator_name": "GROSS DOMESTIC PRODUCT",
         "year": "2022", "value": "0.54", "observation_status": "reported_value",
         "source_file": "icp2021.csv", "source_row": "6"},
        {"source_release": "icp_2021_saved_report", "country_code": "ZWE",
         "country_name": "Zimbabwe", "classification_code": "PPPGlob",
         "indicator_code": "9100000", "indicator_name": "HOUSEHOLDS",
         "year": "2021", "value": "0.45", "observation_status": "reported_value",
         "source_file": "icp2021.csv", "source_row": "7"},
    ])
    _write(benchmark / "icp_2011_workbook_semantic_observations.csv", [
        {"table_id": "D3", "aggregate_key": "GDP", "country_code": "ZWE",
         "country_name_raw": "Zimbabwe", "value": "0.49", "unit": "LCU per intl dollar",
         "source_file": "icp2011.xlsx", "source_row": "56", "observation_status": "reported_value"},
        {"table_id": "D3", "aggregate_key": "AIC", "country_code": "ZWE",
         "country_name_raw": "Zimbabwe", "value": "0.40", "unit": "LCU per intl dollar",
         "source_file": "icp2011.xlsx", "source_row": "56", "observation_status": "reported_value"},
    ])

    rows = lineage._load_icp_rows(inspection, benchmark)
    by_release_year = {(row["source_release"], row["year"]): row for row in rows}
    assert by_release_year[("icp_2011_cycle", 2011)]["lineage_role"] == "original_2011_benchmark"
    assert by_release_year[("icp_2017_cycle", 2011)]["lineage_role"] == "revised_2011_benchmark"
    assert by_release_year[("icp_2017_cycle", 2015)]["lineage_role"] == "annual_series_role_not_inferred"
    assert by_release_year[("icp_2017_cycle", 2017)]["lineage_role"] == "original_2017_benchmark"
    assert by_release_year[("icp_2021_saved_report", 2018)]["lineage_role"] == "interpolation_per_ICP_2021_publication"
    assert by_release_year[("icp_2021_saved_report", 2022)]["lineage_role"] == "GDP_PPP_extrapolation_per_ICP_2021_publication"
    assert len(rows) == 6
    assert by_release_year[("icp_2017_cycle", 2011)]["value"] == 0.5


def test_weo_loader_keeps_ngdp_and_pppgdp_distinct_and_ignores_aggregates(tmp_path, monkeypatch):
    path = tmp_path / "weo.csv"
    _write(path, [
        {"SERIES_CODE": "ZWE.NGDP.A", "COUNTRY": "Zimbabwe", "UNIT": "Zimbabwe dollar",
         "SCALE": "Billions", "2015": "11", "2016": "12"},
        {"SERIES_CODE": "ZWE.PPPGDP.A", "COUNTRY": "Zimbabwe", "UNIT": "Purchasing power parity; billions of international dollars",
         "SCALE": "Billions", "2015": "22", "2016": "24"},
        {"SERIES_CODE": "ZWE.PPPEX.A", "COUNTRY": "Zimbabwe", "UNIT": "National currency per dollar",
         "SCALE": "Units", "2015": "0.123", "2016": "0.124"},
        {"SERIES_CODE": "WLD.NGDP.A", "COUNTRY": "World", "UNIT": "US dollar",
         "SCALE": "Billions", "2015": "100", "2016": "110"},
    ])
    monkeypatch.setattr(lineage.imf, "fingerprint", lambda *_args, **_kwargs: {})
    result = lineage._load_weo(path)

    assert result[("ZWE", 2015)]["NGDP"] == 11
    assert result[("ZWE", 2015)]["PPPGDP"] == 22
    assert result[("ZWE", 2015)]["PPPGDP_scale"] == "Billions"
    assert ("WLD", 2015) not in result
    assert ("ZWE", 2015) in result and "PPPEX" not in result[("ZWE", 2015)]
