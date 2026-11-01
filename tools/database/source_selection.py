"""Validated, provenance-preserving source selection policy and resolver.

This module resolves already-normalized source observations. It does not acquire,
validate provider datasets, import into SQLite, or approve manual overrides.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from tools.sources.registry import SourceError, canonical_source_id, load_registry


class SourceSelectionError(RuntimeError):
    """Invalid selection policy, evidence, or resolution request."""


ALLOWED_MODES = {"priority_source", "primary_with_fallback", "custom_mixture"}
ALLOWED_STATUSES = {"observed", "estimated", "projected", "unavailable", "not_applicable"}
POPULATED_STATUSES = {"observed", "estimated", "projected"}


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceSelectionError(f"Cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SourceSelectionError(f"{label} must be a JSON object")
    return value


def load_policy(path: Path, source_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load and validate policy against the central source catalogue."""
    policy = _read_json(path, "source-selection policy")
    registry = source_registry if source_registry is not None else load_registry()
    validate_policy(policy, registry)
    policy["_root"] = path.resolve().parent.parent
    return policy


def validate_policy(policy: dict[str, Any], source_registry: dict[str, Any]) -> None:
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        raise SourceSelectionError("Unsupported source-selection policy schema")
    if isinstance(policy.get("policy_version"), bool) or not isinstance(policy.get("policy_version"), int) or policy["policy_version"] < 1:
        raise SourceSelectionError("policy_version must be a positive integer")
    if policy.get("status") != "approved":
        raise SourceSelectionError("Only an approved source-selection policy can be resolved")
    release_policy = policy.get("release_policy")
    overrides_policy = policy.get("manual_overrides")
    missing_policy = policy.get("missing_value_policy")
    if not isinstance(release_policy, dict) or release_policy.get("selection") != "latest_validated":
        raise SourceSelectionError("Source selection must use latest_validated releases")
    if policy.get("source_registry") != "config/data_sources.json":
        raise SourceSelectionError("Policy must reference the central source registry")
    if not isinstance(overrides_policy, dict) or overrides_policy.get("enabled") is not True:
        raise SourceSelectionError("Manual override policy must be explicitly enabled")
    if not isinstance(missing_policy, dict) or missing_policy.get("missing_is_not_zero") is not True:
        raise SourceSelectionError("Missing values must never be interpreted as zero")
    if missing_policy.get("missing_is_not_absence") is not True:
        raise SourceSelectionError("Missing values must never be interpreted as absence")
    if not isinstance(policy.get("modes"), dict) or not ALLOWED_MODES.issubset(policy["modes"]):
        raise SourceSelectionError("All three approved source-selection modes must be documented")
    fields = policy.get("fields")
    if not isinstance(fields, list) or not fields:
        raise SourceSelectionError("Policy fields must be a non-empty array")
    seen_ids: set[int] = set()
    seen_keys: set[str] = set()
    sources = source_registry.get("sources", {})
    for index, field in enumerate(fields):
        label = f"fields[{index}]"
        if not isinstance(field, dict):
            raise SourceSelectionError(f"{label} must be an object")
        field_id, key = field.get("id"), field.get("key")
        if isinstance(field_id, bool) or not isinstance(field_id, int) or field_id < 1:
            raise SourceSelectionError(f"{label}.id must be a positive integer")
        if field_id in seen_ids or not isinstance(key, str) or not key or key in seen_keys:
            raise SourceSelectionError(f"{label} has a duplicate ID/key or invalid key")
        seen_ids.add(field_id)
        seen_keys.add(key)
        if field.get("storage") not in {"scalar", "structured"}:
            raise SourceSelectionError(f"{label}.storage must be scalar or structured")
        if not isinstance(field.get("unit"), str) or not field["unit"]:
            raise SourceSelectionError(f"{label}.unit must be non-empty text")
        mode = field.get("selection_mode")
        if mode not in ALLOWED_MODES:
            raise SourceSelectionError(f"{label}.selection_mode is invalid")
        primary = field.get("primary_source")
        if not isinstance(primary, str) or canonical_source_id(source_registry, primary) not in sources:
            raise SourceSelectionError(f"{label}.primary_source is not registered: {primary!r}")
        fallbacks = field.get("fallback_sources", [])
        if not isinstance(fallbacks, list):
            raise SourceSelectionError(f"{label}.fallback_sources must be an array")
        if mode == "priority_source" and fallbacks:
            raise SourceSelectionError(f"{label}: priority_source cannot declare fallbacks")
        if mode == "custom_mixture" and fallbacks:
            raise SourceSelectionError(f"{label}: custom_mixture uses explicit assignments, not ordered fallbacks")
        mixture_sources = field.get("mixture_sources", [])
        if not isinstance(mixture_sources, list):
            raise SourceSelectionError(f"{label}.mixture_sources must be an array")
        for mixture_source in mixture_sources:
            if not isinstance(mixture_source, str) or canonical_source_id(source_registry, mixture_source) not in sources:
                raise SourceSelectionError(f"{label} mixture source is not registered: {mixture_source!r}")
        for fallback_index, fallback in enumerate(fallbacks):
            if not isinstance(fallback, dict):
                raise SourceSelectionError(f"{label}.fallback_sources[{fallback_index}] must be an object")
            if fallback.get("type") == "derived":
                if not fallback.get("method") or not isinstance(fallback.get("inputs"), list):
                    raise SourceSelectionError(f"{label} has an invalid derived fallback")
                continue
            source_id = fallback.get("source_id")
            if not isinstance(source_id, str) or canonical_source_id(source_registry, source_id) not in sources:
                raise SourceSelectionError(f"{label} fallback source is not registered: {source_id!r}")
        resource_policy = field.get("resource_policy")
        if resource_policy is not None:
            if not isinstance(resource_policy, dict) or resource_policy.get("missing_is_not_absence") is not True:
                raise SourceSelectionError(f"{label}.resource_policy is invalid")


