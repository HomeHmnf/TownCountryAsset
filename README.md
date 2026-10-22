# TownCountryAsset

A Natural Earth–based country asset pipeline for Godot. Python is used only for offline asset preparation; the game runtime uses GDScript and precomputed JSON/SVG assets. No Python or C# runtime dependency is required on player devices.

## Architecture

- **Offline build tools (Python):** read local Natural Earth source data, preserve source attributes and provenance, validate geometries, derive low/medium/high detail profiles, and optionally generate static SVG files.
- **Godot runtime (GDScript):** query country metadata, load geometry profiles on demand, and render/highlight entities without recompiling source data.
- **Mobile game:** ships only generated assets and the Godot project. No Python dependency is needed at runtime.

Use GDScript first. Introducing C# would create a mixed-language project and does not automatically make loading precomputed data faster. Consider native/C# optimization only if profiling identifies a CPU-heavy runtime bottleneck.

## Status

The compiler accepts a local Natural Earth Admin 0 Countries 1:50m ZIP, shapefile, or extracted shapefile directory. It does not download data automatically or fabricate missing ISO codes. ZIP extraction rejects traversal paths and symbolic links, and ambiguous inputs containing multiple shapefiles fail rather than selecting an arbitrary layer. The configured stable-ID field must exist and contain unique, usable values; the compiler fails instead of generating order-dependent IDs or silently suffixing duplicates. Metadata and the manifest record source fields and SHA-256 fingerprints of both configuration files.

## Quick start (Linux / fish)

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if needed:
   ```fish
   curl -LsSf https://astral.sh/uv/install.sh | sh
   fish_add_path ~/.local/bin
   ```
   If `uv` is still not found, open a new fish session and run `uv --version`.
2. Clone the repository and enter it:
   ```fish
   git clone https://github.com/HomeHmnf/TownCountryAsset.git
   cd TownCountryAsset
   git fetch origin
   git switch --track origin/work/compiler-hardening
   ```
   If you already cloned the repo, run `git fetch origin; and git switch work/compiler-hardening; and git pull --ff-only origin work/compiler-hardening`.
3. Sync dependencies:
   ```fish
   uv sync --extra dev
   ```
   This creates the project virtual environment at `.venv/` using `uv.lock`. You do not need to activate it manually.
4. Run tests:
   ```fish
   uv run pytest -v
   ```
5. Download [Natural Earth Admin 0 – Countries (1:50m)](https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-0-countries/) and compile it:
   ```fish
   uv run python tools/compile_natural_earth.py --source /path/to/ne_50m_admin_0_countries.zip --output generated/town_country_asset
   ```
   Replace the example source path with the actual ZIP path.
6. Optionally generate static SVG files for all three detail profiles:
   ```fish
   uv run python tools/generate_country_svgs.py --data generated/town_country_asset --output generated/town_country_asset/svg
   ```
   Output is grouped as `svg/low/`, `svg/medium/`, and `svg/high/`, with one SVG per stable country ID. To generate only selected profiles, repeat `--profile`, for example `--profile low --profile medium`.
7. Copy `addons/town_country_asset` and the generated data into your Godot project. The runtime default data path is `res://generated/town_country_asset`.

## Human-readable data inspection workbook

After running the data pipeline to produce candidate metadata, build an Excel workbook that brings the identity registry, all compiled Natural Earth source attributes, ISO proposals, Persian localization candidates, flag mappings, and data-quality findings together for human inspection:

```fish
uv run --with openpyxl python tools/build_inspection_workbook.py
```

The default output is `reports/country-entity-inspection.xlsx`. It contains a master inventory and dedicated `Entity & Identity`, `ISO Review`, `Persian Review`, `Flag Review`, `Source Attributes`, and `Data Quality` worksheets. Each review sheet includes blank decision/evidence fields for humans to fill in. The workbook is generated locally and is not committed by the tool. It never writes decisions back to configuration, approves proposals, modifies the approved snapshot, or changes TownCountryGame. Run the pipeline first if you want the complete raw source attribute columns; without candidate `countries.json`, those columns will be reported as unavailable.

## Automatic online data refresh

Copy `.env.example` to `.env`, adjust the source URLs and local folders, then run the complete data-preparation pipeline:

```fish
cp .env.example .env
# Edit .env for your source URLs and preferred paths.
uv run python tools/run_data_pipeline.py
```

The CLI fetches the configured Natural Earth source, refreshes ISO and Persian-label review evidence when enabled, refreshes the configured MIT-licensed flag source with immutable commit provenance, compiles candidate metadata and geometry using the persistent identity registry, generates SVGs when enabled, audits the result, and compares it with the approved snapshot when available. When all flag mappings are reviewed, it generates one SVG flag per persistent `game_id` inside the candidate output. While mappings remain unreviewed, the pipeline records a `review_required` stage and does not guess or publish partial flags; unrelated candidate data refresh can continue. Other source, compilation, or asset-validation failures preserve the previous candidate and return a non-zero exit status. Run `uv run python tools/run_data_pipeline.py --help` or `--help-config` for configuration defaults.

