from __future__ import annotations

import pytest

from tools.propose_un_wpp_crosswalk import build_review_rows, normalize_m49


def test_crosswalk_proposal_normalizes_m49_and_requires_review():
    rows, counts = build_review_rows([
        {
            "game_id": "tc_" + "a" * 32, "registry_name": "Afghanistan",
            "reference_name": "Afghanistan", "reference_id": "004",
            "match_type": "exact_name", "name_comparison": "exact",
        },
        {
            "game_id": "tc_" + "b" * 32, "registry_name": "Unmatched",
            "reference_name": "", "reference_id": "", "match_type": "unmatched",
        },
    ])
    assert rows[0]["proposed_source_id"] == "4"
    assert rows[0]["review_status"] == "review_required"
    assert rows[1]["review_status"] == "not_eligible"
    assert counts == {"not_eligible": 1, "review_required": 1}


def test_duplicate_m49_or_game_identity_is_not_proposed_as_unambiguous():
    rows, counts = build_review_rows([
        {
            "game_id": "tc_" + "a" * 32, "registry_name": "A",
            "reference_name": "A", "reference_id": "004",
            "match_type": "exact_name",
        },
        {
            "game_id": "tc_" + "b" * 32, "registry_name": "B",
            "reference_name": "B", "reference_id": "4",
            "match_type": "exact_name",
        },
    ])
    assert all(row["review_status"] == "ambiguous_duplicate" for row in rows)
    assert counts == {"ambiguous_duplicate": 2}


def test_m49_reference_id_must_be_numeric():
    with pytest.raises(ValueError, match="must be numeric"):
        normalize_m49("TGO")
