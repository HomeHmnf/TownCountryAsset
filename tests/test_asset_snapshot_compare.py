import hashlib
import json
from pathlib import Path

from tools.compare_asset_snapshots import compare_snapshots


def write_snapshot(root: Path, countries: list[dict], source_hash: str, schema_fields: list[str]):
    root.mkdir(parents=True)
    metadata = {
        "schema_version": 1,
        "source": {"archive_sha256": source_hash, "source_version": "fixture"},
        "source_schema": {"fields": schema_fields, "stable_id_field": "ADM0_A3",
                          "missing_configured_iso_fields": [], "missing_configured_name_fields": []},
        "build_inputs": {"generation_config_sha256": "a" * 64, "regions_config_sha256": "b" * 64},
        "count": len(countries),
        "countries": countries,
    }
    (root / "countries.json").write_text(json.dumps(metadata), encoding="utf-8")
    files = {}
    for profile in ("low", "medium", "high"):
        payload = {"schema_version": 1, "profile": profile,
                   "geometries": {country["id"]: {"type": "Point", "coordinates": [i, 0]}
                                  for i, country in enumerate(countries)}}
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        (root / f"geometry_{profile}.json").write_text(data, encoding="utf-8")
    for filename in ("countries.json", "geometry_low.json", "geometry_medium.json", "geometry_high.json"):
        data = (root / filename).read_bytes()
        files[filename] = {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
    manifest = {"schema_version": 1, "files": files, "source": metadata["source"],
                "source_schema": metadata["source_schema"], "build_inputs": metadata["build_inputs"]}
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def country(country_id: str, iso3: str, name: str):
    return {"id": country_id, "iso3": iso3, "name": name, "aliases": [],
            "regions": ["Europe"], "source_geometry_type": "Polygon",
            "source_attributes": {"ADM0_A3": country_id, "ISO_A3": iso3, "ADMIN": name}}


def test_reports_added_removed_rekeyed_and_metadata_changes(tmp_path):
    old = tmp_path / "old"
    new = tmp_path / "new"
    write_snapshot(old, [country("OLD", "AAA", "Old Name"), country("KEEP", "BBB", "Keep")],
                   "1" * 64, ["ADM0_A3", "ISO_A3", "ADMIN"])
    write_snapshot(new, [country("NEW", "AAA", "New Name"), country("KEEP", "BBB", "Keep Changed"),
                         country("ADD", "CCC", "Added")],
                   "2" * 64, ["ADM0_A3", "ISO_A3", "ADMIN", "NEW_FIELD"])

    report = compare_snapshots(old, new)
    assert report["source_archive_sha256"]["changed"] is True
    assert report["source_schema"]["changed"] is True
    assert report["feature_count"] == {"old": 2, "new": 3, "delta": 1}
    assert report["added_ids"] == ["ADD", "NEW"]
    assert report["removed_ids"] == ["OLD"]
    assert report["possible_rekeys_by_unique_iso3"][0]["old_id"] == "OLD"
    assert report["possible_rekeys_by_unique_iso3"][0]["new_id"] == "NEW"
    assert any(item["id"] == "KEEP" for item in report["changed_existing_features"])
    assert "Review all ID" in report["warning"]


def test_compare_rejects_duplicate_ids_in_snapshot(tmp_path):
    old = tmp_path / "old"
    write_snapshot(old, [country("DUP", "AAA", "One"), country("DUP", "BBB", "Two")],
                   "1" * 64, ["ADM0_A3", "ISO_A3", "ADMIN"])
    try:
        compare_snapshots(old, old)
    except ValueError as exc:
        assert "duplicate country ID" in str(exc)
    else:
        raise AssertionError("expected duplicate IDs to be rejected")
