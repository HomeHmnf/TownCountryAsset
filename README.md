# TownCountryAsset

A Natural Earth–based country asset pipeline for Godot. Python processes source data at build time; GDScript reads generated data at runtime.

## Status

Initial compiler/runtime implementation. It expects a local Natural Earth Admin 0 Countries 1:50m ZIP, shapefile, or extracted shapefile directory. It does not silently download data or invent missing ISO codes.

## Quick start

1. Download [Natural Earth Admin 0 – Countries (1:50m)](https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-0-countries/).
2. Install dependencies: `python -m pip install -e ".[dev]"`
3. Compile: `python tools/compile_natural_earth.py --source /path/to/ne_50m_admin_0_countries.zip --output generated/town_country_asset`
4. Copy `addons/town_country_asset` and the generated output into your Godot project. The default runtime data path is `res://generated/town_country_asset`.

## Runtime API

```gdscript
var assets := CountryAssets.new()
var country = assets.get_country("JPN")
var attrs = assets.get_all_attributes("JPN")
var asia = assets.get_countries_by_region("Asia")
var geometry = assets.get_geometry("JPN", "medium")
```

`get_country_svg()` is reserved but not implemented yet; projection and SVG viewport rules need to be specified before emitting map artwork.

## Design requirements

- Preserve original source archive and all source attributes.
- Record source URL, retrieval date, layer/version, SHA-256, attribution and license.
- Use stable internal IDs; do not fabricate missing ISO codes.
- Preserve multipart polygons, islands and holes; simplification is applied to derived copies only.
- Emit low/medium/high geometry profiles and schema versions.
- Keep region classifications configurable and separate from source attributes.

## Attribution

Natural Earth data is public domain; retain source attribution and provenance in generated builds. See [Natural Earth terms](https://www.naturalearthdata.com/about/terms-of-use/).
