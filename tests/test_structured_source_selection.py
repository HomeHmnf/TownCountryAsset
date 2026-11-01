from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tools.database.source_selection import SourceSelectionError, load_policy
from tools.database.structured_source_selection import resolve_structured_field
from tools.sources.registry import load_registry


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def registry():
    return load_registry()


@pytest.fixture
def policy(registry):
    return load_policy(ROOT / "config/source_selection.json", registry)


def record(*, field_key="religions", source_id="pew_religion", release_id="pew-2020",
           record_key="christian", subfield_key=None, value=31.2, unit="population_or_share_by_category",
           status="estimated", compatibility_status=None):
    row = {
        "game_id": "tc_example", "field_key": field_key, "source_id": source_id,
        "release_id": release_id, "record_key": record_key, "subfield_key": subfield_key,
        "value": value, "unit": unit, "status": status, "observation_period": "2020",
        "source_reference": "table:composition:row", "methodology": "provider estimate",
        "retrieved_at": "2026-11-01T08:00:00+00:00",
    }
    if compatibility_status:
        row["compatibility_status"] = compatibility_status
        row["compatibility_reference"] = "Definition, population scope, unit and reference period reviewed"
    return row


def test_structured_priority_source_resolves_multiple_records_independently(policy, registry):
    result = resolve_structured_field(
        policy, registry, game_id="tc_example", field_key="religions",
        observations=[
            record(record_key="christian", value=31.2),
            record(record_key="muslim", value=24.1),
        ],
        release_states={"pew_religion": "pew-2020"},
    )
    assert result["record_count"] == 2
    assert [row["record_key"] for row in result["records"]] == ["christian", "muslim"]
    assert all(row["selected_source"] == "pew_religion" for row in result["records"])
    assert all(row["release_id"] == "pew-2020" for row in result["records"])


def test_structured_subfields_keep_independent_provenance(policy, registry):
    result = resolve_structured_field(
        policy, registry, game_id="tc_example", field_key="religions",
        observations=[
            record(record_key="composition", subfield_key="christian", value=31.2),
            record(record_key="composition", subfield_key="muslim", value=24.1),
        ],
        release_states={"pew_religion": "pew-2020"},
    )
    assert result["record_count"] == 2
    assert {row["subfield_key"] for row in result["records"]} == {"christian", "muslim"}


def test_structured_manual_override_is_scoped_to_one_subfield(policy, registry):
    override = {
        "override_id": "religion-review-1", "game_id": "tc_example", "field_key": "religions",
        "scope": {"record": "composition", "subfield": "christian"},
        "value": 32.0, "unit": "population_or_share_by_category", "status": "estimated",
        "reason": "Reviewed correction", "author": "reviewer",
        "effective_at": "2026-10-30T12:00:00+00:00",
    }
    result = resolve_structured_field(
        policy, registry, game_id="tc_example", field_key="religions",
        observations=[
            record(record_key="composition", subfield_key="christian"),
            record(record_key="composition", subfield_key="muslim", value=24.1),
        ],
        release_states={"pew_religion": "pew-2020"}, manual_overrides=[override],
    )
    by_key = {row["subfield_key"]: row for row in result["records"]}
    assert by_key["christian"]["selected_source"] == "manual_override"
    assert by_key["christian"]["value"] == 32.0
    assert by_key["christian"]["prior_provider_candidate"]["value"] == 31.2
    assert by_key["muslim"]["selected_source"] == "pew_religion"


def test_structured_fallback_requires_compatibility_evidence(policy, registry):
    primary = record(
        field_key="defence_structure", source_id="iiss_military_balance",
        release_id="iiss-2026", record_key="air_force", value=None, status="unavailable",
        unit="force_structure_records",
    )
    fallback = record(
        field_key="defence_structure", source_id="official_government_sources",
        release_id="official-2026", record_key="air_force", value={"branches": ["air"]},
        unit="force_structure_records", compatibility_status="compatible",
    )
    result = resolve_structured_field(
        policy, registry, game_id="tc_example", field_key="defence_structure",
        observations=[primary, fallback],
        release_states={"iiss_military_balance": "iiss-2026", "official_government_sources": "official-2026"},
    )
    assert result["records"][0]["selected_source"] == "official_government_sources"
    assert result["fallback_count"] == 1


