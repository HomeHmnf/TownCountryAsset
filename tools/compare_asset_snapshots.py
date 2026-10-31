#!/usr/bin/env python3
"""Compare two compiled asset snapshots and report identity/data changes."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_snapshot(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        metadata = json.loads((path / "countries.json").read_text(encoding="utf-8"))
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read snapshot at {path}: {exc}") from exc
    countries = metadata.get("countries")
    if not isinstance(countries, list):
        raise ValueError(f"{path}/countries.json has no countries array")
    indexed: dict[str, Any] = {}
    for index, country in enumerate(countries):
        if not isinstance(country, dict) or not isinstance(country.get("id"), str):
            raise ValueError(f"{path}: invalid country record at index {index}")
        country_id = country["id"]
        if country_id in indexed:
            raise ValueError(f"{path}: duplicate country ID {country_id!r}")
        indexed[country_id] = country
    return metadata, {"countries": indexed, "manifest": manifest, "path": str(path)}


def _index_by_unique_value(countries: dict[str, Any], key: str) -> dict[str, str]:
    values: dict[str, list[str]] = defaultdict(list)
    for country_id, country in countries.items():
        value = country.get(key)
        if isinstance(value, str) and value:
            values[value].append(country_id)
    return {value: ids[0] for value, ids in values.items() if len(ids) == 1}


def _geometry_fingerprints(path: Path, country_ids: set[str]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for profile in ("low", "medium", "high"):
        file_path = path / f"geometry_{profile}.json"
        if not file_path.exists():
            continue
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        geometries = payload.get("geometries", {})
        if not isinstance(geometries, dict):
            continue
        result[profile] = {
            country_id: hashlib.sha256(
                json.dumps(geometries[country_id], sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            for country_id in country_ids if country_id in geometries
        }
    return result


def compare_snapshots(old_dir: Path, new_dir: Path, *, new_snapshot_label: str | None = None) -> dict[str, Any]:
    old_meta, old = load_snapshot(old_dir)
    new_meta, new = load_snapshot(new_dir)
    old_countries, new_countries = old["countries"], new["countries"]
    old_ids, new_ids = set(old_countries), set(new_countries)
    added, removed = sorted(new_ids - old_ids), sorted(old_ids - new_ids)

    old_iso = _index_by_unique_value(old_countries, "iso3")
    new_iso = _index_by_unique_value(new_countries, "iso3")
    rekeyed = []
    for iso, old_id in sorted(old_iso.items()):
        new_id = new_iso.get(iso)
        if new_id and old_id != new_id and old_id in removed and new_id in added:
            rekeyed.append({"iso3": iso, "old_id": old_id, "new_id": new_id,
                            "old_name": old_countries[old_id].get("name"),
                            "new_name": new_countries[new_id].get("name")})

    changed = []
    for country_id in sorted(old_ids & new_ids):
        before, after = old_countries[country_id], new_countries[country_id]
        fields = {}
        for field in ("name", "iso3", "regions", "aliases", "source_geometry_type"):
            if before.get(field) != after.get(field):
                fields[field] = {"old": before.get(field), "new": after.get(field)}
        old_attrs, new_attrs = before.get("source_attributes", {}), after.get("source_attributes", {})
        attr_changes = {
            key: {"old": old_attrs.get(key), "new": new_attrs.get(key)}
            for key in sorted(set(old_attrs) | set(new_attrs))
            if old_attrs.get(key) != new_attrs.get(key)
        }
        if attr_changes:
            fields["source_attributes"] = attr_changes
        if fields:
            changed.append({"id": country_id, "changes": fields})

    old_geo = _geometry_fingerprints(old_dir, old_ids)
    new_geo = _geometry_fingerprints(new_dir, new_ids)
    geometry_changes = {}
    for profile in sorted(set(old_geo) | set(new_geo)):
        before, after = old_geo.get(profile, {}), new_geo.get(profile, {})
        changed_ids = sorted(
            country_id for country_id in set(before) & set(after)
            if before[country_id] != after[country_id]
        )
        missing = sorted((old_ids & new_ids) - (set(before) & set(after)))
        if changed_ids or missing:
            geometry_changes[profile] = {"changed_ids": changed_ids, "missing_shared_ids": missing}

    game_id_values = [
        country.get("game_id")
        for country in new_countries.values()
        if isinstance(country.get("game_id"), str) and country.get("game_id")
    ]
    game_id_counts: dict[str, int] = defaultdict(int)
    for game_id in game_id_values:
        game_id_counts[game_id] += 1
    missing_game_id_source_ids = sorted(
        country_id for country_id, country in new_countries.items()
        if not isinstance(country.get("game_id"), str) or not country.get("game_id")
    )
    duplicate_game_ids = sorted(game_id for game_id, count in game_id_counts.items() if count > 1)
    canonical_geometry = {}
    for profile in ("low", "medium", "high"):
        geometry_path = new_dir / f"geometry_game_id_{profile}.json"
        if not geometry_path.exists():
            canonical_geometry[profile] = {"present": False, "geometry_count": 0, "missing_game_ids": sorted(set(game_id_values))}
            continue
        try:
            payload = json.loads(geometry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot read canonical geometry file {geometry_path}: {exc}") from exc
        geometries = payload.get("geometries", {})
        geometry_keys = set(geometries) if isinstance(geometries, dict) else set()
        expected_game_ids = set(game_id_values)
        canonical_geometry[profile] = {
            "present": True,
            "geometry_count": len(geometry_keys),
            "missing_game_ids": sorted(expected_game_ids - geometry_keys),
            "unexpected_geometry_ids": sorted(geometry_keys - expected_game_ids),
            "key_field": payload.get("key"),
        }
    game_identity = {
        "records_with_game_id": len(game_id_values),
        "records_missing_game_id": len(missing_game_id_source_ids),
        "missing_game_id_source_ids": missing_game_id_source_ids,
        "unique_game_ids": len(game_id_counts),
        "duplicate_game_ids": duplicate_game_ids,
        "canonical_geometry": canonical_geometry,
    }
    old_source = old_meta.get("source", {})
    new_source = new_meta.get("source", {})
    old_manifest = old["manifest"]
    new_manifest = new["manifest"]
    old_schema, new_schema = old_meta.get("source_schema"), new_meta.get("source_schema")
    old_build_inputs, new_build_inputs = old_meta.get("build_inputs"), new_meta.get("build_inputs")
    schema_comparable = old_schema is not None and new_schema is not None
    build_inputs_comparable = old_build_inputs is not None and new_build_inputs is not None
    return {
        "old_snapshot": str(old_dir),
        "new_snapshot": str(new_snapshot_label if new_snapshot_label is not None else new_dir),
        "source_archive_sha256": {
            "old": old_source.get("archive_sha256"), "new": new_source.get("archive_sha256"),
            "changed": old_source.get("archive_sha256") != new_source.get("archive_sha256"),
        },
        "source_version": {"old": old_source.get("source_version"), "new": new_source.get("source_version")},
        "source_schema": {
            "old": old_schema, "new": new_schema,
            "comparable": schema_comparable,
            "changed": old_schema != new_schema if schema_comparable else None,
        },
        "build_inputs": {
            "old": old_build_inputs, "new": new_build_inputs,
            "comparable": build_inputs_comparable,
            "changed": old_build_inputs != new_build_inputs if build_inputs_comparable else None,
        },
        "feature_count": {"old": len(old_ids), "new": len(new_ids), "delta": len(new_ids) - len(old_ids)},
        "game_identity": game_identity,
        "added_ids": added,
        "removed_ids": removed,
        "possible_rekeys_by_unique_iso3": rekeyed,
        "changed_existing_features": changed,
        "geometry_changes": geometry_changes,
        "manifest_file_changes": {
            "old": old_manifest.get("files", {}),
            "new": new_manifest.get("files", {}),
        },
        "warning": "This is a change report, not an approval. Review all ID, ISO, region, geometry, and catalog impacts before promotion.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Asset snapshot comparison", "",
        f"- Old snapshot: `{report['old_snapshot']}`",
        f"- New snapshot: `{report['new_snapshot']}`",
        f"- Feature count: {report['feature_count']['old']} → {report['feature_count']['new']} (Δ {report['feature_count']['delta']})",
        f"- Source archive hash changed: {report['source_archive_sha256']['changed']}",
        "- Source schema comparison: " + (
            str(report["source_schema"]["changed"]) if report["source_schema"]["comparable"]
            else "not comparable (schema metadata missing from at least one snapshot)"
        ),
        "- Build configuration comparison: " + (
            str(report["build_inputs"]["changed"]) if report["build_inputs"]["comparable"]
            else "not comparable (build-input metadata missing from at least one snapshot)"
        ), "",
        "## Identity changes", "",
        f"- Added IDs ({len(report['added_ids'])}): " + (", ".join(f"`{v}`" for v in report["added_ids"]) or "none"),
        f"- Removed IDs ({len(report['removed_ids'])}): " + (", ".join(f"`{v}`" for v in report["removed_ids"]) or "none"),
        f"- Possible rekeys by unique ISO3 ({len(report['possible_rekeys_by_unique_iso3'])}):",
    ]
    for item in report["possible_rekeys_by_unique_iso3"]:
        lines.append(f"  - `{item['old_id']}` → `{item['new_id']}` ({item['iso3']}), {item['old_name']} → {item['new_name']}")
    identity = report["game_identity"]
    lines += [
        "",
        "## Canonical game identity checks",
        "",
        f"- Records with game_id: {identity['records_with_game_id']}",
        f"- Records missing game_id: {identity['records_missing_game_id']}",
        f"- Unique game_id values: {identity['unique_game_ids']}",
        f"- Duplicate game_id values: {len(identity['duplicate_game_ids'])}",
    ]
    if identity["missing_game_id_source_ids"]:
        lines.append("  - Missing on source IDs: " + ", ".join(f"`{v}`" for v in identity["missing_game_id_source_ids"]))
    if identity["duplicate_game_ids"]:
        lines.append("  - Duplicates: " + ", ".join(f"`{v}`" for v in identity["duplicate_game_ids"]))
    lines.append("- Canonical geometry coverage:")
    for profile, details in identity["canonical_geometry"].items():
        status = "present" if details["present"] else "MISSING FILE"
        lines.append(
            f"  - {profile}: {status}; {details['geometry_count']} geometries; "
            f"{len(details['missing_game_ids'])} missing IDs; "
            f"{len(details.get('unexpected_geometry_ids', []))} unexpected IDs; "
            f"key field={details.get('key_field')!r}"
        )
    lines += ["", "## Existing feature metadata changes", ""]
    if report["changed_existing_features"]:
        for item in report["changed_existing_features"]:
            lines.append(f"- `{item['id']}`: " + ", ".join(item["changes"].keys()))
    else:
        lines.append("- none")
    lines += ["", "## Geometry changes", ""]
    if report["geometry_changes"]:
        for profile, change in report["geometry_changes"].items():
            lines.append(f"- {profile}: {len(change['changed_ids'])} changed geometries; {len(change['missing_shared_ids'])} missing shared IDs")
    else:
        lines.append("- none detected")
    lines += ["", "## Review warning", "", report["warning"], ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", required=True, type=Path, help="Previously approved generated asset directory")
    parser.add_argument("--new", required=True, type=Path, help="Candidate generated asset directory")
    parser.add_argument("--output", type=Path, help="Optional report path (.json or .md)")
    parser.add_argument(
        "--new-display-path", type=Path,
        help="Logical candidate path to show in the report when comparing a temporary staging directory",
    )
    args = parser.parse_args()
    try:
        report = compare_snapshots(
            args.old, args.new,
            new_snapshot_label=str(args.new_display_path) if args.new_display_path else None,
        )
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"comparison error: {exc}", file=sys.stderr)
        return 1
    json_text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    markdown_text = render_markdown(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown_text if args.output.suffix.lower() == ".md" else json_text, encoding="utf-8")
        print(f"Comparison report written to {args.output}")
    else:
        print(markdown_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
