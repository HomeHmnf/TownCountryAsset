extends SceneTree
## Run inside a Godot project that includes addons/town_country_asset/runtime/country_assets.gd:
## godot --headless --path . --script tests/godot/test_country_assets.gd

const TEST_ROOT := "user://town_country_asset_svg_test"


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    var absolute_root := ProjectSettings.globalize_path(TEST_ROOT)
    DirAccess.make_dir_recursive_absolute(absolute_root)

    var countries := {
        "schema_version": 1,
        "countries": [
            {"id": "TST", "iso3": "TST", "name": "Testland", "aliases": ["Test Republic"],
             "source_attributes": {}, "regions": []},
            {"id": "ISL", "iso3": "ISL", "name": "Islandia", "aliases": [],
             "source_attributes": {}, "regions": []},
        ],
    }
    _write_json(TEST_ROOT.path_join("countries.json"), countries)

    var polygon := {
        "type": "Polygon",
        "coordinates": [
            [[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]],
            [[2, 2], [8, 2], [8, 8], [2, 8], [2, 2]],
        ],
    }
    var multipolygon := {
        "type": "MultiPolygon",
        "coordinates": [
            [[[20, 0], [20, 1], [21, 1], [21, 0], [20, 0]]],
            [[[30, 0], [30, 1], [31, 1], [31, 0], [30, 0]]],
        ],
    }
    for profile in ["low", "medium", "high"]:
        _write_json(TEST_ROOT.path_join("geometry_%s.json" % profile), {
            "schema_version": 1,
            "profile": profile,
            "geometries": {"TST": polygon, "ISL": multipolygon},
        })

    var assets := CountryAssets.new(TEST_ROOT)
    assert assets.get_country("TST").get("name") == "Testland"
    assert assets.get_country("Test Republic").get("id") == "TST"
    assert assets.get_country("missing").is_empty()
    assert assets.get_geometry("TST", "low").get("type") == "Polygon"
    assert assets.get_geometry("ISL", "high").get("type") == "MultiPolygon"

    var polygon_svg := assets.get_country_svg("TST", "medium")
    assert not polygon_svg.is_empty()
    assert polygon_svg.contains('viewBox="0 0 512 512"')
    assert polygon_svg.contains('fill-rule="evenodd"')
    assert polygon_svg.count("M") == 2
    var multipart_svg := assets.get_country_svg("ISL", "low")
    assert not multipart_svg.is_empty()
    assert multipart_svg.count("M") == 2
    assert assets.get_country_svg("missing").is_empty()
    assert assets.get_country_svg("TST", "invalid").is_empty()

    print("CountryAssets runtime and SVG tests passed.")
    quit(0)


func _write_json(relative_path: String, value: Dictionary) -> void:
    var file := FileAccess.open(relative_path, FileAccess.WRITE)
    assert(file != null, "Could not write test fixture: " + relative_path)
    file.store_string(JSON.stringify(value))
    file.close()
