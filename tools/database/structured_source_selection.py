"""Record-level resolver for structured source-selection fields."""
from __future__ import annotations

from typing import Any, Iterable

from tools.database.source_selection import (
    POPULATED_STATUSES, SourceSelectionError, _field, _structured_item_value_valid,
    _structured_scope, _timestamp, _unit_allowed, _validated_release_id, validate_policy,
)
from tools.sources.registry import canonical_source_id


def _source_records(observations, *, game_id, field_key, field, source_id, registry, release_states):
    canonical = canonical_source_id(registry, source_id)
    release_id = _validated_release_id(canonical, registry, release_states)
    if release_id is None:
        return {}
    result = {}
    for row in observations:
        if not isinstance(row, dict):
            raise SourceSelectionError("Structured observations must be objects")
        if row.get("game_id") != game_id or row.get("field_key") != field_key:
            continue
        raw_source = row.get("source_id")
        if not isinstance(raw_source, str) or canonical_source_id(registry, raw_source) != canonical:
            continue
        if row.get("release_id") != release_id:
            continue
        scope = _structured_scope(row)
        if not _unit_allowed(field, row.get("unit")):
            raise SourceSelectionError(f"Invalid unit in structured record {scope}")
        if not _structured_item_value_valid(row.get("value"), row.get("status")):
            raise SourceSelectionError(f"Invalid value/status in structured record {scope}")
        if not isinstance(row.get("observation_period"), str) or not row["observation_period"]:
            raise SourceSelectionError("Structured records require observation_period")
        _timestamp(row.get("retrieved_at"), "structured_observation.retrieved_at")
        if scope in result:
            raise SourceSelectionError(f"Duplicate structured record {scope} from {canonical}")
        result[scope] = {**row, "source_id": canonical}
    return result


def _overrides(records, *, game_id, field_key, field):
    result = {}
    for row in records:
        if not isinstance(row, dict):
            raise SourceSelectionError("Manual overrides must be objects")
        if row.get("game_id") != game_id or row.get("field_key") != field_key:
            continue
        scope = row.get("scope", {})
        if not isinstance(scope, dict) or scope.get("record") is None:
            continue
        if not isinstance(scope["record"], str) or not scope["record"].strip():
            raise SourceSelectionError("Override record scope must be non-empty text")
        subfield = scope.get("subfield")
        if subfield is not None and (not isinstance(subfield, str) or not subfield.strip()):
            raise SourceSelectionError("Override subfield scope must be non-empty text")
        key = (scope["record"], subfield)
        required = ("override_id", "reason", "author", "effective_at", "unit", "status")
        if any(not isinstance(row.get(k), str) or not row[k].strip() for k in required):
            raise SourceSelectionError("Structured override lacks required audit metadata")
        _timestamp(row["effective_at"], "manual_override.effective_at")
        if not _unit_allowed(field, row["unit"]) or not _structured_item_value_valid(row.get("value"), row["status"]):
            raise SourceSelectionError("Structured override violates field value/unit/status contract")
        if key in result:
            raise SourceSelectionError(f"Multiple overrides for structured scope {key}")
        result[key] = row
    return result


