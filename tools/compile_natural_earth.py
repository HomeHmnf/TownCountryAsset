#!/usr/bin/env python3
"""Compile Natural Earth Admin 0 Countries into JSON metadata and geometry."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

import shapefile
from shapely.geometry import mapping, shape
from shapely.validation import explain_validity

SCHEMA_VERSION = 1
INVALID_IDENTIFIERS = {"", "-99", "-"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_extract_zip(archive: zipfile.ZipFile, destination: Path) -> None:
    """Extract regular files only, rejecting traversal and symlinks."""
    root = destination.resolve()
    for info in archive.infolist():
        member = PurePosixPath(info.filename)
        if member.is_absolute() or any(part in {"..", ""} for part in member.parts):
            raise ValueError(f"Unsafe path in ZIP archive: {info.filename!r}")
        mode = info.external_attr >> 16
        if mode and (mode & 0o170000) == 0o120000:
            raise ValueError(f"Symlinks are not allowed in ZIP archives: {info.filename!r}")
        target = (destination / Path(*member.parts)).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"Unsafe path in ZIP archive: {info.filename!r}")
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as source, target.open("wb") as sink:
            shutil.copyfileobj(source, sink)


def _find_unique_shapefile(root: Path) -> Path:
    matches = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".shp")
    if not matches:
        raise FileNotFoundError(f"No .shp file found under {root}")
    if len(matches) > 1:
        names = ", ".join(str(path.relative_to(root)) for path in matches[:8])
        raise ValueError(f"Expected exactly one .shp file under {root}; found {len(matches)}: {names}")
    return matches[0]


def locate_shapefile(source: Path) -> Path:
    source = source.expanduser()
    if source.is_dir():
        return _find_unique_shapefile(source)
    if source.suffix.lower() == ".shp":
        if not source.is_file():
            raise FileNotFoundError(source)
        return source
    if source.suffix.lower() == ".zip":
        if not source.is_file():
            raise FileNotFoundError(source)
        # Keep extracted components beside the archive so pyshp can read sidecars.
        work = source.parent / ".generated-tmp" / source.stem
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(source) as archive:
                _safe_extract_zip(archive, work)
            return _find_unique_shapefile(work)
        except Exception:
            shutil.rmtree(work, ignore_errors=True)
            raise
    raise ValueError("Source must be a .zip archive, .shp file, or extracted shapefile directory")


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "item"):
        return json_safe(value.item())
    return str(value)


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    profiles = config.get("geometry_profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("Config must define geometry_profiles")
    for name, tolerance in profiles.items():
        if not isinstance(name, str) or not name:
            raise ValueError("Geometry profile names must be non-empty strings")
        if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not math.isfinite(tolerance) or tolerance < 0:
            raise ValueError(f"Invalid simplification tolerance for {name}")
    for field in ("iso3_fields", "name_fields"):
        if not isinstance(config.get(field), list):
            raise ValueError(f"Config must define {field} as a list")
    return config


def iso_candidate(attrs: dict[str, Any], fields: list[str]) -> str | None:
    """Return a source-provided ISO alpha-3 candidate, never a Natural Earth ID."""
    for field in fields:
        value = attrs.get(field)
        if value is None:
            continue
        value = str(value).strip().upper()
        if value in INVALID_IDENTIFIERS:
            continue
        # Do not label arbitrary source identifiers as ISO codes merely because
        # they are non-empty. ISO alpha-3 candidates must have exactly 3 letters.
        if re.fullmatch(r"[A-Z]{3}", value):
            return value
    return None


def _source_provenance(source: Path, config: dict[str, Any]) -> dict[str, Any]:
    archive_hash = sha256_file(source) if source.is_file() and source.suffix.lower() == ".zip" else None
    return {
        "url": config.get("source_url"),
        "retrieval_date": config.get("retrieval_date"),
        "layer": config.get("layer"),
        "scale": config.get("scale"),
        "source_version": config.get("source_version"),
        "attribution": config.get("attribution"),
        "license": config.get("license"),
        "archive_sha256": archive_hash,
    }


def compile_data(source: Path, output: Path, config_path: Path, regions_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    region_config = json.loads(regions_path.read_text(encoding="utf-8"))
    shp_path = locate_shapefile(source)
    reader = shapefile.Reader(str(shp_path), encoding=config.get("encoding", "utf-8"))
    try:
        fields = [field[0] for field in reader.fields[1:]]
        countries: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        geometry_by_profile = {name: {} for name in config["geometry_profiles"]}
        alias_config = region_config.get("aliases", {})
        if not isinstance(alias_config, dict):
            raise ValueError("regions.json 'aliases' must be an object")

        for index, item in enumerate(reader.iterShapeRecords()):
            attrs = {field: json_safe(value) for field, value in zip(fields, item.record)}
            original = shape(item.shape.__geo_interface__)
            if original.is_empty:
                raise ValueError(f"Feature {index} has empty geometry")
            if not original.is_valid:
                raise ValueError(f"Invalid source geometry at feature {index}: {explain_validity(original)}")

            raw_id = attrs.get(config.get("stable_id_field", ""))
            internal_id = str(raw_id).strip() if raw_id is not None else ""
            if internal_id in INVALID_IDENTIFIERS:
                internal_id = f"feature-{index:04d}"
            if internal_id in seen_ids:
                base_id = internal_id
                suffix = 1
                while f"{base_id}#{suffix:04d}" in seen_ids:
                    suffix += 1
                internal_id = f"{base_id}#{suffix:04d}"
            seen_ids.add(internal_id)

            iso = iso_candidate(attrs, config["iso3_fields"])
            name = next(
                (str(attrs[field]).strip() for field in config["name_fields"]
                 if attrs.get(field) not in (None, "")),
                internal_id,
            )
            raw_region = attrs.get(config.get("region_field", ""))
            regions = sorted(
                key for key, values in region_config.get("regions", {}).items()
                if raw_region == key or (isinstance(values, list) and raw_region in values)
            )
            aliases = []
            if iso and isinstance(alias_config.get(iso), list):
                aliases = [str(value) for value in alias_config[iso] if str(value).strip()]
            countries.append({
                "id": internal_id,
                "iso3": iso,
                "name": name,
                "aliases": aliases,
                "source_attributes": attrs,
                "regions": regions,
                "source_geometry_type": original.geom_type,
            })

            for profile, tolerance in config["geometry_profiles"].items():
                derived = original if float(tolerance) == 0 else original.simplify(float(tolerance), preserve_topology=True)
                if derived.is_empty or not derived.is_valid:
                    raise ValueError(
                        f"Invalid geometry after simplification for feature {index}, profile {profile}: "
                        f"{explain_validity(derived)}"
                    )
                geometry_by_profile[profile][internal_id] = mapping(derived)
    finally:
        reader.close()

    output.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "source": _source_provenance(source, config),
        "count": len(countries),
        "countries": countries,
        "aliases": alias_config,
        "region_audit": {
            "unmapped_count": sum(not country["regions"] for country in countries),
            "unmapped_ids": sorted(country["id"] for country in countries if not country["regions"]),
        },
    }
    country_bytes = (json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    generated_files: dict[str, bytes] = {"countries.json": country_bytes}
    for profile, geometries in geometry_by_profile.items():
        payload = {"schema_version": SCHEMA_VERSION, "profile": profile, "geometries": geometries}
        generated_files[f"geometry_{profile}.json"] = (
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")

    for filename, data in generated_files.items():
        (output / filename).write_bytes(data)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "files": {
            filename: {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
            for filename, data in sorted(generated_files.items())
        },
        "source": metadata["source"],
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("generated/town_country_asset"))
    parser.add_argument("--config", type=Path, default=Path("config/generation.json"))
    parser.add_argument("--regions", type=Path, default=Path("config/regions.json"))
    args = parser.parse_args()
    try:
        result = compile_data(args.source, args.output, args.config, args.regions)
    except Exception as exc:
        print(f"compile error: {exc}", file=sys.stderr)
        return 1
    print(f"Compiled {result['count']} features into {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
