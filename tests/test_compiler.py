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
        writer.field("SUBREGION", "C", size=40)
        writer.poly([[(0, 0), (0, 10), (10, 10), (10, 0), (0, 0)],
                     [(2, 2), (8, 2), (8, 8), (2, 8), (2, 2)]])
        writer.record("TST", "TST", "Testland", "Asia", "Eastern Asia")
        writer.poly([[(20, 0), (20, 1), (21, 1), (21, 0), (20, 0)]])
        writer.record("ISL", "-99", "Islandia", "Oceania", "Australia and New Zealand")
        writer.poly([[(30, 0), (30, 1), (31, 1), (31, 0), (30, 0)]])
        writer.record("DUP", "DUP", "Distinct ID", "Asia", "Eastern Asia")
    return base.with_suffix(".shp")


def write_config(tmp_path: Path):
    config = tmp_path / "generation.json"
    config.write_text(json.dumps({
        "schema_version": 1, "layer": "test", "scale": "test",
        "source_url": "https://example.invalid", "source_version": "fixture",
        "retrieval_date": "2026-01-01", "attribution": "fixture", "license": "fixture",
        "iso3_fields": ["ISO_A3"], "name_fields": ["ADMIN"],
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
    assert result["countries"][1]["id"] == "ISL"
    assert result["countries"][2]["id"] == "DUP"


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


def test_identity_registry_adds_game_ids_and_parallel_geometry_without_breaking_legacy_keys(tmp_path):
    from tools.country_identity_registry import bootstrap

    source = make_fixture(tmp_path)
    config, regions = write_config(tmp_path)
    # Build the same source metadata once without a registry to bootstrap a test registry.
    base = compile_data(source, tmp_path / "base", config, regions)
    registry_path = tmp_path / "identity_registry.json"
    registry_path.write_text(json.dumps(bootstrap(base)), encoding="utf-8")

    out = tmp_path / "with-identities"
    result = compile_data(source, out, config, regions, registry_path)
    by_source_id = {country["id"]: country for country in result["countries"]}
    registry = json.loads(registry_path.read_text())
    game_id_by_source = {
        record["source"]["current_source_id"]: record["game_id"]
        for record in registry["records"]
    }

    assert set(by_source_id) == {"TST", "ISL", "DUP"}
    assert all(by_source_id[source_id]["game_id"] == game_id
               for source_id, game_id in game_id_by_source.items())
    assert by_source_id["ISL"]["iso3"] is None
    assert by_source_id["TST"]["source_attributes"]["ADMIN"] == "Testland"

    legacy_geometry = json.loads((out / "geometry_high.json").read_text())
    canonical_geometry = json.loads((out / "geometry_game_id_high.json").read_text())
    assert set(legacy_geometry["geometries"]) == {"TST", "ISL", "DUP"}
    assert set(canonical_geometry["geometries"]) == set(game_id_by_source.values())
    assert canonical_geometry["key"] == "game_id"
    manifest = json.loads((out / "manifest.json").read_text())
    assert "geometry_game_id_high.json" in manifest["files"]
    assert result["identity_registry"]["game_id_count"] == 3


def test_compiler_preserves_game_id_when_source_id_is_explicitly_renamed(tmp_path):
    from tools.country_identity_registry import bootstrap

    source = make_fixture(tmp_path)
    config, regions = write_config(tmp_path)
    base = compile_data(source, tmp_path / "base", config, regions)
    registry = bootstrap(base)
    target = next(
        record for record in registry["records"]
        if record["source"]["current_source_id"] == "TST"
    )
    stable_game_id = target["game_id"]
    target["source"]["current_source_id"] = "TST_NEW"
    target["source"]["previous_source_ids"] = ["TST"]
    target["geometry_key"] = "TST_NEW"
    registry_path = tmp_path / "identity_registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    # Simulate an upstream source-ID rename while preserving the feature's
    # other attributes and geometry.
    reader = shapefile.Reader(str(source))
    fields = [field[0] for field in reader.fields[1:]]
    records = [dict(zip(fields, record)) for record in reader.records()]
    geometries = list(reader.iterShapes())
    reader.close()
    records[0]["ADM0_A3"] = "TST_NEW"
    renamed_base = tmp_path / "renamed-source"
    with shapefile.Writer(str(renamed_base), shapeType=shapefile.POLYGON) as writer:
        for field in fields:
            writer.field(field, "C", size=40)
        for geometry, record in zip(geometries, records):
            writer.shape(geometry)
            writer.record(*[record[field] for field in fields])

    out = tmp_path / "renamed-output"
    result = compile_data(renamed_base.with_suffix(".shp"), out, config, regions, registry_path)
    renamed = next(country for country in result["countries"] if country["id"] == "TST_NEW")
    assert renamed["game_id"] == stable_game_id
    assert renamed["name"] == "Testland"
    assert renamed["source_attributes"]["ADMIN"] == "Testland"

    canonical = json.loads((out / "geometry_game_id_high.json").read_text())
    assert stable_game_id in canonical["geometries"]
    assert "TST_NEW" not in canonical["geometries"]

def test_compiler_with_identity_registry_fails_on_unmapped_source_feature(tmp_path):
    from tools.country_identity_registry import bootstrap

    source = make_fixture(tmp_path)
    config, regions = write_config(tmp_path)
    base = compile_data(source, tmp_path / "base", config, regions)
    registry = bootstrap(base)
    registry["records"].pop()
    registry_path = tmp_path / "identity_registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    with pytest.raises(ValueError, match="Identity registry validation failed"):
        compile_data(source, tmp_path / "out", config, regions, registry_path)


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



def test_iso_code_never_falls_back_to_administrative_id_and_regions_use_subregion(tmp_path):
    source = make_fixture(tmp_path)
    config, regions = write_config(tmp_path)
    config_data = json.loads(config.read_text())
    config_data["iso3_fields"] = ["ISO_A3"]
    config_data["region_field"] = "SUBREGION"
    config.write_text(json.dumps(config_data))
    region_data = json.loads(regions.read_text())
    region_data["regions"] = {
        "North America": ["Northern America", "Central America", "Caribbean"],
        "South America": ["South America"],
        "Asia": ["Eastern Asia"],
        "Oceania": ["Australia and New Zealand"],
    }
    regions.write_text(json.dumps(region_data))

    # A source admin ID can differ from the ISO code; only ISO_A3 is used.
    source_iso = shapefile.Reader(str(source))
    try:
        fields = [field[0] for field in source_iso.fields[1:]]
        records = [dict(zip(fields, record)) for record in source_iso.records()]
    finally:
        source_iso.close()
    assert records[0]["ADM0_A3"] == "TST"
    assert records[0]["ISO_A3"] == "TST"

    result = compile_data(source, tmp_path / "out", config, regions)
    assert result["countries"][0]["iso3"] == "TST"
    assert result["countries"][0]["regions"] == ["Asia"]
    assert result["countries"][1]["iso3"] is None
    assert result["region_audit"]["unmapped_count"] == 0


def test_iso_candidate_rejects_non_iso_source_identifiers():
    from tools.compile_natural_earth import iso_candidate

    assert iso_candidate({"ADM0_A3": "SDS", "ISO_A3": "SSD"}, ["ISO_A3"]) == "SSD"
    assert iso_candidate({"ADM0_A3": "KOS", "ISO_A3": "-99"}, ["ISO_A3"]) is None
    assert iso_candidate({"ISO_A3": "ABC1"}, ["ISO_A3"]) is None


def test_compiler_keeps_admin_id_separate_from_iso3(tmp_path):
    base = tmp_path / "identity-fixture"
    with shapefile.Writer(str(base), shapeType=shapefile.POLYGON) as writer:
        writer.field("ADM0_A3", "C", size=8)
        writer.field("ISO_A3", "C", size=8)
        writer.field("ADMIN", "C", size=40)
        writer.field("REGION_UN", "C", size=40)
        writer.field("SUBREGION", "C", size=40)
        writer.poly([[(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]])
        writer.record("SDS", "SSD", "South Sudan", "Africa", "Eastern Africa")
        writer.poly([[(2, 0), (2, 1), (3, 1), (3, 0), (2, 0)]])
        writer.record("KOS", "-99", "Kosovo", "Europe", "Southern Europe")
    config, regions = write_config(tmp_path)
    config_data = json.loads(config.read_text())
    config_data["iso3_fields"] = ["ISO_A3"]
    config_data["region_field"] = "SUBREGION"
    config.write_text(json.dumps(config_data))
    region_data = json.loads(regions.read_text())
    region_data["regions"] = {
        "Africa": ["Eastern Africa"],
        "Europe": ["Southern Europe"],
    }
    regions.write_text(json.dumps(region_data))

    result = compile_data(base.with_suffix(".shp"), tmp_path / "out", config, regions)
    south_sudan, kosovo = result["countries"]
    assert south_sudan["id"] == "SDS"
    assert south_sudan["iso3"] == "SSD"
    assert kosovo["id"] == "KOS"
    assert kosovo["iso3"] is None


def test_americas_subregions_are_classified_and_exceptions_are_reported(tmp_path):
    base = tmp_path / "americas-fixture"
    with shapefile.Writer(str(base), shapeType=shapefile.POLYGON) as writer:
        writer.field("ADM0_A3", "C", size=8)
        writer.field("ISO_A3", "C", size=8)
        writer.field("ADMIN", "C", size=40)
        writer.field("REGION_UN", "C", size=40)
        writer.field("SUBREGION", "C", size=40)
        for index, (admin_id, name, subregion) in enumerate([
            ("CAN", "Canada", "Northern America"),
            ("BLZ", "Belize", "Central America"),
            ("JAM", "Jamaica", "Caribbean"),
            ("BRA", "Brazil", "South America"),
            ("SGS", "South Georgia", "Seven seas (open ocean)"),
        ]):
            x = index * 2
            writer.poly([[(x, 0), (x, 1), (x + 1, 1), (x + 1, 0), (x, 0)]])
            writer.record(admin_id, admin_id, name, "Americas", subregion)

    config, regions = write_config(tmp_path)
    config_data = json.loads(config.read_text())
    config_data["region_field"] = "SUBREGION"
    config.write_text(json.dumps(config_data))
    region_data = json.loads(regions.read_text())
    region_data["regions"] = {
        "North America": ["Northern America", "Central America", "Caribbean"],
        "South America": ["South America"],
    }
    regions.write_text(json.dumps(region_data))

    result = compile_data(base.with_suffix(".shp"), tmp_path / "out", config, regions)
    by_id = {country["id"]: country for country in result["countries"]}
    assert by_id["CAN"]["regions"] == ["North America"]
    assert by_id["BLZ"]["regions"] == ["North America"]
    assert by_id["JAM"]["regions"] == ["North America"]
    assert by_id["BRA"]["regions"] == ["South America"]
    assert result["region_audit"]["unmapped_count"] == 1
    assert result["region_audit"]["unmapped_ids"] == ["SGS"]



def test_missing_configured_stable_id_field_fails_explicitly(tmp_path):
    source = make_fixture(tmp_path)
    config, regions = write_config(tmp_path)
    config_data = json.loads(config.read_text())
    config_data["stable_id_field"] = "MISSING_ID"
    config.write_text(json.dumps(config_data))

    with pytest.raises(ValueError, match="stable_id_field.*absent from source schema"):
        compile_data(source, tmp_path / "out", config, regions)


def test_unusable_stable_id_fails_instead_of_using_feature_order(tmp_path):
    source = make_fixture(tmp_path)
    reader = shapefile.Reader(str(source))
    fields = [field[0] for field in reader.fields[1:]]
    records = [dict(zip(fields, record)) for record in reader.records()]
    shapes = list(reader.iterShapes())
    reader.close()
    base = tmp_path / "invalid-id"
    with shapefile.Writer(str(base), shapeType=shapefile.POLYGON) as writer:
        for field in fields:
            writer.field(field, "C", size=40)
        for geom, record in zip(shapes, records):
            writer.shape(geom)
            writer.record(*[("-99" if field == "ADM0_A3" else record[field]) for field in fields])
    config, regions = write_config(tmp_path)
    with pytest.raises(ValueError, match="refusing to create an order-dependent ID"):
        compile_data(base.with_suffix(".shp"), tmp_path / "out", config, regions)


def test_duplicate_stable_ids_fail_instead_of_being_suffixed(tmp_path):
    source = make_fixture(tmp_path)
    reader = shapefile.Reader(str(source))
    fields = [field[0] for field in reader.fields[1:]]
    records = [dict(zip(fields, record)) for record in reader.records()]
    shapes = list(reader.iterShapes())
    reader.close()
    records[2]["ADM0_A3"] = records[0]["ADM0_A3"]
    base = tmp_path / "duplicate-id"
    with shapefile.Writer(str(base), shapeType=shapefile.POLYGON) as writer:
        for field in fields:
            writer.field(field, "C", size=40)
        for geom, record in zip(shapes, records):
            writer.shape(geom)
            writer.record(*[record[field] for field in fields])
    config, regions = write_config(tmp_path)
    with pytest.raises(ValueError, match="Duplicate value.*source IDs must be unique"):
        compile_data(base.with_suffix(".shp"), tmp_path / "out", config, regions)


def test_manifest_records_source_schema_and_config_hashes(tmp_path):
    source = make_fixture(tmp_path)
    config, regions = write_config(tmp_path)
    out = tmp_path / "out"
    compile_data(source, out, config, regions)
    metadata = json.loads((out / "countries.json").read_text())
    manifest = json.loads((out / "manifest.json").read_text())
    assert metadata["source_schema"]["stable_id_field"] == "ADM0_A3"
    assert "ADM0_A3" in metadata["source_schema"]["fields"]
    assert metadata["build_inputs"]["generation_config_sha256"]
    assert metadata["build_inputs"]["regions_config_sha256"]
    assert manifest["source_schema"] == metadata["source_schema"]
    assert manifest["build_inputs"] == metadata["build_inputs"]