All URLs and output/input directories are configurable through `.env` or process environment variables. Existing process environment variables take precedence. The local `.env` is ignored by Git; commit only changes to `.env.example`.
Flag source settings are `TCA_FLAG_SOURCE_URL`, `TCA_FLAG_SOURCE_REF`, `TCA_FLAG_SOURCE_DIR`, and `TCA_FLAG_REFRESH_ENABLED`. The explicit reviewed mapping lives in `config/country_flag_mapping.json`; the source refresh and generator are also available independently as `tools/refresh_flag_source.py` and `tools/generate_country_flags.py`. See the [flag CLI details](docs/cli-tool.md) and [implementation log](docs/implementation/data-refresh.md).

This workflow prepares data in **TownCountryAsset only**. It does not update TownCountryGame, promote candidate outputs over approved assets, regenerate the identity registry, or verify ISO proposals automatically. See [CLI documentation](docs/cli-tool.md) and the [implementation log](docs/implementation/data-refresh.md).

## Common development commands

```fish
uv run pytest -v
uv run python tools/audit_generated_assets.py --data generated/town_country_asset --source /path/to/ne_50m_admin_0_countries.zip
uv run python tools/compare_asset_snapshots.py --old generated/town_country_asset --new generated/town_country_asset_candidate --output reports/source-update-comparison.md
uv run python --version
uv run python -c 'import shapely, shapefile; print("Shapely", shapely.__version__); print("pyshp", shapefile.__version__)'
```

Update the dependency lockfile only after intentionally changing dependencies:

```fish
uv lock
uv sync --extra dev
```

## Runtime API

```gdscript
var assets := CountryAssets.new()
var country = assets.get_country("JPN")
var attrs = assets.get_all_attributes("JPN")
var asia = assets.get_countries_by_region("Asia")
var geometry = assets.get_geometry("JPN", "medium")
var svg = assets.get_country_svg("JPN", "medium")
```

Country lookup accepts a source-provided ISO alpha-3 candidate, stable internal ID, normalized country name, or configured aliases. The stable internal ID is based on the configured Natural Earth identifier and is not necessarily an ISO code; do not treat it as one. Geometry profiles are low/medium/high and are loaded lazily by the runtime. `get_country_svg()` produces a 512×512 fitted SVG string from the selected profile on demand. The optional offline SVG tool instead pre-generates SVG files, useful when static files are preferred or runtime path generation should be avoided.

SVG is a visual preview, not a cartographic projection suitable for area or distance analysis. Polygon holes use `fill-rule="evenodd"`. Antimeridian-crossing features may need a projection-aware renderer for ideal visual results.

## Validation and limitations

- Compiler tests validate source attributes, ISO/source-ID separation, missing and malformed ISO candidates, aliases, holes, stable IDs, missing/invalid/duplicate stable-ID rejection, source-schema/configuration fingerprints, region classification/audit output, deterministic outputs, manifest checksums, simplification validity, unsafe ZIP rejection, ambiguous shapefile rejection, and source archive checksums.
- `tools/audit_generated_assets.py` checks country ID uniqueness, ISO candidate syntax, geometry-key coverage across low/medium/high profiles, region-audit consistency, source-schema metadata, configuration fingerprints, generated-file hashes/sizes, and (when `--source` is provided) the local source ZIP checksum. It reports unmapped regions for review; it does not silently assign them.
- `tools/compare_asset_snapshots.py` compares an approved snapshot to a candidate, reporting added/removed IDs, possible rekeys inferred only from unique shared ISO candidates, changed source attributes/names/regions, per-feature geometry changes, source schema changes, source archive hashes, and configuration fingerprints. Its output is a review report, not an automatic approval.
- SVG tests validate well-formed XML, the 512×512 viewBox, polygon holes, multipart geometry, unsupported/empty geometry rejection, and output across low/medium/high profiles.
- A Godot runtime fixture test is provided at `tests/godot/test_country_assets.gd`. Run it from the consuming Godot project with `godot --headless --path . --script tests/godot/test_country_assets.gd`; the project must have the addon available and its `CountryAssets` global class registered.
- The current detail profiles are separate geometry files so the runtime can load only the desired profile. Avoid loading all profiles at startup on memory-constrained devices.
- Region classifications and aliases are configurable and independent of original source attributes. The current compiler uses Natural Earth `SUBREGION` to map North America (including Central America and the Caribbean) and South America. Any records outside the configured mappings are listed in `region_audit.unmapped_ids`; review these rather than assigning a region by guesswork.

## Build provenance and determinism

- The manifest contains SHA-256 and byte size for each generated JSON payload.
- When the source is a ZIP, the source archive SHA-256 is recorded in metadata and the manifest.
- Generated JSON and the manifest do not include build timestamps, so identical inputs/configuration produce byte-identical outputs.
- Before publishing an asset build, fill `source_version` and `retrieval_date` in `config/generation.json` with the release and date actually used. They are deliberately `null` by default rather than guessed.
- The compiler does not independently verify Natural Earth release identity; the source archive hash records exactly which ZIP was compiled.
- Preserve original source records and attribution; simplification is applied only to derived geometries, which are validated after simplification.
- No C#/.NET dependency is introduced, so Android export does not acquire additional .NET-specific requirements.

## Attribution

Natural Earth data is public domain; retain source attribution and provenance for reproducible builds. See [Natural Earth terms](https://www.naturalearthdata.com/about/terms-of-use/).
