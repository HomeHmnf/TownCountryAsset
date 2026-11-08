from __future__ import annotations

import csv

import pytest

from tools import assess_wdi_macro_decomposition as assessment
from tools import acquire_world_bank_wdi_snapshot as snapshot


def _record(code, year, value, status=""):
    return {
        "indicator": {"id": code},
        "country": {"id": "US", "value": "United States"},
        "countryiso3code": "USA",
        "date": str(year),
        "value": str(value) if value is not None else None,
        "obs_status": status,
    }


def _fixture_snapshot():
    codes = (*assessment.BASE_CODES, *assessment.SUPPORTING)
    observations = {code: [] for code in codes}
    values = {
        "NY.GDP.MKTP.CD": 100,
        "NY.GDP.PCAP.CD": 10,
        "NY.GDP.MKTP.PP.CD": 40,
        "FP.CPI.TOTL.ZG": 10,
        "SL.UEM.TOTL.ZS": 5,
        "NY.GDP.MKTP.CN": 200,
        "PA.NUS.FCRF": 2,
        "PA.NUS.ATLS": 4,
        "PA.NUS.PPP": 5,
        "SP.POP.TOTL": 10,
        "FP.CPI.TOTL": 110,
    }
    for code in codes:
        observations[code].append(_record(code, 2024, values[code], "F" if code == "SP.POP.TOTL" else ""))
    observations["FP.CPI.TOTL"].append(_record("FP.CPI.TOTL", 2023, 100))
    return {
        "manifest": {"snapshot_id": "test-snapshot", "retrieved_at": "2026-11-08T00:00:00Z"},
        "manifest_sha256": "a" * 64,
        "country_regions": {
            "USA": {
                "region_id": "NAC", "region_value": "North America",
                "special_notes": "Example note", "income_level": "High income",
                "lending_type": "Not classified", "capital_city": "Washington D.C.",
            }
        },
        "indicator_metadata": {
            code: {"name": f"Name {code}", "unit": "test unit", "sourceNote": "definition", "sourceOrganization": "WB"}
            for code in codes
        },
        "indicator_metadata_api_metadata": {code: {"lastupdated": "2026-10-08"} for code in codes},
        "observations": observations,
    }


def test_decomposition_reconstructs_wdi_arithmetic_without_approving_identity():
    snapshot_data = _fixture_snapshot()
    imf_data = {
        "NGDPD": {("g1", 2024): {"value": 120}},
        "NGDPDPC": {("g1", 2024): {"value": 12}},
        "PPPGDP": {("g1", 2024): {"value": 50}},
        "PCPIPCH": {("g1", 2024): {"value": 11}},
    }
    countries = [{
        "game_id": "g1", "country_name": "Example", "source_lookup_code": "USA",
        "identity_mapping_status": "mapped_review_required",
    }]
    result = assessment.assess_snapshot(
        snapshot_data, imf_data, countries, start_year=2024, end_year=2024,
    )
    row = result["rows"][0]
    assert result["row_count"] == 1
    assert row["wdi_gdp_current_usd_implied_official_fx"] == 100
    assert row["wdi_gdp_current_usd_implied_alternative_factor"] == 50
    assert row["imf_ngdpd_implied_conversion_factor_lcu_per_usd"] == pytest.approx(200 / 120)
    assert row["wdi_gdp_current_ppp_implied_from_lcu"] == 40
    assert row["wdi_gdp_per_capita_implied_from_usd_and_population"] == 10
    assert row["wdi_cpi_index_yoy_percent_diagnostic"] == pytest.approx(10)
    assert row["wdi_ppp_vs_lcu_factor_implied_relative_difference_percent"] == 0
    assert row["wdi_gdp_per_capita_vs_gdp_population_implied_relative_difference_percent"] == 0
    assert row["wdi_inflation_vs_cpi_index_yoy_difference_percentage_points"] == pytest.approx(0)
    assert row["status_SP.POP.TOTL"] == "F"
    assert row["identity_gate"] == "blocking"
    assert row["identity_mapping_status"] == "mapped_review_required"
    assert result["side_effects"]["game_database_written"] is False


def test_decomposition_keeps_missing_or_zero_denominators_uncomputed():
    snapshot_data = _fixture_snapshot()
    snapshot_data["observations"]["PA.NUS.FCRF"][0]["value"] = "0"
    snapshot_data["observations"]["SP.POP.TOTL"][0]["value"] = None
    countries = [{
        "game_id": "g1", "country_name": "Example", "source_lookup_code": "USA",
        "identity_mapping_status": "mapped_review_required",
    }]
    result = assessment.assess_snapshot(
        snapshot_data, {}, countries, start_year=2024, end_year=2024,
    )
    row = result["rows"][0]
    assert row["wdi_gdp_current_usd_implied_official_fx"] is None
    assert row["imf_ngdpd_implied_conversion_factor_lcu_per_usd"] is None
    assert row["wdi_gdp_per_capita_implied_from_usd_and_population"] is None


def test_decomposition_requires_all_supporting_series():
    snapshot_data = _fixture_snapshot()
    del snapshot_data["observations"]["PA.NUS.PPP"]
    with pytest.raises(assessment.DecompositionError, match="lacks supporting indicators"):
        assessment.assess_snapshot(snapshot_data, {}, [], start_year=2024, end_year=2024)


def test_report_writes_matrix_and_assessment(tmp_path):
    snapshot_data = _fixture_snapshot()
    countries = [{
        "game_id": "g1", "country_name": "Example", "source_lookup_code": "USA",
        "identity_mapping_status": "mapped_review_required",
    }]
    result = assessment.assess_snapshot(
        snapshot_data, {}, countries, start_year=2024, end_year=2024,
    )
    target = assessment.write_report(result, tmp_path)
    with (target / "decomposition_matrix.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1
    assert rows[0]["wdi_gdp_current_lcu"] == "200.0"
    assert (target / "assessment.json").exists()
    assert (target / "assessment.md").exists()
