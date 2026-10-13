#!/usr/bin/env python3
"""Audit generated country metadata, geometry keys, and manifest integrity."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


PROFILES = ("low", "medium", "high")
ISO3_RE = re.compile(r"^[A-Z]{3}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_generated_assets(data_dir: Path, source: Path | None = None) -> list[str]:
    """Return audit errors; an empty list means structural checks passed."""
    errors: list[str] = []
    countries_path = data_dir / "countries.json"
    manifest_path = data_dir / "manifest.json"
    try:
        metadata = json.loads(countries_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Cannot read metadata/manifest: {exc}"]

    countries = metadata.get("countries")
    if not isinstance(countries, list):
        return ["countries.json must contain a countries array"]
    if metadata.get("count") != len(countries):
        errors.append(f"count mismatch: declared {metadata.get('count')!r}, found {len(countries)}")

    ids: list[str] = []
    iso_by_id: dict[str, str | None] = {}
    for index, country in enumerate(countries):
        if not isinstance(country, dict):
            errors.append(f"country at index {index} is not an object")
            continue
        country_id = country.get("id")
        if not isinstance(country_id, str) or not country_id.strip():
            errors.append(f"country at index {index} has an empty/non-string id")
            continue
        ids.append(country_id)
        iso = country.get("iso3")
        if iso is not None and (not isinstance(iso, str) or not ISO3_RE.fullmatch(iso)):
            errors.append(f"{country_id}: iso3 must be null or three uppercase ASCII letters")
        iso_by_id[country_id] = iso
        if not isinstance(country.get("name"), str) or not country["name"].strip():
            errors.append(f"{country_id}: missing country name")
        if not isinstance(country.get("regions"), list):
            errors.append(f"{country_id}: regions must be an array")
        if not isinstance(country.get("source_attributes"), dict):
            errors.append(f"{country_id}: source_attributes must be an object")

    duplicates = sorted({country_id for country_id in ids if ids.count(country_id) > 1})
    if duplicates:
        errors.append("duplicate country ids: " + ", ".join(duplicates))
    id_set = set(ids)

    for profile in PROFILES:
        filename = f"geometry_{profile}.json"
        path = data_dir / filename
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{filename}: cannot read JSON: {exc}")
            continue
        if payload.get("profile") != profile:
            errors.append(f"{filename}: profile field does not match filename")
        geometries = payload.get("geometries")
        if not isinstance(geometries, dict):
            errors.append(f"{filename}: geometries must be an object")
            continue
        geometry_ids = set(geometries)
        missing = sorted(id_set - geometry_ids)
        extra = sorted(geometry_ids - id_set)
        if missing:
            errors.append(f"{filename}: missing geometry IDs: {', '.join(missing[:20])}")
        if extra:
            errors.append(f"{filename}: unknown geometry IDs: {', '.join(extra[:20])}")

    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, dict):
        errors.append("manifest.json must contain a files object")
    else:
        for filename in ("countries.json", *(f"geometry_{p}.json" for p in PROFILES)):
            entry: Any = manifest_files.get(filename)
            path = data_dir / filename
            if not isinstance(entry, dict):
                errors.append(f"manifest missing entry for {filename}")
                continue
            if not path.is_file():
                continue
            actual_hash = sha256_file(path)
            if entry.get("sha256") != actual_hash:
                errors.append(f"{filename}: SHA-256 does not match manifest")
            if entry.get("size_bytes") != path.stat().st_size:
                errors.append(f"{filename}: size_bytes does not match manifest")

    source_schema = metadata.get("source_schema")
    if not isinstance(source_schema, dict):
        errors.append("source_schema is missing or invalid")
    else:
        schema_fields = source_schema.get("fields")
        if not isinstance(schema_fields, list) or not all(isinstance(field, str) for field in schema_fields):
            errors.append("source_schema.fields must be an array of field names")
        stable_field = source_schema.get("stable_id_field")
        if not isinstance(stable_field, str) or not stable_field:
            errors.append("source_schema.stable_id_field must be a non-empty string")
        elif isinstance(schema_fields, list) and stable_field not in schema_fields:
            errors.append("source_schema.stable_id_field is absent from source_schema.fields")

    build_inputs = metadata.get("build_inputs")
    if not isinstance(build_inputs, dict):
        errors.append("build_inputs is missing or invalid")
    else:
        for key in ("generation_config_sha256", "regions_config_sha256"):
            value = build_inputs.get(key)
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                errors.append(f"build_inputs.{key} must be a SHA-256 hex digest")

    if isinstance(manifest, dict):
        if manifest.get("source_schema") != metadata.get("source_schema"):
            errors.append("manifest source_schema does not match countries.json")
        if manifest.get("build_inputs") != metadata.get("build_inputs"):
            errors.append("manifest build_inputs does not match countries.json")

    source_meta = metadata.get("source")
    if not isinstance(source_meta, dict):
        errors.append("countries.json must contain source provenance")
    elif source is not None:
        if not source.is_file():
            errors.append(f"source archive does not exist: {source}")
        else:
            expected = source_meta.get("archive_sha256")
            actual = sha256_file(source)
            if expected != actual:
                errors.append(f"source archive SHA-256 mismatch: metadata={expected!r}, actual={actual}")
    elif isinstance(source_meta, dict) and not source_meta.get("archive_sha256"):
        errors.append("source archive SHA-256 is missing from metadata")

    region_audit = metadata.get("region_audit")
    if not isinstance(region_audit, dict):
        errors.append("region_audit is missing or invalid")
    else:
        unmapped = region_audit.get("unmapped_ids")
        if not isinstance(unmapped, list):
            errors.append("region_audit.unmapped_ids must be an array")
        else:
            unknown = sorted(set(unmapped) - id_set)
            if unknown:
                errors.append("region audit contains unknown IDs: " + ", ".join(unknown[:20]))
            actual_unmapped = sorted(
                country_id for country_id, country in zip(ids, countries)
                if isinstance(country, dict) and not country.get("regions")
            )
            if sorted(unmapped) != actual_unmapped:
                errors.append("region_audit.unmapped_ids does not match countries with no region")
            if region_audit.get("unmapped_count") != len(unmapped):
                errors.append("region_audit.unmapped_count does not match unmapped_ids")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("generated/town_country_asset"))
    parser.add_argument("--source", type=Path, help="Optional verified source ZIP to check against manifest provenance")
    args = parser.parse_args()
    errors = audit_generated_assets(args.data, args.source)
    if errors:
        print(f"Asset audit failed ({len(errors)} issue(s)):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Asset audit passed: {args.data}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
