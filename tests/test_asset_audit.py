import hashlib
import json
from pathlib import Path

from tools.audit_generated_assets import audit_generated_assets


def write_json(path: Path, value) -> bytes:
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(data)
    return data


def make_assets(tmp_path: Path) -> Path:
    data_dir = tmp_path / "assets"
    data_dir.mkdir()
    metadata = {
        "schema_version": 1,
        "count": 2,
        "source": {"archive_sha256": "a" * 64},
        "source_schema": {"fields": ["ADM0_A3", "ISO_A3", "ADMIN"], "stable_id_field": "ADM0_A3",
                          "missing_configured_iso_fields": [], "missing_configured_name_fields": []},
        "build_inputs": {"generation_config_sha256": "b" * 64, "regions_config_sha256": "c" * 64},
        "countries": [
            {"id": "JPN", "iso3": "JPN", "name": "Japan", "regions": ["Asia"], "source_attributes": {}},
            {"id": "KOS", "iso3": None, "name": "Kosovo", "regions": [], "source_attributes": {}},
        ],
        "region_audit": {"unmapped_count": 1, "unmapped_ids": ["KOS"]},
    }
    files = {"countries.json": write_json(data_dir / "countries.json", metadata)}
    for profile in ("low", "medium", "high"):
        files[f"geometry_{profile}.json"] = write_json(
            data_dir / f"geometry_{profile}.json",
            {"schema_version": 1, "profile": profile, "geometries": {"JPN": {}, "KOS": {}}},
        )
    manifest = {
        "schema_version": 1,
        "files": {
            name: {"sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)}
            for name, content in sorted(files.items())
        },
        "source": metadata["source"],
        "source_schema": metadata["source_schema"],
        "build_inputs": metadata["build_inputs"],
    }
    write_json(data_dir / "manifest.json", manifest)
    return data_dir


def test_audit_accepts_consistent_assets(tmp_path):
    data_dir = make_assets(tmp_path)
    assert audit_generated_assets(data_dir) == []


def test_audit_detects_geometry_key_mismatch(tmp_path):
    data_dir = make_assets(tmp_path)
    geometry_path = data_dir / "geometry_low.json"
    payload = json.loads(geometry_path.read_text())
    payload["geometries"].pop("KOS")
    geometry_path.write_text(json.dumps(payload))
    errors = audit_generated_assets(data_dir)
    assert any("missing geometry IDs: KOS" in error for error in errors)
    assert any("SHA-256 does not match manifest" in error for error in errors)


def test_audit_detects_invalid_iso_and_region_audit_mismatch(tmp_path):
    data_dir = make_assets(tmp_path)
    metadata_path = data_dir / "countries.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["countries"][0]["iso3"] = "JPN1"
    metadata["region_audit"]["unmapped_ids"] = []
    write_json(metadata_path, metadata)
    errors = audit_generated_assets(data_dir)
    assert any("iso3 must be null or three uppercase ASCII letters" in error for error in errors)
    assert any("region_audit.unmapped_ids does not match" in error for error in errors)
    assert any("SHA-256 does not match manifest" in error for error in errors)
