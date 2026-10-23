# Data refresh CLI

## Purpose

The data-refresh CLI is the entry point for preparing game-ready country assets from online sources. It belongs to **TownCountryAsset**; it does not update or commit files in the separate TownCountryGame repository.

The one-command workflow fetches configured source datasets, preserves source evidence and checksums, refreshes flag-source provenance when enabled, compiles country metadata and geometry, attempts reviewed flag generation, optionally generates country SVGs, audits outputs, compares a candidate with the approved snapshot, and writes a run summary. Required source/compile/asset failures produce a failure report and non-zero exit status. Incomplete flag review is recorded as `review_required` and does not invent mappings.

## Configuration

Copy `.env.example` to `.env` and customize it. The CLI reads `.env` without requiring a third-party dotenv package. Existing process environment variables take precedence over values in `.env`. Never commit secrets or a local `.env`.

| Variable | Purpose |
|---|---|
| `TCA_NATURAL_EARTH_URL` | URL for the Natural Earth Admin 0 Countries archive |
| `TCA_ISO_REFERENCE_URL` | URL for the ISO 3166-1 discovery/reference CSV |
| `TCA_PERSIAN_LABEL_SOURCE_URL` | HTTPS endpoint queried for current Wikidata Persian (`fa`) labels; labels remain candidates |
| `TCA_FLAG_SOURCE_URL` | Flag source repository URL (initial source: `lipis/flag-icons`, MIT licensed) |
| `TCA_FLAG_SOURCE_REF` | Configured source ref; refresh tooling records the resolved immutable commit |
| `TCA_FETCHED_DATA_DIR` | Local directory for fetched source archives |
| `TCA_ISO_DATA_DIR` | Raw snapshots and normalized ISO reference |
| `TCA_PERSIAN_DATA_DIR` | Timestamped raw Wikidata responses, candidate snapshots, and provenance |
| `TCA_PERSIAN_LOCALIZATION_REPORT` | Latest Persian localization review worksheet |
| `TCA_FLAG_SOURCE_DIR` | Local cache for fetched flag source files and provenance |
| `TCA_FLAG_ASSET_OUTPUT_DIR` | Candidate flag asset output directory, keyed by persistent `game_id` |
| `TCA_FLAG_MAPPING` | Explicit reviewed mapping from persistent IDs to source flag identifiers |
| `TCA_FLAG_REPORT` | Flag mapping and asset coverage review report |
| `TCA_GAME_DATA_OUTPUT_DIR` | Candidate game-data output directory |
| `TCA_APPROVED_DATA_DIR` | Existing approved snapshot used only for comparison |
| `TCA_REPORT_DIR` | Run summaries and comparison reports |
| `TCA_GENERATION_CONFIG` | Generation settings JSON |
| `TCA_REGIONS_CONFIG` | Region mapping JSON |
| `TCA_IDENTITY_REGISTRY` | Persistent identity registry; the pipeline must never bootstrap or overwrite it |
| `TCA_GENERATE_SVGS` | Generate static SVG files after successful compilation |
| `TCA_COMPARE_WITH_APPROVED` | Compare candidate output with approved output if present |
| `TCA_RUN_ISO_REVIEW` | Refresh the ISO proposal report without approving assignments |
| `TCA_RUN_PERSIAN_LOCALIZATION` | Fetch current Wikidata Persian labels and refresh the review worksheet on each pipeline run |
| `TCA_FLAG_REFRESH_ENABLED` | Refresh the configured flag source and record immutable provenance during the pipeline run |
| `TCA_HTTP_TIMEOUT_SECONDS` | Network timeout per download |

Paths may be absolute or relative to the repository root. Boolean values accept `true/false`, `1/0`, and `yes/no`.

## Usage

The CLI builds into a temporary sibling directory. Compilation, country-SVG generation when enabled, asset audits, identity-registry audit, and comparison must pass before the validated directory replaces `TCA_GAME_DATA_OUTPUT_DIR`. Flag generation runs against the isolated candidate directory. If its only issues are unreviewed or missing mapping decisions, the stage is marked `review_required`, no partial flags are written, and the non-flag candidate refresh may continue. Source integrity errors, malformed SVGs, duplicate/unknown mappings, or other asset errors fail the run. On a failed required build or audit, the previous candidate directory is preserved and temporary output is removed. This publication step never changes `TCA_APPROVED_DATA_DIR`.