def resolve_structured_field(
    policy: dict[str, Any], source_registry: dict[str, Any], *,
    game_id: str, field_key: str, observations: Iterable[dict[str, Any]],
    release_states: dict[str, str] | None = None,
    manual_overrides: Iterable[dict[str, Any]] = (),
    mixture_assignments: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve each record/subfield independently with immutable release provenance.

    Structured observations add required record_key and optional subfield_key.
    Mixture assignment keys are record_key or record_key/subfield_key.
    """
    validate_policy(policy, source_registry)
    field = _field(policy, field_key)
    if field.get("storage") != "structured":
        raise SourceSelectionError(f"{field_key} is not a structured field")
    if not isinstance(game_id, str) or not game_id:
        raise SourceSelectionError("game_id must be non-empty text")
    observations = list(observations)
    primary_id = canonical_source_id(source_registry, field["primary_source"])
    source_ids = [primary_id]
    if field["selection_mode"] == "primary_with_fallback":
        source_ids.extend(canonical_source_id(source_registry, x["source_id"])
                          for x in field.get("fallback_sources", [])
                          if isinstance(x, dict) and isinstance(x.get("source_id"), str))
        resource_policy = field.get("resource_policy", {})
        if isinstance(resource_policy, dict):
            source_ids.extend(canonical_source_id(source_registry, x)
                              for x in resource_policy.get("resource_fallbacks", {}).values()
                              if isinstance(x, str))
    elif field["selection_mode"] == "custom_mixture":
        source_ids.extend(canonical_source_id(source_registry, x) for x in field.get("mixture_sources", []))
    source_ids = list(dict.fromkeys(source_ids))
    source_data = {
        source_id: _source_records(
            observations, game_id=game_id, field_key=field_key, field=field,
            source_id=source_id, registry=source_registry, release_states=release_states,
        ) for source_id in source_ids
    }
    overrides = _overrides(manual_overrides, game_id=game_id, field_key=field_key, field=field)
    scopes = set(overrides)
    for items in source_data.values():
        scopes.update(items)
    assignments = mixture_assignments or {}
    decisions = []
    for scope in sorted(scopes, key=lambda x: (x[0], x[1] or "")):
        record_key, subfield_key = scope
        assignment_key = record_key if subfield_key is None else f"{record_key}/{subfield_key}"
        primary = source_data[primary_id].get(scope)
        override = overrides.get(scope)
        rejected = []
        chosen = None
        assigned_source = None
        if override is not None:
            decisions.append({
                "record_key": record_key, "subfield_key": subfield_key,
                "selected_source": "manual_override", "release_id": None,
                "selection_status": override["status"], "value": override.get("value"),
                "unit": override["unit"], "observation_period": override.get("observation_period"),
                "source_reference": override.get("source_reference"),
                "methodology": override.get("methodology") or override["reason"],
                "retrieved_at": override["effective_at"], "override_id": override["override_id"],
                "override_reason": override["reason"], "override_author": override["author"],
                "prior_provider_candidate": primary, "fallback_used": False,
            })
            continue
        if field["selection_mode"] == "priority_source":
            chosen = primary
        elif field["selection_mode"] == "primary_with_fallback":
            if primary is not None and primary["status"] in POPULATED_STATUSES | {"not_applicable"}:
                chosen = primary
            else:
                for source_id in source_ids:
                    if source_id == primary_id:
                        continue
                    candidate = source_data[source_id].get(scope)
                    if candidate is None:
                        continue
                    if candidate.get("compatibility_status") != "compatible" or not isinstance(candidate.get("compatibility_reference"), str) or not candidate["compatibility_reference"].strip():
                        rejected.append({"source_id": source_id, "reason": "Fallback lacks explicit compatibility evidence"})
                        continue
                    if candidate["status"] == "unavailable":
                        continue
                    chosen, assigned_source = candidate, source_id
                    break
        else:
            assigned = assignments.get(assignment_key)
            if not isinstance(assigned, str):
                rejected.append({"reason": f"Explicit mixture assignment required for {assignment_key}"})
            else:
                assigned_source = canonical_source_id(source_registry, assigned)
                if assigned_source not in source_ids:
                    raise SourceSelectionError(f"Unapproved mixture source {assigned!r} for {assignment_key}")
                chosen = source_data[assigned_source].get(scope)
        if chosen is None:
            decisions.append({
                "record_key": record_key, "subfield_key": subfield_key,
                "selected_source": None, "release_id": None, "selection_status": "unavailable",
                "value": None, "unit": field["unit"], "observation_period": None,
                "source_reference": None, "methodology": None, "retrieved_at": None,
                "fallback_used": False, "primary_candidate": primary,
                "rejected_candidates": rejected, "reason": "No eligible validated observation; missing remains explicit",
            })
            continue
        decisions.append({
            "record_key": record_key, "subfield_key": subfield_key,
            "selected_source": chosen["source_id"], "release_id": chosen["release_id"],
            "selection_status": chosen["status"], "value": chosen.get("value"),
            "unit": chosen["unit"], "observation_period": chosen["observation_period"],
            "source_reference": chosen.get("source_reference"), "methodology": chosen.get("methodology"),
            "retrieved_at": chosen["retrieved_at"], "fallback_used": chosen["source_id"] != primary_id,
            "primary_candidate": primary, "rejected_candidates": rejected,
            "assigned_source": assigned_source, "compatibility_reference": chosen.get("compatibility_reference"),
            "reason": "Selected validated record/subfield observation",
        })
    return {
        "game_id": game_id, "field_key": field_key, "field_id": field["id"],
        "policy_version": policy["policy_version"], "selection_mode": field["selection_mode"],
        "primary_source": primary_id, "records": decisions, "record_count": len(decisions),
        "unavailable_count": sum(x["selection_status"] == "unavailable" for x in decisions),
        "fallback_count": sum(bool(x["fallback_used"]) for x in decisions),
        "override_count": sum(x["selected_source"] == "manual_override" for x in decisions),
    }
