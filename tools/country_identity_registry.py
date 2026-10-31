#!/usr/bin/env python3
"""Create and validate the asset-owned canonical country identity registry.

The registry is authoritative for game_id assignment. Source IDs are lookup keys,
never ID-generation inputs. Bootstrap creates random UUID-backed proposals once;
subsequent validation never invents IDs or silently rekeys records.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

DATASET = "natural_earth_admin_0"
REGISTRY_SCHEMA_VERSION = 1


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def source_id(country: dict[str, Any]) -> str:
    value = country.get("id")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Every source record must have a non-empty string id")
    return value.strip()


def bootstrap(metadata: dict[str, Any]) -> dict[str, Any]:
    """Create an initial proposal. UUIDs are random and then persisted in the registry."""
    countries = metadata.get("countries")
    if not isinstance(countries, list):
        raise ValueError("Source metadata must contain a countries array")
    records = []
    seen: set[str] = set()
    for country in countries:
        if not isinstance(country, dict):
            raise ValueError("Every source country must be an object")
        sid = source_id(country)
        if sid in seen:
            raise ValueError(f"Duplicate source id in input: {sid}")
        seen.add(sid)
        records.append({
            "game_id": f"tc_{uuid.uuid4().hex}",
            "source": {"dataset": DATASET, "current_source_id": sid, "previous_source_ids": []},
            "status": "proposed",
            "iso": {"alpha2": None, "alpha3": country.get("iso3"), "assignment_status": "unverified"},
            "names": {
                "en": country.get("name"),
                "fa": None,
                "aliases_en": list(country.get("aliases", [])),
                "aliases_fa": [],
                "localization_status": "unreviewed"
            },
            "entity_type": "unreviewed",
            "regions": list(country.get("regions", [])),
            "geometry_key": sid
        })
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "dataset": DATASET,
        "status": "proposal",
        "records": records
    }


def validate(registry: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if registry.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        errors.append(f"schema_version must be {REGISTRY_SCHEMA_VERSION}")
    if registry.get("dataset") != DATASET:
        errors.append(f"dataset must be {DATASET!r}")
    records = registry.get("records")
    countries = metadata.get("countries")
    if not isinstance(records, list):
        return errors + ["registry.records must be an array"]
    if not isinstance(countries, list):
        return errors + ["source metadata countries must be an array"]

    game_ids: list[str] = []
    source_to_game: dict[str, str] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"registry record {index} must be an object")
            continue
        gid = record.get("game_id")
        if not isinstance(gid, str) or not gid.strip():
            errors.append(f"registry record {index} has empty game_id")
        else:
            game_ids.append(gid)
        source = record.get("source")
        if not isinstance(source, dict) or source.get("dataset") != DATASET:
            errors.append(f"registry record {index} has invalid source.dataset")
            continue
        current = source.get("current_source_id")
        previous = source.get("previous_source_ids", [])
        if not isinstance(current, str) or not current.strip():
            errors.append(f"registry record {index} has empty current_source_id")
            continue
        if not isinstance(previous, list) or not all(isinstance(x, str) and x.strip() for x in previous):
            errors.append(f"{gid or index}: previous_source_ids must be non-empty strings")
            continue
        if current in previous:
            errors.append(f"{gid or index}: current source id is repeated in previous_source_ids")
        for sid in [current, *previous]:
            if sid in source_to_game and source_to_game[sid] != gid:
                errors.append(f"source id {sid!r} maps to multiple game_ids")
            else:
                source_to_game[sid] = gid
        if record.get("geometry_key") != current:
            errors.append(f"{gid or index}: geometry_key must match current_source_id")
        names = record.get("names")
        if not isinstance(names, dict) or not isinstance(names.get("en"), str) or not names["en"].strip():
            errors.append(f"{gid or index}: names.en must be non-empty")
        if not isinstance(record.get("regions"), list):
            errors.append(f"{gid or index}: regions must be an array")
        iso = record.get("iso")
        if not isinstance(iso, dict):
            errors.append(f"{gid or index}: iso must be an object")
        elif iso.get("alpha3") is not None and (
            not isinstance(iso.get("alpha3"), str) or len(iso["alpha3"]) != 3 or not iso["alpha3"].isalpha() or not iso["alpha3"].isascii() or iso["alpha3"] != iso["alpha3"].upper()
        ):
            errors.append(f"{gid or index}: iso.alpha3 must be null or three uppercase ASCII letters")

    if len(game_ids) != len(set(game_ids)):
        errors.append("game_id values must be unique")
    current_ids = [source_id(c) for c in countries if isinstance(c, dict)]
    if len(current_ids) != len(countries):
        errors.append("source countries must all be objects with valid ids")
    if len(current_ids) != len(set(current_ids)):
        errors.append("source input contains duplicate ids")
    registered_current = {
        record.get("source", {}).get("current_source_id")
        for record in records if isinstance(record, dict) and isinstance(record.get("source"), dict)
    }
    source_set = set(current_ids)
    missing = sorted(source_set - registered_current)
    stale = sorted(registered_current - source_set)
    if missing:
        errors.append("source features missing registry entries: " + ", ".join(missing[:30]))
    if stale:
        errors.append("registry current_source_id values absent from source: " + ", ".join(stale[:30]))
    if len(records) != len(countries):
        errors.append(f"record count mismatch: registry={len(records)}, source={len(countries)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-data", type=Path, default=Path("generated/town_country_asset/countries.json"))
    parser.add_argument("--registry", type=Path, default=Path("config/country_identity_registry.json"))
    parser.add_argument("--bootstrap", action="store_true", help="Create a new proposal; refuses to overwrite an existing registry")
    args = parser.parse_args()
    try:
        metadata = read_json(args.source_data)
        if args.bootstrap:
            if args.registry.exists():
                raise ValueError(f"Refusing to overwrite existing registry: {args.registry}")
            registry = bootstrap(metadata)
            errors = validate(registry, metadata)
            if errors:
                raise ValueError("Generated proposal failed validation: " + "; ".join(errors))
            args.registry.parent.mkdir(parents=True, exist_ok=True)
            args.registry.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote {len(registry['records'])} proposed identities to {args.registry}")
            print("Review every record before changing status from proposal.")
            return 0
        registry = read_json(args.registry)
        errors = validate(registry, metadata)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"identity registry error: {exc}", file=sys.stderr)
        return 1
    if errors:
        print(f"Identity registry validation failed ({len(errors)} issue(s)):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Identity registry validation passed: {len(registry['records'])} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
