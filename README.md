# TownCountryAsset

A Natural Earth–based country asset pipeline for Godot. Python processes source data at build time; GDScript reads generated data at runtime.

## Status

The compiler accepts a local Natural Earth Admin 0 Countries 1:50m ZIP, shapefile, or extracted shapefile directory. It does not download data automatically or fabricate missing ISO codes. ZIP extraction rejects traversal paths and symbolic links, and ambiguous inputs containing multiple shapefiles fail rather than selecting an arbitrary layer.

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
var svg = assets.get_country_svg("JPN", "medium")
```

Country lookup accepts the source ISO candidate, stable internal ID, normalized country name, or configured aliases. SVG output is a 512×512 equirectangular fit of the country's existing GeoJSON coordinates; it is intended for previews and is not a cartographic projection suitable for area or distance analysis. Polygon holes use the SVG even-odd fill rule. Antimeridian-crossing features may need a projection-aware renderer for visually ideal results.

## Build provenance and determinism

- The manifest contains SHA-256 and byte size for each generated JSON payload.
- When the source is a ZIP, the source archive SHA-256 is recorded in metadata and the manifest.
- Generated JSON and the manifest do not include build timestamps, so identical inputs/configuration produce byte-identical outputs.
- Before publishing an asset build, fill `source_version` and `retrieval_date` in `config/generation.json` with the release and date actually used. These are deliberately `null` by default rather than guessed.
- The compiler does not independently verify Natural Earth release identity; the source archive hash records exactly which ZIP was compiled.

## Design requirements

- Preserve all original source attributes.
- Record source URL, retrieval date, layer/version, archive SHA-256, attribution and license.
- Never infer or synthesize ISO identifiers. `feature-NNNN` is an internal fallback only.
- Keep stable IDs unique even when source identifiers are missing or duplicated.
- Preserve multipart polygons, islands and holes; simplification is applied to derived copies only and every derived geometry is validated.
- Emit low/medium/high geometry profiles and schema versions.
- Keep region classifications and aliases configurable and separate from source attributes.

## Attribution

Natural Earth data is public domain; retain source attribution and provenance for reproducible builds. See [Natural Earth terms](https://www.naturalearthdata.com/about/terms-of-use/).
