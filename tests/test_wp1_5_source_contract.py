from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_wp1_5_contract_has_exact_41_selected_fields_including_religion_and_gini():
    contract = json.loads((ROOT / "config/wp1_5_data_sources.json").read_text(encoding="utf-8"))
    fields = contract["fields"]
    ids = [field["id"] for field in fields]
    keys = [field["key"] for field in fields]
    assert len(fields) == 41
    assert len(ids) == len(set(ids)) == 41
    assert len(keys) == len(set(keys)) == 41
    by_id = {field["id"]: field for field in fields}
    assert by_id[48]["key"] == "religions"
    assert by_id[48]["storage"] == "structured"
    assert by_id[48]["primary_source"] == "pew_religion_2020"
    assert by_id[56]["key"] == "gini_index"
    assert by_id[56]["storage"] == "scalar"
    assert by_id[56]["primary_source"] == "world_bank_pip"
    assert contract["reconciliation"]["approved_count"] == 41
    assert contract["reconciliation"]["status"] == "confirmed_by_owner"


def test_every_field_source_is_declared_and_natural_earth_is_not_a_wp1_5_source():
    contract = json.loads((ROOT / "config/wp1_5_data_sources.json").read_text(encoding="utf-8"))
    registry = json.loads((ROOT / "config/data_sources.json").read_text(encoding="utf-8"))
    source_keys = set(registry["sources"])
    assert contract["source_registry"] == "config/data_sources.json"
    assert all(field["primary_source"] in source_keys for field in contract["fields"])
    assert not any("natural_earth" in field["primary_source"] for field in contract["fields"])
    assert registry["policy"]["natural_earth"] == "geography_and_cartography_only"


def test_resource_catalog_is_nonempty_and_has_unique_keys():
    catalog = json.loads((ROOT / "config/wp1_5_resource_catalog.json").read_text(encoding="utf-8"))
    resources = [
        resource
        for group in catalog["resource_groups"]
        for resource in group["resources"]
    ]
    keys = [resource["key"] for resource in resources]
    assert resources
    assert len(keys) == len(set(keys))


def test_wpp_download_profile_pins_official_files_and_togo_update():
    contract = json.loads((ROOT / "config/wp1_5_data_sources.json").read_text(encoding="utf-8"))
    registry = json.loads((ROOT / "config/data_sources.json").read_text(encoding="utf-8"))
    downloads = {item["id"]: item for item in registry["sources"]["un_wpp_2024"]["downloads"]}
    assert downloads["demographic_indicators_medium"]["fields"] == [1, 2, 6, 13, 14]
    assert downloads["population_by_age_5_group_sex_medium"]["fields"] == [12]
    update = downloads["interim_update_togo"]
    assert update["release"] == "2026-01-19-togo-update"
    assert update["scope"].startswith("Togo only")
    wpp = registry["sources"]["un_wpp_2024"]
    assert wpp["license_status"] == "CC BY 3.0 IGO"
    assert wpp["selected_current_period"] == "2026"
    assert wpp["selected_variant"] == "Medium"
    assert wpp["selected_value_status"] == "projected"