The target interface is:

```fish
uv run python tools/run_data_pipeline.py
```

Use `--help` to inspect supported CLI options. The command should be safe to rerun, report each stage, preserve timestamped upstream evidence, and return non-zero if a required stage fails. It must not silently promote candidate output over the approved snapshot.

## Manually maintained ISO reference snapshot

The manual reference files are stored under `data/reference/iso/`:

- `iso-3166-1-2026-10.ods` — editable Calc workbook for inspection and monthly maintenance.
- `iso-3166-1-2026-10.tsv` — intended machine-readable tab-separated export.

The CLI validates the reference at the start of every run. It prefers a well-formed TSV; if the TSV is missing or malformed (including spreadsheet XML saved with a `.tsv` extension), it falls back to parsing the ODS workbook directly. The selected source, validated row count, and fallback/quality warnings are recorded in the run summary. If neither file can be parsed, the CLI warns and continues the other pipeline stages without treating the manual reference as current.

The committed TSV was detected as Excel XML rather than tab-separated text, so automation should select the ODS workbook. The ODS reader preserves leading zeros in numeric codes and warns about missing numeric values; the current workbook appears to omit Zambia's numeric code. Correct the workbook and re-export a true TSV from Calc with Tab as the field delimiter when convenient. Do not use the workbook or this manually assembled snapshot as proof of an official ISO-hosted export. This manual snapshot is a comparison input only: it does not verify, approve, or write ISO assignments to `config/country_identity_registry.json`. The existing online ISO proposal refresh remains a separate workflow.

## Flag source refresh (staged rollout)

The standalone flag-source refresh command is available while the flag feature is being built out:

```fish
uv run python tools/refresh_flag_source.py
```

It reads `TCA_FLAG_SOURCE_URL`, `TCA_FLAG_SOURCE_REF`, `TCA_FLAG_SOURCE_DIR`, and `TCA_HTTP_TIMEOUT_SECONDS` from `.env` (process environment overrides file values). Optional flags `--source-url`, `--source-ref`, `--output-dir`, `--timeout`, and `--env-file` override those values for one invocation.

The command accepts only an HTTPS GitHub repository URL, resolves the configured ref to a full commit SHA using GitHub's API, then downloads the archive for that immutable commit. It validates the ZIP structure, rejects traversal paths and symlinks, requires SVGs under a `flags/` directory and an MIT license file, and records archive/license SHA-256 hashes, sizes, retrieval time, configured ref, resolved commit, and source URL. Timestamped snapshots are not overwritten when the upstream commit changes; the cache filenames are commit-keyed. It does not extract files or assign flags.

The main data-refresh pipeline runs this source refresh when `TCA_FLAG_REFRESH_ENABLED=true`. A failed enabled refresh fails the pipeline; disable it only when intentionally using an already-cached source archive. The pipeline subsequently runs the generator against its isolated candidate directory.

### Generate and audit reviewed flag assets (Stage 8c)

After the source archive is refreshed and the mapping contains reviewed decisions, run:

```fish
uv run python tools/generate_country_flags.py
```

The command reads the persistent identity registry, `TCA_FLAG_MAPPING`, and the commit-keyed archive in `TCA_FLAG_SOURCE_DIR`. It verifies the archive checksum against provenance, reads the source's `flags/4x3/<code>.svg` files, validates each selected SVG, and writes output as `<game_id>.svg` with a manifest containing per-file hashes and source revision metadata. The output directory is replaced only after complete one-to-one coverage validates; failed audits preserve existing output. A Markdown audit is written to `TCA_FLAG_REPORT`.

Only mapping records with `status: "reviewed"` and a valid lowercase two-letter source code are eligible. Missing mappings, duplicate IDs/codes, unknown IDs, missing source files, and malformed SVGs fail closed. The current mapping intentionally has null codes and `unreviewed` statuses, so the audit is expected to fail until mapping decisions are reviewed. It does not guess flags, use generic fallbacks, or modify the identity registry. The main pipeline now runs this generator after candidate compilation. If all records are reviewed and valid, the flags are published inside the candidate as `flags/<game_id>.svg`. If the report contains only unreviewed/missing mapping decisions, the pipeline marks the stage `review_required` and continues the country-data refresh without flags; no partial set is published. All other generator errors fail the pipeline. This temporary review gate lets the existing data refresh remain usable while the explicit mapping is reviewed; flag completeness is not considered achieved until the audit reports PASS for every registry ID.

