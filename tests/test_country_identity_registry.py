import copy

from tools.country_identity_registry import bootstrap, validate


def source_metadata():
    return {
        "countries": [
            {"id": "AAA", "iso3": "AAA", "name": "Alpha", "aliases": [], "regions": ["Asia"]},
            {"id": "BBB", "iso3": None, "name": "Beta", "aliases": ["Beta Isles"], "regions": []},
        ]
    }


def test_bootstrap_preserves_every_source_record_and_uses_unique_opaque_ids():
    source = source_metadata()
    registry = bootstrap(source)
    assert len(registry["records"]) == len(source["countries"])
    assert {r["source"]["current_source_id"] for r in registry["records"]} == {"AAA", "BBB"}
    assert len({r["game_id"] for r in registry["records"]}) == 2
    assert all(r["game_id"].startswith("tc_") for r in registry["records"])
    assert validate(registry, source) == []


def test_validation_rejects_missing_or_duplicate_game_ids():
    source = source_metadata()
    registry = bootstrap(source)
    registry["records"][1]["game_id"] = registry["records"][0]["game_id"]
    errors = validate(registry, source)
    assert any("game_id values must be unique" in e for e in errors)


def test_validation_rejects_source_feature_missing_from_registry():
    source = source_metadata()
    registry = bootstrap(source)
    registry["records"].pop()
    errors = validate(registry, source)
    assert any("missing registry entries" in e for e in errors)
    assert any("record count mismatch" in e for e in errors)


def test_validation_rejects_two_game_ids_claiming_same_source_id():
    source = source_metadata()
    registry = bootstrap(source)
    registry["records"][1]["source"]["current_source_id"] = "AAA"
    registry["records"][1]["geometry_key"] = "AAA"
    errors = validate(registry, source)
    assert any("maps to multiple game_ids" in e for e in errors)


def test_registry_keeps_id_when_source_id_changes_are_explicitly_mapped():
    source = source_metadata()
    registry = bootstrap(source)
    first = registry["records"][0]
    original_game_id = first["game_id"]
    first["source"]["previous_source_ids"] = ["OLD_AAA"]
    # The registry's reviewed current key is changed explicitly; identity remains stable.
    first["source"]["current_source_id"] = "NEW_AAA"
    first["geometry_key"] = "NEW_AAA"
    changed_source = copy.deepcopy(source)
    changed_source["countries"][0]["id"] = "NEW_AAA"
    errors = validate(registry, changed_source)
    assert errors == []
    assert first["game_id"] == original_game_id


def test_bootstrap_never_overwrites_or_implicitly_updates_existing_registry_is_cli_policy():
    # The command's --bootstrap path checks path existence before writing. This test
    # documents the invariant at the API level: bootstrap is proposal creation only.
    first = bootstrap(source_metadata())
    second = bootstrap(source_metadata())
    assert [r["game_id"] for r in first["records"]] != [r["game_id"] for r in second["records"]]
