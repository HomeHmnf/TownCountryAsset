from __future__ import annotations

import gzip
import csv

import pytest

from tools.build_un_wpp_crosswalk import (
    TAIWAN_GAME_ID,
    TAIWAN_LOC_ID,
    WPPSourceCrosswalkError,
    build_reviewed_crosswalk,
    _location_index,
)


def _review(game_id: str, source_id: str, *, match_type: str = "exact_name",
            comparison: str = "exact", status: str = "review_required") -> dict[str, str]:
    return {
        "game_id": game_id,
        "registry_name": "Example",
        "m49_reference_name": "Example",
        "m49_reference_id": source_id,
        "proposed_source_id": source_id,
        "identity_match_type": match_type,
        "name_comparison": comparison,
        "review_status": status,
    }


def _index() -> dict[str, dict[str, str]]:
    return {
        "4": {"source_name": "Afghanistan", "iso2": "AF", "iso3": "AFG"},
        "158": {
            "source_name": "China, Taiwan Province of China",
            "iso2": "TW",
            "iso3": "TWN",
        },
    }


def test_builds_verified_exact_mapping_and_explicit_taiwan_exception():
    ordinary_game = "tc_" + "a" * 32
    records = [
        _review(ordinary_game, "004"),
        _review(
            TAIWAN_GAME_ID, "", match_type="unmatched",
            comparison="not_compared", status="not_eligible",
        ),
    ]
    payload, counts = build_reviewed_crosswalk(
        records, _index(), _index(), expected_country_area_count=2,
    )
    mappings = {item["game_id"]: item for item in payload["mappings"]}
    assert mappings[ordinary_game]["source_id"] == "4"
    assert mappings[ordinary_game]["match_method"] == "reviewed_manual"
    assert mappings[TAIWAN_GAME_ID]["source_id"] == TAIWAN_LOC_ID
    assert mappings[TAIWAN_GAME_ID]["evidence_url"] == "https://population.un.org/wpp/"
    assert counts["included_m49_verified"] == 1
    assert counts["included_taiwan_manual_exception"] == 1


def test_holds_explicit_variants_and_unmatched_identities():
    ordinary_game = "tc_" + "a" * 32
    variant_game = "tc_" + "b" * 32
    records = [
        _review(ordinary_game, "004"),
        _review(variant_game, "158", match_type="explicit_variant"),
        _review(
            TAIWAN_GAME_ID, "", match_type="unmatched",
            comparison="not_compared", status="not_eligible",
        ),
    ]
    payload, counts = build_reviewed_crosswalk(
        records, _index(), _index(), expected_country_area_count=2,
    )
    game_ids = {item["game_id"] for item in payload["mappings"]}
    assert ordinary_game in game_ids
    assert variant_game not in game_ids
    assert TAIWAN_GAME_ID in game_ids
    assert counts["held_for_identity_review"] == 1


def test_rejects_taiwan_when_wpp_identity_metadata_does_not_match():
    records = [
        _review(
            TAIWAN_GAME_ID, "", match_type="unmatched",
            comparison="not_compared", status="not_eligible",
        ),
    ]
    bad = _index()
    bad["158"] = {
        "source_name": "Taiwan",
        "iso2": "TW",
        "iso3": "TWN",
    }
    with pytest.raises(WPPSourceCrosswalkError, match="expected Taiwan"):
        build_reviewed_crosswalk(
            records, bad, bad, expected_country_area_count=2,
        )


def test_location_index_reads_unique_2026_medium_location_rows(tmp_path):
    path = tmp_path / "demographic.csv.gz"
    columns = [
        "LocID", "Location", "ISO2_code", "ISO3_code", "LocTypeName",
        "VarID", "Variant", "Time",
    ]
    rows = [
        {
            "LocID": "158", "Location": "China, Taiwan Province of China",
            "ISO2_code": "TW", "ISO3_code": "TWN", "LocTypeName": "Country/Area",
            "VarID": "2", "Variant": "Medium", "Time": "2026",
        },
        {
            "LocID": "158", "Location": "China, Taiwan Province of China",
            "ISO2_code": "TW", "ISO3_code": "TWN", "LocTypeName": "Country/Area",
            "VarID": "2", "Variant": "Medium", "Time": "2026",
        },
    ]
    with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    assert _location_index(path, "test")["158"]["iso3"] == "TWN"