def _field(policy: dict[str, Any], field_key: str) -> dict[str, Any]:
    matches = [row for row in policy["fields"] if row["key"] == field_key]
    if len(matches) != 1:
        raise SourceSelectionError(f"Unknown or ambiguous policy field: {field_key}")
    return matches[0]


def _validated_release_id(
    source_id: str,
    registry: dict[str, Any],
    release_states: dict[str, str] | None,
) -> str | None:
    canonical = canonical_source_id(registry, source_id)
    if release_states is not None:
        return release_states.get(canonical)
    root = registry.get("_root")
    if root is None:
        return None
    path = Path(root) / "reports" / "sources" / "releases" / f"{canonical}.json"
    if not path.is_file():
        return None
    state = _read_json(path, "release state")
    latest = state.get("latest_validated")
    if not isinstance(latest, dict) or latest.get("status") not in {"validated", "applied"}:
        return None
    release_id = latest.get("release_id")
    return release_id if isinstance(release_id, str) and release_id else None


def _unit_allowed(field: dict[str, Any], unit: Any) -> bool:
    contracted = field["unit"]
    allowed = {contracted, *(part.strip() for part in contracted.split("_or_") if part.strip())}
    return isinstance(unit, str) and unit in allowed


def _valid_value(field: dict[str, Any], row: dict[str, Any]) -> bool:
    status = row.get("status")
    value = row.get("value")
    if status not in ALLOWED_STATUSES or not _unit_allowed(field, row.get("unit")):
        return False
    if value is None:
        return status in {"unavailable", "not_applicable"}
    if status not in POPULATED_STATUSES:
        return False
    if field["storage"] == "scalar":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        try:
            return math.isfinite(float(value))
        except (OverflowError, ValueError):
            return False
    if not isinstance(value, (dict, list)):
        return False
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


