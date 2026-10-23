#!/usr/bin/env python3
"""Generate fitted SVG previews from compiled TownCountryAsset geometry JSON.

This is a build-time tool. The Godot runtime does not require Python.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

SVG_SIZE = 512
SVG_PADDING = 8
PROFILES = ("low", "medium", "high")


def _is_position(value: Any) -> bool:
    return (
        isinstance(value, list) and len(value) >= 2
        and isinstance(value[0], (int, float)) and not isinstance(value[0], bool)
        and isinstance(value[1], (int, float)) and not isinstance(value[1], bool)
    )


def _positions(value: Any):
    if _is_position(value):
        yield float(value[0]), float(value[1])
    elif isinstance(value, list):
        for child in value:
            yield from _positions(child)


def _rings(value: Any):
    if not isinstance(value, list) or not value:
        return
    if _is_position(value[0]):
        yield value
    else:
        for child in value:
            yield from _rings(child)


def geometry_to_svg(geometry: dict[str, Any], *, size: int = SVG_SIZE) -> str:
    """Render a GeoJSON Polygon or MultiPolygon into a fitted SVG string."""
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if kind not in ("Polygon", "MultiPolygon") or not isinstance(coordinates, list):
        raise ValueError("geometry must be a GeoJSON Polygon or MultiPolygon")
    points = list(_positions(coordinates))
    if not points:
        raise ValueError("geometry contains no coordinate positions")

    min_x = min(x for x, _ in points)
    max_x = max(x for x, _ in points)
    min_y = min(y for _, y in points)
    max_y = max(y for _, y in points)
    span_x = max(max_x - min_x, 1e-6)
    span_y = max(max_y - min_y, 1e-6)
    usable = size - SVG_PADDING * 2
    scale = min(usable / span_x, usable / span_y)
    offset_x = (size - span_x * scale) / 2
    offset_y = (size - span_y * scale) / 2

    commands: list[str] = []
    for ring in _rings(coordinates):
        if len(ring) < 3:
            continue
        for index, point in enumerate(ring):
            x = offset_x + (float(point[0]) - min_x) * scale
            y = offset_y + (max_y - float(point[1])) * scale
            commands.append(("M" if index == 0 else "L") + f"{x:.3f},{y:.3f}")
        commands.append("Z")
    if not commands:
        raise ValueError("geometry contains no drawable rings")

    root = Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "width": str(size), "height": str(size),
        "viewBox": f"0 0 {size} {size}",
    })
    SubElement(root, "path", {
        "d": "".join(commands),
        "fill": "currentColor",
        "fill-rule": "evenodd",
        "stroke": "currentColor",
        "stroke-width": "0.5",
        "stroke-linejoin": "round",
    })
    return tostring(root, encoding="unicode", short_empty_elements=True)


def safe_filename(identifier: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", identifier).strip("._")
    if not cleaned:
        raise ValueError(f"identifier cannot be represented as a filename: {identifier!r}")
    return cleaned


def generate_svgs(data_root: Path, output_root: Path, profiles: tuple[str, ...] = PROFILES) -> int:
    metadata_path = data_root / "countries.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"metadata file not found: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    countries = metadata.get("countries")
    if not isinstance(countries, list):
        raise ValueError("countries.json must contain a countries array")

    written = 0
    for profile in profiles:
        if profile not in PROFILES:
            raise ValueError(f"unknown profile {profile!r}; choose from {', '.join(PROFILES)}")
        geometry_path = data_root / f"geometry_{profile}.json"
        payload = json.loads(geometry_path.read_text(encoding="utf-8"))
        geometries = payload.get("geometries")
        if not isinstance(geometries, dict):
            raise ValueError(f"{geometry_path} must contain a geometries object")
        profile_dir = output_root / profile
        profile_dir.mkdir(parents=True, exist_ok=True)
        for country in countries:
            identifier = str(country.get("id", ""))
            geometry = geometries.get(identifier)
            if geometry is None:
                raise ValueError(f"missing {profile} geometry for country id {identifier!r}")
            destination = profile_dir / f"{safe_filename(identifier)}.svg"
            destination.write_text(geometry_to_svg(geometry) + "\n", encoding="utf-8")
            written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("generated/town_country_asset"))
    parser.add_argument("--output", type=Path, default=Path("generated/town_country_asset/svg"))
    parser.add_argument("--profile", choices=PROFILES, action="append",
                        help="profile to generate; repeat to select multiple (default: all)")
    args = parser.parse_args()
    try:
        count = generate_svgs(args.data, args.output, tuple(args.profile or PROFILES))
    except Exception as exc:
        print(f"SVG generation error: {exc}", file=sys.stderr)
        return 1
    print(f"Generated {count} SVG files in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
