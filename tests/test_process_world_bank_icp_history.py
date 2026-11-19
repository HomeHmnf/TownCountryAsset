from __future__ import annotations

import json
from pathlib import Path

from tools.process_world_bank_icp_history import (
    _approved_mapping_index,
    _norm_m49,
    INDICATOR_NAMES,
)


def test_m49_normalization_preserves_non_numeric_exception_codes():
    assert _norm_m49("036") == "36"
    assert _norm_m49(" 004 ") == "4"
    assert _norm_m49("-099") == "-099"


def test_approved_mapping_index_ignores_pending_and_rejects_non_bijective():
    mapping = {
        "schema_version": 1,
        "source_key": "world_bank_icp",
        "dataset": "world_bank_icp_databank_saved_report",
        "mappings": [
            {"source_country_code": "AUS", "game_id": "tc_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "review_status": "pending"},
            {"source_country_code": "KHM", "game_id": "tc_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "review_status": "approved"},
        ]
    }
    result = _approved_mapping_index(mapping)
    assert list(result) == ["KHM"]
    mapping["mappings"].append({
        "source_country_code": "CHN",
        "game_id": "tc_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "review_status": "approved",
    })
    try:
        _approved_mapping_index(mapping)
    except RuntimeError as exc:
        assert "one-to-one" in str(exc)
    else:
        raise AssertionError("non-bijective approved crosswalk must fail")


def test_indicator_contract_has_six_distinct_codes():
    assert len(INDICATOR_NAMES) == 6
    assert len(set(INDICATOR_NAMES)) == 6

def test_canonical_registry_reads_only_approved_verified_iso_assignments(tmp_path: Path):
    import sqlite3
    from tools.process_world_bank_icp_history import _canonical_iso_registry

    db = tmp_path / "canonical.sqlite"
    connection = sqlite3.connect(db)
    connection.execute(
        "CREATE TABLE countries (game_id TEXT, iso_alpha3 TEXT, iso_assignment_status TEXT, record_status TEXT)"
    )
    connection.executemany(
        "INSERT INTO countries VALUES (?, ?, ?, ?)",
        [
            ("tc_" + "a" * 32, "AUS", "verified", "approved"),
            ("tc_" + "b" * 32, "BRN", "unverified", "approved"),
            ("tc_" + "c" * 32, "KHM", "verified", "candidate"),
        ],
    )
    connection.commit()
    connection.close()

    matches, status = _canonical_iso_registry(db)
    assert status == "read_only_verified_registry_loaded"
    assert [item["game_id"] for item in matches["AUS"]] == ["tc_" + "a" * 32]
    assert "BRN" not in matches
    assert "KHM" not in matches

def test_exception_entity_cannot_be_promoted_to_country_mapping():
    mapping = {
        "schema_version": 1,
        "source_key": "world_bank_icp",
        "dataset": "world_bank_icp_databank_saved_report",
        "mappings": [
            {"source_country_code": "WLD", "game_id": "tc_" + "a" * 32, "review_status": "approved"}
        ],
        "exceptions": [
            {"source_country_code": "WLD", "status": "aggregate_not_a_country"}
        ],
    }
    try:
        _approved_mapping_index(mapping)
    except RuntimeError as exc:
        assert "listed as an exception" in str(exc)
    else:
        raise AssertionError("benchmark aggregate must never be approved as a country")
