import json
from pathlib import Path
import shapefile
from tools.compile_natural_earth import compile_data


def make_fixture(tmp_path: Path) -> Path:
    base = tmp_path / "fixture"
    with shapefile.Writer(str(base), shapeType=shapefile.POLYGON) as writer:
        writer.field("ADM0_A3", "C", size=8)
        writer.field("ISO_A3", "C", size=8)
        writer.field("ADMIN", "C", size=40)
        writer.field("REGION_UN", "C", size=40)
        writer.poly([[(0,0),(0,10),(10,10),(10,0),(0,0)], [(2,2),(8,2),(8,8),(2,8),(2,2)]])
        writer.record("TST", "TST", "Testland", "Asia")
        writer.poly([[(20,0),(20,1),(21,1),(21,0),(20,0)]])
        writer.record("-99", "-99", "Islandia", "Oceania")
    return base.with_suffix(".shp")


def write_config(tmp_path: Path):
    config = tmp_path / "generation.json"
    config.write_text(json.dumps({"schema_version":1,"layer":"test","scale":"test",
        "source_url":"https://example.invalid","source_version":"fixture","retrieval_date":"2026-01-01",
        "attribution":"fixture","license":"fixture","iso3_fields":["ADM0_A3","ISO_A3"],
        "name_fields":["ADMIN"],"stable_id_field":"ADM0_A3","region_field":"REGION_UN",
        "geometry_profiles":{"low":0.1,"medium":0.01,"high":0.0}}))
    regions = tmp_path / "regions.json"
    regions.write_text(json.dumps({"regions":{"Asia":["Asia"],"Oceania":["Oceania"]},"aliases":{}}))
    return config, regions


def test_preserves_attributes_hole_and_missing_iso(tmp_path):
    source = make_fixture(tmp_path)
    config, regions = write_config(tmp_path)
    out = tmp_path / "out"
    result = compile_data(source, out, config, regions)
    assert result["count"] == 2
    first = result["countries"][0]
    assert first["source_attributes"]["ADMIN"] == "Testland"
    assert first["iso3"] == "TST"
    assert first["regions"] == ["Asia"]
    assert first["source_geometry_type"] == "Polygon"
    high = json.loads((out / "geometry_high.json").read_text())
    assert len(high["geometries"]["TST"]["coordinates"]) == 2
    assert result["countries"][1]["iso3"] is None
    assert result["countries"][1]["id"] == "feature-0001"


def test_country_output_is_deterministic(tmp_path):
    source = make_fixture(tmp_path)
    config, regions = write_config(tmp_path)
    a, b = tmp_path / "a", tmp_path / "b"
    compile_data(source, a, config, regions)
    compile_data(source, b, config, regions)
    assert (a / "countries.json").read_bytes() == (b / "countries.json").read_bytes()
    assert json.loads((a / "manifest.json").read_text())["schema_version"] == 1
