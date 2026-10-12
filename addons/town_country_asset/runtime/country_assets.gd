class_name CountryAssets
extends RefCounted
## Reader for JSON emitted by tools/compile_natural_earth.py.

const DATA_ROOT := "res://generated/town_country_asset"
var _data_root: String
var _metadata: Dictionary = {}
var _geometry_cache: Dictionary = {}

func _init(data_root: String = DATA_ROOT) -> void:
    _data_root = data_root
    var path := _data_root.path_join("countries.json")
    if not FileAccess.file_exists(path):
        push_warning("TownCountryAsset metadata not found: %s" % path)
        return
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(path))
    if parsed is Dictionary:
        _metadata = parsed
    else:
        push_error("Invalid TownCountryAsset metadata JSON: %s" % path)

func get_country(code_or_id: String) -> Dictionary:
    for country in _metadata.get("countries", []):
        if country.get("iso3", "") == code_or_id or country.get("id", "") == code_or_id:
            return country.duplicate(true)
    return {}

func get_all_attributes(code_or_id: String) -> Dictionary:
    return get_country(code_or_id).get("source_attributes", {}).duplicate(true)

func get_countries_by_region(region: String) -> Array:
    var result: Array = []
    for country in _metadata.get("countries", []):
        if region in country.get("regions", []):
            result.append(country.duplicate(true))
    return result

func get_geometry(code_or_id: String, profile: String = "medium") -> Dictionary:
    if not ["low", "medium", "high"].has(profile):
        push_warning("Unknown geometry profile: %s" % profile)
        return {}
    if not _geometry_cache.has(profile):
        var path := _data_root.path_join("geometry_%s.json" % profile)
        if not FileAccess.file_exists(path):
            push_warning("TownCountryAsset geometry not found: %s" % path)
            return {}
        var parsed = JSON.parse_string(FileAccess.get_file_as_string(path))
        if not parsed is Dictionary:
            push_error("Invalid geometry JSON: %s" % path)
            return {}
        _geometry_cache[profile] = parsed.get("geometries", {})
    var country := get_country(code_or_id)
    var internal_id: String = country.get("id", "")
    return _geometry_cache[profile].get(internal_id, {}).duplicate(true)

func get_country_svg(_code_or_id: String, _profile: String = "medium") -> String:
    # Not implemented: callers must choose a projection and viewport before SVG generation.
    return ""
