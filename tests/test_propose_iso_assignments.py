from __future__ import annotations

import csv
import json

import pytest

from tools.propose_iso_assignments import propose, read_reference, render_report


def registry():
    return {
        "records": [
            {
                "game_id": "tc_alpha",
                "names": {"en": "Alpha"},
                "iso": {"alpha2": None, "alpha3": "AAA", "assignment_status": "unverified"},
            },
            {
                "game_id": "tc_beta",
                "names": {"en": "Beta"},
                "iso": {"alpha2": None, "alpha3": None, "assignment_status": "unverified"},
            },
            {
                "game_id": "tc_verified",
                "names": {"en": "Gamma"},
                "iso": {"alpha2": "GG", "alpha3": "GAM", "assignment_status": "verified"},
            },
        ]
    }


def reference():
    return [
        {"alpha2": "AA", "alpha3": "AAA", "english_name": "Alpha"},
        {"alpha2": "BB", "alpha3": "BBB", "english_name": "Beta"},
        {"alpha2": "GG", "alpha3": "GAM", "english_name": "Gamma"},
    ]


def test_proposals_match_names_but_never_mutate_registry():
    data = registry()
    before = json.dumps(data, sort_keys=True)
    result = propose(data, reference())
    assert result["candidate_count"] == 3
    assert result["proposals"][0]["candidate_alpha2"] == "AA"
    assert "human verification required" in result["proposals"][0]["decision"]
    assert "already marked verified" in result["proposals"][2]["decision"]
    assert json.dumps(data, sort_keys=True) == before


def test_no_match_does_not_fall_back_to_source_or_existing_iso_code():
    data = {"records": [{
        "game_id": "tc_custom",
        "source": {"current_source_id": "ZZZ"},
        "names": {"en": "Custom Territory"},
        "iso": {"alpha2": None, "alpha3": "ZZZ", "assignment_status": "unverified"},
    }]}
    result = propose(data, reference())
    row = result["proposals"][0]
    assert row["candidate_alpha2"] == ""
    assert row["candidate_alpha3"] == ""
    assert "no exact normalized English-name match" in row["decision"]


def test_normalized_spelling_format_matches_but_does_not_use_fuzzy_synonyms():
    data = {"records": [
        {"game_id": "tc_one", "names": {"en": "Côte d'Ivoire"}, "iso": {}},
        {"game_id": "tc_two", "names": {"en": "Ivory Coast"}, "iso": {}},
    ]}
    refs = [{"alpha2": "CI", "alpha3": "CIV", "english_name": "Cote d Ivoire"}]
    result = propose(data, refs)
    assert result["proposals"][0]["candidate_alpha3"] == "CIV"
    assert result["proposals"][1]["candidate_alpha3"] == ""


def test_reference_csv_requires_valid_columns_and_unique_valid_codes(tmp_path):
    path = tmp_path / "reference.csv"
    path.write_text("alpha2,alpha3,english_name\nAA,AAA,Alpha\n", encoding="utf-8")
    assert read_reference(path) == reference()[:1]

    path.write_text("alpha2,alpha3,english_name\nA,AAA,Alpha\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid alpha2"):
        read_reference(path)


def test_report_explains_review_only_policy():
    report = render_report(propose(registry(), reference()), "official-iso.csv")
    assert "does not modify the registry or approve" in report
    assert "source IDs and existing ISO fields are never used" in report
