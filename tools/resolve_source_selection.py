"""Resolve normalized observations with the approved policy and write audit reports."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.database.source_selection import SourceSelectionError, load_policy, resolve_field
from tools.database.structured_source_selection import resolve_structured_field
from tools.sources.registry import SourceError, canonical_source_id, load_registry
from tools.sources.reporting import write_selection_report_bundle


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceSelectionError(f"Cannot read {label} {path}: {exc}") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_overrides(path: Path | None, payload: dict[str, Any], policy: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None, str | None]:
    if "manual_overrides" in payload:
        if not isinstance(payload["manual_overrides"], list):
            raise SourceSelectionError("Input manual_overrides must be an array")
        return payload["manual_overrides"], "input", None
    if path is None:
        configured = Path(policy["_root"]) / policy["manual_overrides"]["dataset"]
        path = configured
    if not path.exists():
        return [], str(path), None
    value = _read_json(path, "manual override dataset")
    if isinstance(value, list):
        rows = value
    elif isinstance(value, dict) and isinstance(value.get("overrides"), list):
        rows = value["overrides"]
    else:
        raise SourceSelectionError("Manual override dataset must be an array or an object with an overrides array")
    if not all(isinstance(row, dict) for row in rows):
        raise SourceSelectionError("Every manual override must be an object")
    return rows, str(path), _sha256(path)


def _release_state_summary(registry: dict[str, Any]) -> dict[str, str]:
    root = Path(registry["_root"])
    result = {}
    template = registry["release_management"]["release_record"]["path_template"]
    for source_id in registry["sources"]:
        path = root / template.replace("<source-id>", source_id)
        if not path.is_file():
            continue
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        latest = state.get("latest_validated")
        if isinstance(latest, dict) and latest.get("status") in {"validated", "applied"}:
            release_id = latest.get("release_id")
            if isinstance(release_id, str):
                result[source_id] = release_id
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Normalized observations JSON; game_id values must already use the reviewed identity crosswalk")
    parser.add_argument("--policy", type=Path, default=Path("config/source_selection.json"))
    parser.add_argument("--registry", type=Path, default=Path("config/data_sources.json"))
    parser.add_argument("--overrides", type=Path, help="Optional manual override JSON; otherwise use policy path")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/sources/selections"))
    args = parser.parse_args(argv)

    try:
        payload = _read_json(args.input, "normalized selection input")
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise SourceSelectionError("Selection input must be a schema_version 1 JSON object")
        observations = payload.get("observations")
        if not isinstance(observations, list) or not all(isinstance(row, dict) for row in observations):
            raise SourceSelectionError("Selection input observations must be an array of objects")
        registry = load_registry(args.registry)
        policy = load_policy(args.policy, registry)
        overrides, override_path, override_sha = _load_overrides(args.overrides, payload, policy)
        game_ids = payload.get("game_ids")
        if game_ids is None:
            game_ids = sorted({
                row.get("game_id") for row in [*observations, *overrides]
                if isinstance(row, dict) and isinstance(row.get("game_id"), str) and row.get("game_id")
            })
        if not isinstance(game_ids, list) or not game_ids or any(
            not isinstance(value, str) or not value for value in game_ids
        ):
            raise SourceSelectionError("Provide a non-empty game_ids array or observations containing game_id")
        if len(set(game_ids)) != len(game_ids):
            raise SourceSelectionError("game_ids must be unique")
        release_states = payload.get("release_states")
        if release_states is not None and (
            not isinstance(release_states, dict)
            or any(not isinstance(k, str) or not k or not isinstance(v, str) or not v for k, v in release_states.items())
        ):
            raise SourceSelectionError("release_states must map source IDs to non-empty validated release IDs")
        if release_states is not None:
            for source_id in release_states:
                if canonical_source_id(registry, source_id) is None:
                    raise SourceSelectionError(f"release_states contains an unregistered source ID: {source_id}")
        assignments = payload.get("mixture_assignments", {})
        expected_records = payload.get("expected_records", {})
        if not isinstance(assignments, dict) or not isinstance(expected_records, dict):
            raise SourceSelectionError("mixture_assignments and expected_records must be objects")
        if any(not isinstance(value, dict) for value in assignments.values()):
            raise SourceSelectionError("Each mixture_assignments field entry must be an object")
        field_by_key = {field["key"]: field for field in policy["fields"]}
        known_game_ids = set(game_ids)
        for row in observations:
            if any(not isinstance(row.get(key), str) or not row[key] for key in ("game_id", "field_key", "source_id", "release_id")):
                raise SourceSelectionError("Every observation requires game_id, field_key, source_id and release_id")
            if row["game_id"] not in known_game_ids:
                raise SourceSelectionError(f"Observation game_id is not in the requested identity set: {row['game_id']}")
            if row["field_key"] not in field_by_key:
                raise SourceSelectionError(f"Observation uses an unknown policy field: {row['field_key']}")
            if canonical_source_id(registry, row["source_id"]) is None:
                raise SourceSelectionError(f"Observation uses an unregistered source ID: {row['source_id']}")
            if field_by_key[row["field_key"]]["storage"] == "structured" and (
                not isinstance(row.get("record_key"), str) or not row["record_key"]
            ):
                raise SourceSelectionError(f"Structured observation requires record_key: {row['field_key']}")
        for row in overrides:
            if not isinstance(row, dict) or row.get("game_id") not in known_game_ids:
                raise SourceSelectionError("Every manual override must target a requested game_id")
            if row.get("field_key") not in field_by_key:
                raise SourceSelectionError(f"Manual override uses an unknown policy field: {row.get('field_key')!r}")
        if set(expected_records) - {key for key, field in field_by_key.items() if field["storage"] == "structured"}:
            raise SourceSelectionError("expected_records may only target structured policy fields")
        if set(assignments) - set(field_by_key):
            raise SourceSelectionError("mixture_assignments contains an unknown policy field")

        decisions = []
        for game_id in game_ids:
            for field in policy["fields"]:
                field_key = field["key"]
                common = {
                    "game_id": game_id, "field_key": field_key,
                    "observations": observations, "release_states": release_states,
                }
                if field["storage"] == "structured":
                    expected = expected_records.get(field_key, [])
                    if not isinstance(expected, list):
                        raise SourceSelectionError(f"expected_records[{field_key}] must be an array")
                    result = resolve_structured_field(
                        policy, registry, **common,
                        manual_overrides=overrides,
                        mixture_assignments=assignments.get(field_key, {}),
                        expected_records=expected,
                    )
                    decisions.append({"storage": "structured", "result": result})
                else:
                    result = resolve_field(
                        policy, registry, **common,
                        manual_overrides=overrides,
                        mixture_assignments=assignments.get(field_key, {}),
                    )
                    decisions.append({"storage": "scalar", "result": result})

        now = datetime.now(timezone.utc)
        run_id = now.strftime("%Y%m%dT%H%M%S%fZ")
        validated_states = release_states if release_states is not None else _release_state_summary(registry)
        provenance = {
            "created_at": now.isoformat(),
            "policy_path": str(args.policy),
            "policy_sha256": _sha256(args.policy),
            "policy_version": policy["policy_version"],
            "source_registry_path": str(args.registry),
            "source_registry_sha256": _sha256(args.registry),
            "registered_source_count": len(registry["sources"]),
            "input_path": str(args.input),
            "input_sha256": _sha256(args.input),
            "override_path": override_path,
            "override_sha256": override_sha,
            "game_ids": game_ids,
            "game_count": len(game_ids),
            "field_count": len(policy["fields"]),
            "latest_validated_releases": validated_states,
            "database_imported": False,
        }
        paths, summary = write_selection_report_bundle(
            output_root=args.output_dir, report_id=run_id,
            decisions=decisions, provenance=provenance,
        )
        print(json.dumps({
            "run_id": run_id, "summary": summary, "reports": paths,
            "database_imported": False,
        }, ensure_ascii=False, indent=2))
        return 0
    except (SourceError, SourceSelectionError, OSError, ValueError, TypeError) as exc:
        print(f"Source-selection resolution failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
