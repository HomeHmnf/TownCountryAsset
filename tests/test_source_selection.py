from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tools.database.source_selection import (
    SourceSelectionError,
    load_policy,
    resolve_field,
    validate_policy,
)
from tools.sources.registry import load_registry


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def registry():
    return load_registry()


@pytest.fixture
def policy(registry):
    return load_policy(ROOT / "config/source_selection.json", registry)


def observation(
    *,
    game_id="tc_example",
    field_key="population",
    source_id="un_wpp",
    release_id="wpp-2024",
    value=1234,
    unit="people",
    status="observed",
    compatibility_status=None,
):
    row = {
        "game_id": game_id,
        "field_key": field_key,
        "source_id": source_id,
        "release_id": release_id,
        "value": value,
        "unit": unit,
        "status": status,
        "observation_period": "2024",
        "source_reference": "table:country-row",
        "methodology": "provider value normalized to canonical unit",
        "retrieved_at": "2026-11-01T08:00:00+00:00",
    }
    if compatibility_status is not None:
        row["compatibility_status"] = compatibility_status
    return row


def test_project_policy_validates_all_41_registered_fields(policy, registry):
    validate_policy(policy, registry)
    assert len(policy["fields"]) == 41
    assert sum(row["selection_mode"] == "priority_source" for row in policy["fields"]) == 36
    assert sum(row["selection_mode"] == "primary_with_fallback" for row in policy["fields"]) == 5


def test_priority_source_uses_only_latest_validated_primary(policy, registry):
    result = resolve_field(
        policy, registry, game_id="tc_example", field_key="population",
        observations=[
            observation(release_id="unvalidated-new", value=9999),
            observation(release_id="wpp-2024", value=1234),
        ],
        release_states={"un_wpp": "wpp-2024"},
    )
    assert result["value"] == 1234
    assert result["selected_source"] == "un_wpp"
    assert result["release_id"] == "wpp-2024"
    assert result["fallback_used"] is False


def test_latest_available_is_not_eligible_without_latest_validated(policy, registry):
    result = resolve_field(
        policy, registry, game_id="tc_example", field_key="population",
        observations=[observation()],
        release_states={},
    )
    assert result["value"] is None
    assert result["selection_status"] == "unavailable"


def test_priority_source_does_not_use_unconfigured_alternative(policy, registry):
    result = resolve_field(
        policy, registry, game_id="tc_example", field_key="population",
        observations=[observation(source_id="world_bank_wdi", release_id="wdi-2025")],
        release_states={"world_bank_wdi": "wdi-2025"},
    )
    assert result["value"] is None
    assert result["selected_source"] is None


def test_fallback_requires_explicit_compatibility_and_never_overwrites_primary(policy, registry):
    primary = observation(
        field_key="labour_force", source_id="ilostat", release_id="ilo-2025", value=500,
    )
    fallback = observation(
        field_key="labour_force", source_id="world_bank_wdi", release_id="wdi-2025",
        value=450, compatibility_status="compatible",
    )
    result = resolve_field(
        policy, registry, game_id="tc_example", field_key="labour_force",
        observations=[primary, fallback],
        release_states={"ilostat": "ilo-2025", "world_bank_wdi": "wdi-2025"},
    )
    assert result["value"] == 500
    assert result["selected_source"] == "ilostat"
    assert result["fallback_used"] is False


def test_fallback_fills_missing_primary_only_when_compatibility_is_explicit(policy, registry):
    fallback = observation(
        field_key="labour_force", source_id="world_bank_wdi", release_id="wdi-2025",
        value=450, compatibility_status="compatible",
    )
    result = resolve_field(
        policy, registry, game_id="tc_example", field_key="labour_force",
        observations=[fallback],
        release_states={"world_bank_wdi": "wdi-2025"},
    )
    assert result["value"] == 450
    assert result["selected_source"] == "world_bank_wdi"
    assert result["fallback_used"] is True


def test_fallback_without_compatibility_is_rejected(policy, registry):
    fallback = observation(
        field_key="labour_force", source_id="world_bank_wdi", release_id="wdi-2025",
        value=450,
    )
    result = resolve_field(
        policy, registry, game_id="tc_example", field_key="labour_force",
        observations=[fallback],
        release_states={"world_bank_wdi": "wdi-2025"},
    )
    assert result["value"] is None
    assert result["rejected_candidates"][0]["source_id"] == "world_bank_wdi"


