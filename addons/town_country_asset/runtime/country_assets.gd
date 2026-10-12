class_name CountryAssets
extends RefCounted
## Reader and lightweight SVG renderer for JSON emitted by the country compiler.

const DATA_ROOT := "res://generated/town_country_asset"
const SVG_SIZE := 512.0
const SVG_PADDING := 8.0

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
    var query := code_or_id.strip_edges().to_lower()
    for country in _metadata.get("countries", []):
        if str(country.get("iso3", "")).to_lower() == query:
            return country.duplicate(true)
        if str(country.get("id", "")).to_lower() == query:
            return country.duplicate(true)
        if str(country.get("name", "")).to_lower() == query:
            return country.duplicate(true)
        for alias in country.get("aliases", []):
            if str(alias).to_lower() == query:
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


func get_country_svg(code_or_id: String, profile: String = "medium") -> String:
    var geometry := get_geometry(code_or_id, profile)
    if geometry.is_empty():
        return ""
    var geometry_type: String = str(geometry.get("type", ""))
    if not ["Polygon", "MultiPolygon"].has(geometry_type):
        push_warning("SVG renderer supports Polygon and MultiPolygon, got: %s" % geometry_type)
        return ""

    var positions: Array[Vector2] = []
    _collect_positions(geometry.get("coordinates", []), positions)
    if positions.is_empty():
        return ""
    var min_x := positions[0].x
    var max_x := positions[0].x
    var min_y := positions[0].y
    var max_y := positions[0].y
    for point in positions:
        min_x = minf(min_x, point.x)
        max_x = maxf(max_x, point.x)
        min_y = minf(min_y, point.y)
        max_y = maxf(max_y, point.y)

    var span_x := maxf(max_x - min_x, 0.000001)
    var span_y := maxf(max_y - min_y, 0.000001)
    var usable := SVG_SIZE - SVG_PADDING * 2.0
    var scale := minf(usable / span_x, usable / span_y)
    var drawn_width := span_x * scale
    var drawn_height := span_y * scale
    var offset_x := (SVG_SIZE - drawn_width) * 0.5
    var offset_y := (SVG_SIZE - drawn_height) * 0.5

    var path_data := _build_svg_rings(geometry.get("coordinates", []), min_x, max_y, scale, offset_x, offset_y)
    if path_data.is_empty():
        return ""
    return '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">' + \
        '<path d="' + path_data + '" fill="currentColor" fill-rule="evenodd" stroke="currentColor" stroke-width="0.5" stroke-linejoin="round"/></svg>'


func _is_position(value: Variant) -> bool:
    if not value is Array or value.size() < 2:
        return false
    var x_type := typeof(value[0])
    var y_type := typeof(value[1])
    return (x_type == TYPE_FLOAT or x_type == TYPE_INT) and (y_type == TYPE_FLOAT or y_type == TYPE_INT)


func _collect_positions(value: Variant, positions: Array[Vector2]) -> void:
    if _is_position(value):
        positions.append(Vector2(float(value[0]), float(value[1])))
        return
    if value is Array:
        for child in value:
            _collect_positions(child, positions)



func _build_svg_rings(value: Variant, min_x: float, max_y: float, scale: float,
        offset_x: float, offset_y: float) -> String:
    if not value is Array or value.is_empty():
        return ""
    if _is_position(value[0]):
        var commands := ""
        for index in range(value.size()):
            var point = value[index]
            var x := offset_x + (float(point[0]) - min_x) * scale
            var y := offset_y + (max_y - float(point[1])) * scale
            commands += ("M" if index == 0 else "L") + String.num(x, 3) + "," + String.num(y, 3)
        return commands + "Z"
    var result := ""
    for child in value:
        result += _build_svg_rings(child, min_x, max_y, scale, offset_x, offset_y)
    return result