def _timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise SourceSelectionError(f"{label} must be an ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceSelectionError(f"{label} is not a valid ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SourceSelectionError(f"{label} must include a timezone")
    return parsed


def _candidate_rows(
    observations: Iterable[dict[str, Any]],
    *,
    game_id: str,
    field_key: str,
    field: dict[str, Any],
    source_id: str,
    registry: dict[str, Any],
    release_states: dict[str, str] | None,
) -> list[dict[str, Any]]:
    canonical = canonical_source_id(registry, source_id)
    validated_release = _validated_release_id(canonical, registry, release_states)
    if validated_release is None:
        return []
    found = []
    for row in observations:
        if not isinstance(row, dict):
            raise SourceSelectionError("Every observation must be an object")
        if row.get("game_id") != game_id or row.get("field_key") != field_key:
            continue
        raw_source_id = row.get("source_id")
        if not isinstance(raw_source_id, str):
            continue
        row_source = canonical_source_id(registry, raw_source_id)
        if row_source != canonical or row.get("release_id") != validated_release:
            continue
        if not _valid_value(field, row):
            continue
        if not isinstance(row.get("observation_period"), str) or not row["observation_period"]:
            continue
        _timestamp(row.get("retrieved_at"), "observation.retrieved_at")
        found.append({**row, "source_id": canonical})
    if len(found) > 1:
        raise SourceSelectionError(
            f"Ambiguous observations for {game_id}/{field_key}/{canonical}: expected one row per validated release"
        )
    return found


def _matching_override(
    overrides: Iterable[dict[str, Any]],
    *,
    game_id: str,
    field_key: str,
    field: dict[str, Any],
) -> dict[str, Any] | None:
    matches = []
    for row in overrides:
        if not isinstance(row, dict):
            raise SourceSelectionError("Every manual override must be an object")
        scope = row.get("scope", {})
        if not isinstance(scope, dict):
            raise SourceSelectionError("Manual override scope must be an object")
        if row.get("game_id") != game_id or row.get("field_key") != field_key:
            continue
        if scope.get("subfield") is not None or scope.get("resource") is not None or scope.get("record") is not None:
            continue
        required = ("override_id", "reason", "author", "effective_at", "unit", "status")
        if any(not isinstance(row.get(key), str) or not row[key].strip() for key in required):
            raise SourceSelectionError("Matching manual override lacks ID, reason, author, timestamp, unit or status")
        _timestamp(row["effective_at"], "manual_override.effective_at")
        if not _valid_value(field, {
            "value": row.get("value"), "unit": row["unit"], "status": row["status"],
        }):
            raise SourceSelectionError("Manual override value/status/unit violates the field contract")
        matches.append(row)
    if len(matches) > 1:
        raise SourceSelectionError(f"Multiple manual overrides match {game_id}/{field_key}")
    return matches[0] if matches else None


def resolve_field(
    policy: dict[str, Any],
    source_registry: dict[str, Any],
    *,
    game_id: str,
    field_key: str,
    observations: Iterable[dict[str, Any]],
    release_states: dict[str, str] | None = None,
    manual_overrides: Iterable[dict[str, Any]] = (),
    mixture_assignments: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve one country/entity field, returning value and complete decision provenance.

    Observation records require game_id, field_key, source_id, release_id, value,
    unit, status, observation_period, source_reference, methodology and retrieved_at.
    Fallback rows additionally require compatibility_status='compatible'.
    """
    validate_policy(policy, source_registry)
    field = _field(policy, field_key)
    if not isinstance(game_id, str) or not game_id:
        raise SourceSelectionError("game_id must be non-empty text")
    rows = list(observations)
    overrides = list(manual_overrides)
    override = _matching_override(
        overrides, game_id=game_id, field_key=field_key, field=field,
    )
    primary_id = canonical_source_id(source_registry, field["primary_source"])
    primary_rows = _candidate_rows(
        rows, game_id=game_id, field_key=field_key, field=field,
        source_id=primary_id, registry=source_registry, release_states=release_states,
    )
    primary = primary_rows[0] if primary_rows else None
    decision: dict[str, Any] = {
        "game_id": game_id,
        "field_key": field_key,
        "field_id": field["id"],
        "policy_version": policy["policy_version"],
        "selection_mode": field["selection_mode"],
        "primary_source": primary_id,
        "primary_candidate": primary,
        "selected_source": None,
        "release_id": None,
        "selection_status": "unavailable",
        "value": None,
        "unit": field["unit"],
        "observation_period": None,
        "source_reference": None,
        "methodology": None,
        "retrieved_at": None,
        "fallback_used": False,
        "override_id": None,
        "reason": None,
        "rejected_candidates": [],
    }
    if override is not None:
        decision.update(
            selected_source="manual_override",
            selection_status=override["status"],
            value=override.get("value"),
            unit=override["unit"],
            observation_period=override.get("observation_period"),
            source_reference=override.get("source_reference"),
            methodology=override.get("methodology") or override["reason"],
            retrieved_at=override["effective_at"],
            override_id=override["override_id"],
            override_reason=override["reason"],
            override_author=override["author"],
            override_source=override.get("source"),
            effective_at=override["effective_at"],
            reason="Explicit, scoped manual override takes precedence over provider observations",
            prior_provider_candidate=primary,
        )
        return decision

    chosen = None
    if field["selection_mode"] == "priority_source":
        chosen = primary
    elif field["selection_mode"] == "primary_with_fallback":
        if primary is not None and primary["status"] != "unavailable":
            chosen = primary
        else:
            for fallback in field.get("fallback_sources", []):
                if fallback.get("type") == "derived":
                    decision["rejected_candidates"].append({
                        "type": "derived",
                        "method": fallback.get("method"),
                        "reason": "Derived fallback requires a separately validated derivation implementation",
                    })
                    continue
                fallback_id = canonical_source_id(source_registry, fallback["source_id"])
                candidates = _candidate_rows(
                    rows, game_id=game_id, field_key=field_key, field=field,
                    source_id=fallback_id, registry=source_registry, release_states=release_states,
                )
                if not candidates:
                    continue
                candidate = candidates[0]
                if candidate.get("compatibility_status") != "compatible" or not isinstance(candidate.get("compatibility_reference"), str) or not candidate["compatibility_reference"].strip():
                    decision["rejected_candidates"].append({
                        "source_id": fallback_id,
                        "release_id": candidate["release_id"],
                        "reason": "Fallback lacks an explicit compatible field/unit/scope/period assessment and its evidence reference",
                    })
                    continue
                if candidate["status"] == "unavailable":
                    continue
                chosen = candidate
                decision["compatibility_status"] = candidate["compatibility_status"]
                decision["compatibility_reference"] = candidate["compatibility_reference"]
                break
    else:
        assignments = mixture_assignments or {}
        assigned = assignments.get(game_id)
        if not isinstance(assigned, str):
            decision["reason"] = "custom_mixture requires an explicit source assignment for this game_id"
            return decision
        assigned_id = canonical_source_id(source_registry, assigned)
        allowed = {primary_id}
        allowed.update(
            canonical_source_id(source_registry, source_id)
            for source_id in field.get("mixture_sources", [])
        )
        if assigned_id not in allowed:
            raise SourceSelectionError(f"Mixture assignment source is not allowed for {field_key}: {assigned}")
        assigned_rows = _candidate_rows(
            rows, game_id=game_id, field_key=field_key, field=field,
            source_id=assigned_id, registry=source_registry, release_states=release_states,
        )
        chosen = assigned_rows[0] if assigned_rows else None
        decision["assigned_source"] = assigned_id

    if chosen is None:
        if primary is not None and primary["status"] == "not_applicable":
            decision["selection_status"] = "not_applicable"
            decision["reason"] = "Primary source explicitly marks this field not applicable"
        elif decision["rejected_candidates"]:
            decision["reason"] = "No usable validated observation; fallback candidates were rejected or require additional implementation"
        else:
            decision["reason"] = "No compatible observation from the approved source selection was available"
        return decision

    decision.update(
        selected_source=chosen["source_id"],
        release_id=chosen["release_id"],
        selection_status=chosen["status"],
        value=chosen.get("value"),
        unit=chosen["unit"],
        observation_period=chosen["observation_period"],
        source_reference=chosen.get("source_reference"),
        methodology=chosen.get("methodology"),
        retrieved_at=chosen["retrieved_at"],
        fallback_used=chosen["source_id"] != primary_id,
        reason="Selected the approved validated source observation",
    )
    return decision
