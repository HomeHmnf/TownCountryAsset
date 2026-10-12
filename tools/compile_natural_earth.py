#!/usr/bin/env python3
"""Compile Natural Earth Admin 0 Countries into JSON metadata and geometry."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, math, sys, zipfile
from pathlib import Path
from typing import Any
import shapefile
from shapely.geometry import mapping, shape
from shapely.validation import explain_validity

SCHEMA_VERSION = 1

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def locate_shapefile(source: Path) -> Path:
    if source.is_dir():
        matches = sorted(source.rglob("*.shp"))
        if not matches: raise FileNotFoundError(f"No .shp file found under {source}")
        return matches[0]
    if source.suffix.lower() == ".shp": return source
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            if not any(n.lower().endswith(".shp") for n in archive.namelist()):
                raise ValueError(f"No .shp file found in {source}")
            work = source.parent / ".generated-tmp" / source.stem
            work.mkdir(parents=True, exist_ok=True)
            archive.extractall(work)
        matches = sorted(work.rglob("*.shp"))
        if not matches: raise FileNotFoundError("ZIP extraction produced no shapefile")
        return matches[0]
    raise ValueError("Source must be a .zip archive, .shp file, or extracted directory")

def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)): return value
    if isinstance(value, float): return value if math.isfinite(value) else None
    if hasattr(value, "item"): return json_safe(value.item())
    return str(value)

def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    profiles = config.get("geometry_profiles")
    if not isinstance(profiles, dict) or not profiles: raise ValueError("Config must define geometry_profiles")
    for name, tolerance in profiles.items():
        if not isinstance(tolerance, (int, float)) or tolerance < 0:
            raise ValueError(f"Invalid simplification tolerance for {name}")
    return config

def iso_candidate(attrs: dict[str, Any], fields: list[str]) -> str | None:
    for field in fields:
        value = attrs.get(field)
        if value is not None:
            value = str(value).strip()
            if value and value not in {"-99", "-"}: return value
    return None

def compile_data(source: Path, output: Path, config_path: Path, regions_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    region_config = json.loads(regions_path.read_text(encoding="utf-8"))
    shp_path = locate_shapefile(source)
    reader = shapefile.Reader(str(shp_path), encoding="utf-8")
    fields = [field[0] for field in reader.fields[1:]]
    countries, seen_ids = [], set()
    geometry_by_profile = {name: {} for name in config["geometry_profiles"]}
    for index, item in enumerate(reader.iterShapeRecords()):
        attrs = {field: json_safe(value) for field, value in zip(fields, item.record)}
        original = shape(item.shape.__geo_interface__)
        if original.is_empty: raise ValueError(f"Feature {index} has empty geometry")
        if not original.is_valid: raise ValueError(f"Invalid source geometry at feature {index}: {explain_validity(original)}")
        raw_id = attrs.get(config.get("stable_id_field", ""))
        internal_id = str(raw_id).strip() if raw_id not in (None, "", "-99", "-") else ""
        if not internal_id: internal_id = f"feature-{index:04d}"
        if internal_id in seen_ids: internal_id = f"{internal_id}#{index:04d}"
        seen_ids.add(internal_id)
        iso = iso_candidate(attrs, config.get("iso3_fields", []))
        name = next((str(attrs[f]).strip() for f in config.get("name_fields", []) if attrs.get(f) not in (None, "")), internal_id)
        raw_region = attrs.get(config.get("region_field", ""))
        regions = sorted(key for key, values in region_config.get("regions", {}).items() if raw_region == key or raw_region in values)
        countries.append({"id": internal_id, "iso3": iso, "name": name, "source_attributes": attrs,
                         "regions": regions, "source_geometry_type": original.geom_type})
        for profile, tolerance in config["geometry_profiles"].items():
            derived = original if float(tolerance) == 0 else original.simplify(float(tolerance), preserve_topology=True)
            geometry_by_profile[profile][internal_id] = mapping(derived)
    output.mkdir(parents=True, exist_ok=True)
    metadata = {"schema_version": SCHEMA_VERSION, "source": {
        "url": config.get("source_url"), "retrieval_date": config.get("retrieval_date"),
        "layer": config.get("layer"), "scale": config.get("scale"), "source_version": config.get("source_version"),
        "attribution": config.get("attribution"), "license": config.get("license"),
        "archive_sha256": sha256_file(source) if source.is_file() else None},
        "count": len(countries), "countries": countries, "aliases": region_config.get("aliases", {})}
    (output / "countries.json").write_text(json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    for profile, geometries in geometry_by_profile.items():
        payload = {"schema_version": SCHEMA_VERSION, "profile": profile, "geometries": geometries}
        (output / f"geometry_{profile}.json").write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    manifest = {"schema_version": SCHEMA_VERSION, "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "files": sorted(["countries.json"] + [f"geometry_{p}.json" for p in geometry_by_profile])}
    (output / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return metadata

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("generated/town_country_asset"))
    parser.add_argument("--config", type=Path, default=Path("config/generation.json"))
    parser.add_argument("--regions", type=Path, default=Path("config/regions.json"))
    args = parser.parse_args()
    try: result = compile_data(args.source, args.output, args.config, args.regions)
    except Exception as exc:
        print(f"compile error: {exc}", file=sys.stderr); return 1
    print(f"Compiled {result['count']} features into {args.output}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