def test_structured_custom_mixture_requires_per_record_assignment(policy, registry):
    changed = copy.deepcopy(policy)
    field = next(row for row in changed["fields"] if row["key"] == "government_structure")
    field["selection_mode"] = "custom_mixture"
    field["mixture_sources"] = ["world_bank_wdi"]
    source_record = record(
        field_key="government_structure", source_id="world_bank_wdi",
        release_id="wdi-2025", record_key="executive", value={"type": "cabinet"},
        unit="government_structure_record",
    )
    result = resolve_structured_field(
        changed, registry, game_id="tc_example", field_key="government_structure",
        observations=[source_record], release_states={"world_bank_wdi": "wdi-2025"},
    )
    assert result["records"][0]["selection_status"] == "unavailable"
    result = resolve_structured_field(
        changed, registry, game_id="tc_example", field_key="government_structure",
        observations=[source_record], release_states={"world_bank_wdi": "wdi-2025"},
        mixture_assignments={"executive": "world_bank_wdi"},
    )
    assert result["records"][0]["selected_source"] == "world_bank_wdi"


def test_structured_rejects_duplicate_records_and_invalid_units(policy, registry):
    with pytest.raises(SourceSelectionError, match="Duplicate structured record"):
        resolve_structured_field(
            policy, registry, game_id="tc_example", field_key="religions",
            observations=[record(), record(value=32.0)],
            release_states={"pew_religion": "pew-2020"},
        )
    bad = record(unit="wrong")
    with pytest.raises(SourceSelectionError, match="Invalid unit"):
        resolve_structured_field(
            policy, registry, game_id="tc_example", field_key="religions",
            observations=[bad], release_states={"pew_religion": "pew-2020"},
        )


def test_structured_missing_entries_are_not_invented(policy, registry):
    result = resolve_structured_field(
        policy, registry, game_id="tc_example", field_key="religions",
        observations=[], release_states={"pew_religion": "pew-2020"},
    )
    assert result["records"] == []
    assert result["record_count"] == 0
    assert result["unavailable_count"] == 0


def test_expected_record_catalogue_emits_explicit_unavailable_items(policy, registry):
    result = resolve_structured_field(
        policy, registry, game_id="tc_example", field_key="natural_resources",
        observations=[], release_states={"usgs_mcs": "mcs-2026"},
        expected_records=[
            {"record_key": "copper/reserves"},
            {"record_key": "gold/production"},
        ],
    )
    assert result["record_count"] == 2
    assert result["unavailable_count"] == 2
    assert all(row["value"] is None for row in result["records"])
    assert all(row["selection_status"] == "unavailable" for row in result["records"])


def test_resource_fallback_is_limited_to_its_registered_record_key(policy, registry):
    changed = copy.deepcopy(policy)
    field = next(row for row in changed["fields"] if row["key"] == "natural_resources")
    field["resource_policy"]["resource_fallbacks"] = {"copper/reserves": "world_bank_wdi"}
    fallback = record(
        field_key="natural_resources", source_id="world_bank_wdi", release_id="wdi-2025",
        record_key="gold/production", value={"quantity": 10}, unit="resource_records",
        compatibility_status="compatible",
    )
    result = resolve_structured_field(
        changed, registry, game_id="tc_example", field_key="natural_resources",
        observations=[fallback], release_states={"world_bank_wdi": "wdi-2025"},
        expected_records=[{"record_key": "gold/production"}],
    )
    assert result["records"][0]["selection_status"] == "unavailable"
    assert result["fallback_count"] == 0


def test_duplicate_expected_catalogue_records_are_rejected(policy, registry):
    with pytest.raises(SourceSelectionError, match="Duplicate expected"):
        resolve_structured_field(
            policy, registry, game_id="tc_example", field_key="natural_resources",
            observations=[], release_states={"usgs_mcs": "mcs-2026"},
            expected_records=[{"record_key": "copper/reserves"}, {"record_key": "copper/reserves"}],
        )


def test_scalar_field_cannot_be_passed_to_structured_resolver(policy, registry):
    with pytest.raises(SourceSelectionError, match="not a structured field"):
        resolve_structured_field(
            policy, registry, game_id="tc_example", field_key="population",
            observations=[], release_states={},
        )