## Snapshot comparison details

The comparison report distinguishes a real difference from unavailable metadata. If either snapshot lacks source-schema or build-input metadata (as can happen with older approved snapshots), that comparison is marked “not comparable” rather than “changed.” During a pipeline run, the comparison is performed against the isolated staging directory, while the report displays the configured candidate output path.

## Outputs and reports

- **Fetched source data:** immutable/timestamped source downloads and provenance.
- **Candidate game data:** metadata, geometry profiles, manifest and optional SVGs are built in an isolated temporary directory, then published to `TCA_GAME_DATA_OUTPUT_DIR` only after successful validation. A failed run preserves the prior candidate.
- **ISO review:** proposals only; a name match is never approval.
- **Persian localization review:** each pipeline run queries the configured live endpoint, preserves a timestamped raw response and SHA-256 provenance, and refreshes `reports/persian-localization-proposals.md`. Candidate snapshots are timestamped and immutable. Features are mapped to Wikidata only through Natural Earth's explicit `WIKIDATAID` attribute; no name-based or fuzzy entity matching is used. Missing QIDs and missing Persian labels are reported for review.
- **Run summary:** one Markdown report and one machine-readable JSON report per invocation.
- **Comparison:** added/removed identities, possible rekeys, metadata changes and geometry changes versus the approved snapshot.

## Human-readable inspection workbook

Build a filterable Excel workbook from the persistent identity registry, latest compiled candidate metadata, ISO proposal report, latest Persian candidate snapshot, and explicit flag mapping:

```bash
uv run --with openpyxl python tools/build_inspection_workbook.py
```

The default output is `reports/country-entity-inspection.xlsx`. Sheets cover the master inventory, entity/identity records, ISO review, Persian review, flag review, all available Natural Earth source attributes, and data-quality/review findings. Decision, reviewer, date, and evidence fields are blank for human completion. The workbook is read-only with respect to source data and never approves or writes back review decisions. Run the data pipeline first for complete compiled source attributes.

## Safety boundaries

- The asset project prepares data; it does not update the game repository.
- Do not overwrite the identity registry automatically or regenerate stable IDs from source order, names, or ISO codes.
- Do not automatically approve ISO assignments or Persian labels. Persian labels are source candidates, not proof of an official or preferred translation.
- Do not replace approved data based only on successful compilation. Keep generated candidate data separate until the owner reviews the report.
- Do not claim an upstream version unless it was obtained from source metadata or release information; always record retrieval time and SHA-256.
- When a source changes schema or fails validation, stop the affected stage, write a failure summary, and preserve the last known-good approved output.

The default Natural Earth archive URL uses the Natural Earth S3 distribution endpoint. The older website download URL returned HTTP 500 during a local end-to-end run; existing `.env` files override defaults, so update `TCA_NATURAL_EARTH_URL` in `.env` when adopting a changed default.

The CLI implementation and each completed implementation phase are tracked in `docs/implementation/data-refresh.md`.


## Human-readable inspection workbook

Run:

```bash
uv run python tools/export_country_inspection_workbook.py
```

By default this writes `reports/country-data-inspection.xlsx`. Override inputs or output when needed:

```bash
uv run python tools/export_country_inspection_workbook.py \
  --registry config/country_identity_registry.json \
  --countries generated/town_country_asset_candidate/countries.json \
  --iso-report reports/iso-assignment-proposals.md \
  --persian-report reports/persian-localization-proposals.md \
  --flag-mapping config/country_flag_mapping.json \
  --output reports/country-data-inspection.xlsx
```

Sheets include a read-me page, master inventory, ISO review, entity review, Persian review, flag review, data-quality findings, and all compiled source attributes. Tables are filterable and the headers are frozen. The exporter joins records by persistent `game_id`, not row order or display name. Candidate fields are shown as candidates, and review decision columns are left for human inspection. Exporting does not modify any input, approve proposals, or apply workbook edits to project data.

The exporter reads `generated/town_country_asset_candidate/countries.json` so it can include the current compiled source attributes. Run the data pipeline first if this file is absent or stale. The Python project dependency `openpyxl` is used to write the XLSX workbook.
