from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tools.build_imf_weo_historical_candidate import build_candidate, CandidateError


def _inputs(tmp_path: Path):
    identity = tmp_path / "identity.json"
    identity.write_text(json.dumps({
        "records": [
            {"game_id": "tc_" + "a" * 32,
             "source": {"current_source_id": "AAA"},
             "iso": {"alpha3": "AAA", "assignment_status": "unverified"}}
        ]
    }), encoding="utf-8")
    raw = tmp_path / "weo.csv"
    headers = [
        "SERIES_CODE", "COUNTRY", "FREQUENCY", "UNIT", "SCALE",
        "LATEST_ACTUAL_ANNUAL_DATA", "START_END_MONTHS_OF_REPORTING_YEAR",
        "2024", "2025", "2026"
    ]
    rows = [
        ["AAA.NGDPD.A", "Example", "Annual", "US dollar", "Billions", "2025",
         "January/December", "10.5", "11", ""],
        ["AAA.LUR.A", "Example", "Annual", "", "Units", "2024",
         "January/December", "5.2", "", ""],
        ["BBB.NGDPD.A", "Unmapped", "Annual", "US dollar", "Billions", "2025",
         "January/December", "2", "", ""],
        ["AAA.PPPGDP.A", "Example", "Annual", "Purchasing power parity", "Billions", "",
         "January/December", "..", "8", ""],
    ]
    with raw.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)
    return raw, identity


def test_complete_values_import_candidate_even_with_unverified_identity(tmp_path):
    raw, identity = _inputs(tmp_path)
    observations, exceptions, summary = build_candidate(raw, identity, verify_snapshot=False)
    assert len(observations) == 4
    assert {row["game_id"] for row in observations} == {"tc_" + "a" * 32}
    assert all(row["value_status"] == "unclassified" for row in observations)
    assert summary["distinct_game_ids"] == 1
    assert any(row["exception"] == "unmapped_or_ambiguous_identity" for row in exceptions)


def test_blank_cells_are_not_synthesized_and_unclassified_is_preserved(tmp_path):
    raw, identity = _inputs(tmp_path)
    observations, _, _ = build_candidate(raw, identity, verify_snapshot=False)
    assert not any(row["observation_year"] == 2026 for row in observations)
    assert all(row["value_status"] == "unclassified" for row in observations)


def test_wdi_presence_is_not_an_input_to_eligibility(tmp_path):
    raw, identity = _inputs(tmp_path)
    observations, _, _ = build_candidate(raw, identity, verify_snapshot=False)
    assert {(row["indicator_code"], row["observation_year"]) for row in observations} == {
        ("NGDPD", 2024), ("NGDPD", 2025), ("LUR", 2024), ("PPPGDP", 2025)
    }


def test_missing_unit_is_retained_as_null_not_inferred(tmp_path):
    raw, identity = _inputs(tmp_path)
    observations, _, _ = build_candidate(raw, identity, verify_snapshot=False)
    unemployment = next(row for row in observations if row["indicator_code"] == "LUR")
    assert unemployment["unit"] is None
    assert unemployment["scale"] == "Units"


def test_duplicate_source_series_rejected(tmp_path):
    raw, identity = _inputs(tmp_path)
    text = raw.read_text(encoding="utf-8")
    duplicate = text.splitlines()[1]
    raw.write_text(text + duplicate + "\n", encoding="utf-8")
    with pytest.raises(CandidateError, match="Duplicate WEO series"):
        build_candidate(raw, identity, verify_snapshot=False)



def test_explicit_imf_crosswalk_maps_wbg_and_field_filter_is_respected(tmp_path):
    raw, identity = _inputs(tmp_path)
    with raw.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([
            "WBG.NGDPD.A", "West Bank and Gaza", "Annual", "US dollar", "Billions",
            "2025", "January/December", "3.5", "", ""
        ])
        writer.writerow([
            "G001.NGDPD.A", "World", "Annual", "US dollar", "Billions",
            "2025", "January/December", "100", "", ""
        ])
    crosswalk = tmp_path / "imf_weo.json"
    crosswalk.write_text(json.dumps({
        "schema_version": 1,
        "dataset": "world_economic_outlook",
        "source_key": "imf_weo",
        "mappings": [{
            "game_id": "tc_" + "a" * 32,
            "source_id": "WBG",
            "match_method": "reviewed_manual",
            "evidence_url": "https://example.org/imf-weo-appendix",
            "source_name": "West Bank and Gaza"
        }]
    }), encoding="utf-8")
    observations, exceptions, summary = build_candidate(
        raw, identity, verify_snapshot=False, crosswalk_path=crosswalk, field_ids={15}
    )
    wbg = [row for row in observations if row["source_country_code"] == "WBG"]
    assert len(wbg) == 1
    assert wbg[0]["game_id"] == "tc_" + "a" * 32
    assert wbg[0]["field_id"] == 15
    assert all(row["field_id"] == 15 for row in observations)
    assert any(row.get("source_country_code") == "G001" for row in exceptions)
    assert summary["field_ids"] == [15]
    assert summary["crosswalk_sha256"] == sha256(crosswalk)


def test_imf_crosswalk_rejects_game_id_not_in_registry(tmp_path):
    raw, identity = _inputs(tmp_path)
    crosswalk = tmp_path / "imf_weo.json"
    crosswalk.write_text(json.dumps({
        "schema_version": 1,
        "dataset": "world_economic_outlook",
        "source_key": "imf_weo",
        "mappings": [{
            "game_id": "tc_" + "b" * 32,
            "source_id": "WBG",
            "match_method": "reviewed_manual"
        }]
    }), encoding="utf-8")
    with pytest.raises(CandidateError, match="canonical identity registry"):
        build_candidate(raw, identity, verify_snapshot=False, crosswalk_path=crosswalk)
