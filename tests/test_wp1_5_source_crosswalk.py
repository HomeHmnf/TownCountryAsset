from __future__ import annotations

import json

import pytest

from tools.database.source_crosswalk import CrosswalkError, load_crosswalk

G1 = "tc_" + "1" * 32
G2 = "tc_" + "2" * 32


def write_crosswalk(tmp_path, mappings, dataset="un_wpp_2024"):
    path = tmp_path / "crosswalk.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "dataset": dataset,
        "source_key": "un_wpp_2024",
        "mappings": mappings,
    }), encoding="utf-8")
    return path


def test_loads_explicit_partial_crosswalk_and_reports_coverage(tmp_path):
    path = write_crosswalk(tmp_path, [{
        "game_id": G1,
        "source_id": "4",
        "match_method": "authoritative_identifier",
        "evidence_url": "https://population.un.org/wpp/",
    }])
    crosswalk = load_crosswalk(path, expected_dataset="un_wpp_2024", known_game_ids=[G1, G2])
    assert crosswalk.mappings[0].source_id == "4"
    assert crosswalk.coverage([G1, G2]) == {
        "expected_count": 2,
        "mapped_count": 1,
        "missing_game_ids": [G2],
        "unexpected_game_ids": [],
    }


def test_rejects_dataset_mismatch_and_unknown_game_id(tmp_path):
    row = {"game_id": G1, "source_id": "4", "match_method": "reviewed_manual"}
    with pytest.raises(CrosswalkError, match="dataset mismatch"):
        load_crosswalk(write_crosswalk(tmp_path, [row]), expected_dataset="imf_weo")
    with pytest.raises(CrosswalkError, match="absent from"):
        load_crosswalk(write_crosswalk(tmp_path, [row]), expected_dataset="un_wpp_2024", known_game_ids=[G2])


@pytest.mark.parametrize("mutate, message", [
    ({"source_id": ""}, "source_id"),
    ({"match_method": "fuzzy_name"}, "match_method"),
    ({"game_id": "USA"}, "persistent game_id"),
    ({"evidence_url": "http://example.test"}, "HTTPS"),
])
def test_rejects_unsafe_mapping_fields(tmp_path, mutate, message):
    row = {"game_id": G1, "source_id": "4", "match_method": "reviewed_manual"}
    row.update(mutate)
    with pytest.raises(CrosswalkError, match=message):
        load_crosswalk(write_crosswalk(tmp_path, [row]), expected_dataset="un_wpp_2024")


def test_rejects_duplicate_source_ids_and_game_ids(tmp_path):
    row = {"game_id": G1, "source_id": "4", "match_method": "reviewed_manual"}
    duplicate_source = [row, {**row, "game_id": G2}]
    with pytest.raises(CrosswalkError, match="Duplicate source_id"):
        load_crosswalk(write_crosswalk(tmp_path, duplicate_source), expected_dataset="un_wpp_2024")
    duplicate_game = [row, {**row, "source_id": "5"}]
    with pytest.raises(CrosswalkError, match="Duplicate game_id"):
        load_crosswalk(write_crosswalk(tmp_path, duplicate_game), expected_dataset="un_wpp_2024")
