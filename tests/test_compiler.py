import json
import zipfile
from pathlib import Path

import pytest
import shapefile
from shapely.geometry import shape

from tools.compile_natural_earth import compile_data, locate_shapefile


def make_fixture(tmp_path: Path) -> Path:
    base = tmp_path / "fixture"
    with shapefile.Writer(str(base), shapeType=shapefile.POLYGON) as writer:
        writer.field("ADM0_A3", "C", size=8)
        writer.field("ISO_A3", "C", size=8)
        writer.field("ADMIN", "C", size=40)
        writer.field("REGION_UN", "C", size=40)
        writer.poly([[(0, 0), (0, 10), (10, 10), (10, 0), (0, 0)],
                     [(2, 2), (8, 2), (8, 8), (2, 8), (2, 2)]])
        writer.record("TST", "TST", "Testland", "Asia")
        writer.poly([[(20, 0), (20, 1), (21, 1), (21, 0), (20, 0)]])
        writer.record("-99", "-99", "Islandia", "Oceania")
        writer.poly([[(30, 0), (30, 1), (31, 1), (31, 0), (30, 0)]])
        writer.record("TST", "TST", "Duplicate ID", "Asia")
    return base.with_suffix(".shp")


def write_config(tmp_path: Path):
    config = tmp_path / "generation.json"
    config.write_text(json.dumps({
        "schema_version": 1, "layer": "test", "scale": "test",
        "source_url": "https://example.invalid", "source_version": "fixture",
        "retrieval_date": "2026-01-01", "attribution": "fixture", "license": "fixture",
        "iso3_fields": ["ADM0_A3", "ISO_A3"], "name_fields": ["ADMIN"],
        "stable_id_field": "ADM0_A3", "region_field": "REGION_UN",
        "geometry_profiles": {"low": 0.1, "medium": 0.01, "high": 0.0},
    }))
    regions = tmp_path / "regions.json"
    regions.write_text(json.dumps({
        "regions": {"Asia": ["Asia"], "Oceania": ["Oceania"]},
        "aliases": {"TST": ["Testland", "Test Republic"]},
    }))
    return config, regions


def test_preserves_attributes_hole_missing_iso_and_aliases(tmp_path):
    source = make_fixture(tmp_path)
    config, regions = write_config(tmp_path)
    out = tmp_path / "out"
    result = compile_data(source, out, config, regions)
    assert result["count"] == 3
    first = result["countries"][0]
    assert first["source_attributes"]["ADMIN"] == "Testland"
    assert first["iso3"] == "TST"
    assert first["aliases"] == ["Testland", "Test Republic"]
    assert first["regions"] == ["Asia"]
    assert first["source_geometry_type"] == "Polygon"
    high = json.loads((out / "geometry_high.json").read_text())
    assert len(high["geometries"]["TST"]["coordinates"]) == 2
    assert result["countries"][1]["iso3"] is None
    assert result["countries"][1]["id"] == "feature-0001"
    assert result["countries"][2]["id"] == "TST#0001"


def test_output_files_and_manifest_checksums_are_deterministic(tmp_path):
    source = make_fixture(tmp_path)
    config, regions = write_config(tmp_path)
    a, b = tmp_path / "a", tmp_path / "b"
    compile_data(source, a, config, regions)
    compile_data(source, b, config, regions)
    for filename in ("countries.json", "geometry_low.json", "geometry_medium.json", "geometry_high.json", "manifest.json"):
        assert (a / filename).read_bytes() == (b / filename).read_bytes()
    manifest = json.loads((a / "manifest.json").read_text())
    assert manifest["schema_version"] == 1
    assert manifest["files"]["countries.json"]["sha256"]


def test_simplified_geometry_remains_valid(tmp_path):
    source = make_fixture(tmp_path)
    config, regions = write_config(tmp_path)
    out = tmp_path / "out"
    compile_data(source, out, config, regions)
    for profile in ("low", "medium", "high"):
        payload = json.loads((out / f"geometry_{profile}.json").read_text())
        for geometry in payload["geometries"].values():
            assert shape(geometry).is_valid


def test_zip_extraction_rejects_path_traversal(tmp_path):
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escaped.txt", "bad")
        archive.writestr("data.shp", b"not really a shapefile")
    with pytest.raises(ValueError, match="Unsafe path"):
        locate_shapefile(archive_path)
    assert not (tmp_path.parent / "escaped.txt").exists()


def test_directory_with_ambiguous_shapefiles_fails(tmp_path):
    source_dir = tmp_path / "many"
    source_dir.mkdir()
    (source_dir / "one.shp").write_bytes(b"")
    (source_dir / "two.SHP").write_bytes(b"")
    with pytest.raises(ValueError, match="exactly one"):
        locate_shapefile(source_dir)


def test_zip_input_records_archive_checksum(tmp_path):
    source = make_fixture(tmp_path)
    archive_path = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for path in source.parent.glob("fixture.*"):
            archive.write(path, path.name)
    config, regions = write_config(tmp_path)
    result = compile_data(archive_path, tmp_path / "zip-out", config, regions)
    assert len(result["source"]["archive_sha256"]) == 64
