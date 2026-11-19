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