def test_unavailable_primary_can_fall_back_but_not_applicable_cannot(policy, registry):
    unavailable = observation(
        field_key="labour_force", source_id="ilostat", release_id="ilo-2025",
        value=None, status="unavailable",
    )
    fallback = observation(
        field_key="labour_force", source_id="world_bank_wdi", release_id="wdi-2025",
        value=450, compatibility_status="compatible",
    )
    result = resolve_field(
        policy, registry, game_id="tc_example", field_key="labour_force",
        observations=[unavailable, fallback],
        release_states={"ilostat": "ilo-2025", "world_bank_wdi": "wdi-2025"},
    )
    assert result["value"] == 450

    not_applicable = {**unavailable, "status": "not_applicable"}
    result = resolve_field(
        policy, registry, game_id="tc_example", field_key="labour_force",
        observations=[not_applicable, fallback],
        release_states={"ilostat": "ilo-2025", "world_bank_wdi": "wdi-2025"},
    )
    assert result["selection_status"] == "not_applicable"
    assert result["value"] is None


def test_derived_density_fallback_is_not_silently_calculated(policy, registry):
    result = resolve_field(
        policy, registry, game_id="tc_example", field_key="population_density",
        observations=[],
        release_states={},
    )
    assert result["value"] is None
    assert result["rejected_candidates"][0]["type"] == "derived"


def test_manual_override_takes_precedence_and_records_prior_candidate(policy, registry):
    primary = observation()
    override = {
        "override_id": "ovr-001",
        "game_id": "tc_example",
        "field_key": "population",
        "scope": {"country": "tc_example"},
        "value": 1300,
        "unit": "people",
        "status": "observed",
        "reason": "Reviewed national statistical release",
        "author": "project-review",
        "effective_at": "2026-10-30T12:00:00+00:00",
    }
    result = resolve_field(
        policy, registry, game_id="tc_example", field_key="population",
        observations=[primary],
        release_states={"un_wpp": "wpp-2024"},
        manual_overrides=[override],
    )
    assert result["value"] == 1300
    assert result["selected_source"] == "manual_override"
    assert result["override_id"] == "ovr-001"
    assert result["prior_provider_candidate"]["value"] == 1234


def test_duplicate_manual_overrides_and_ambiguous_source_rows_fail(policy, registry):
    override = {
        "override_id": "ovr-001", "game_id": "tc_example", "field_key": "population",
        "scope": {}, "value": 1, "unit": "people", "status": "observed",
        "reason": "review", "author": "reviewer",
        "effective_at": "2026-10-30T12:00:00+00:00",
    }
    with pytest.raises(SourceSelectionError, match="Multiple manual overrides"):
        resolve_field(
            policy, registry, game_id="tc_example", field_key="population",
            observations=[], release_states={},
            manual_overrides=[override, {**override, "override_id": "ovr-002"}],
        )
    with pytest.raises(SourceSelectionError, match="Ambiguous observations"):
        resolve_field(
            policy, registry, game_id="tc_example", field_key="population",
            observations=[observation(), observation(value=1235)],
            release_states={"un_wpp": "wpp-2024"},
        )


def test_custom_mixture_requires_explicit_registered_assignment(policy, registry):
    changed = copy.deepcopy(policy)
    field = next(row for row in changed["fields"] if row["key"] == "population")
    field["selection_mode"] = "custom_mixture"
    field["mixture_sources"] = ["world_bank_wdi"]
    fallback = observation(
        source_id="world_bank_wdi", release_id="wdi-2025", value=1200,
    )
    result = resolve_field(
        changed, registry, game_id="tc_example", field_key="population",
        observations=[fallback], release_states={"world_bank_wdi": "wdi-2025"},
    )
    assert result["value"] is None
    result = resolve_field(
        changed, registry, game_id="tc_example", field_key="population",
        observations=[fallback], release_states={"world_bank_wdi": "wdi-2025"},
        mixture_assignments={"tc_example": "world_bank_wdi"},
    )
    assert result["value"] == 1200
    assert result["selected_source"] == "world_bank_wdi"


def test_policy_rejects_unregistered_source_and_invalid_mode(policy, registry):
    changed = copy.deepcopy(policy)
    changed["fields"][0]["primary_source"] = "not_registered"
    with pytest.raises(SourceSelectionError, match="not registered"):
        validate_policy(changed, registry)
    changed = copy.deepcopy(policy)
    changed["fields"][0]["selection_mode"] = "automatic_magic"
    with pytest.raises(SourceSelectionError, match="selection_mode"):
        validate_policy(changed, registry)
