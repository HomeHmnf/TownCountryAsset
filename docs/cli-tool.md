# Data refresh CLI

## Purpose

The data-refresh CLI is the entry point for preparing game-ready country assets from online sources. It belongs to **TownCountryAsset**; it does not update or commit files in the separate TownCountryGame repository.

The intended one-command workflow fetches the configured source datasets, preserves source evidence and checksums, validates the inputs, compiles country metadata and geometry, optionally generates SVGs, audits outputs, compares a candidate with the last approved asset snapshot, and writes a human-readable run summary. Failures must produce a failure report and a non-zero exit status.

## Configuration

Copy `.env.example` to `.env` and customize it. The CLI reads `.env` without requiring a third-party dotenv package. Existing process environment variables take precedence over values in `.env`. Never commit secrets or a local `.env`.

| Variable | Purpose |
|---|---|
| `TCA_NATURAL_EARTH_URL` | URL for the Natural Earth Admin 0 Countries archive |
| `TCA_ISO_REFERENCE_URL` | URL for the ISO 3166-1 discovery/reference CSV |
| `TCA_PERSIAN_LABEL_SOURCE_URL` | HTTPS endpoint queried for current Wikidata Persian (`fa`) labels; labels remain candidates |
| `TCA_FETCHED_DATA_DIR` | Local directory for fetched source archives |
| `TCA_ISO_DATA_DIR` | Raw snapshots and normalized ISO reference |
| `TCA_PERSIAN_DATA_DIR` | Timestamped raw Wikidata responses, candidate snapshots, and provenance |
| `TCA_PERSIAN_LOCALIZATION_REPORT` | Latest Persian localization review worksheet |
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
| `TCA_HTTP_TIMEOUT_SECONDS` | Network timeout per download |

Paths may be absolute or relative to the repository root. Boolean values accept `true/false`, `1/0`, and `yes/no`.

## Usage

The CLI builds into a temporary sibling directory. Compilation, SVG generation, asset audits, identity-registry review, and comparison must all pass before the validated directory replaces `TCA_GAME_DATA_OUTPUT_DIR`. On a failed build or audit, the previous candidate directory is preserved and temporary output is removed. This publication step never changes `TCA_APPROVED_DATA_DIR`.

The target interface is:

```fish
uv run python tools/run_data_pipeline.py
```

Use `--help` to inspect supported CLI options. The command should be safe to rerun, report each stage, preserve timestamped upstream evidence, and return non-zero if a required stage fails. It must not silently promote candidate output over the approved snapshot.

## Snapshot comparison details

The comparison report distinguishes a real difference from unavailable metadata. If either snapshot lacks source-schema or build-input metadata (as can happen with older approved snapshots), that comparison is marked “not comparable” rather than “changed.” During a pipeline run, the comparison is performed against the isolated staging directory, while the report displays the configured candidate output path.

## Outputs and reports

- **Fetched source data:** immutable/timestamped source downloads and provenance.
- **Candidate game data:** metadata, geometry profiles, manifest and optional SVGs are built in an isolated temporary directory, then published to `TCA_GAME_DATA_OUTPUT_DIR` only after successful validation. A failed run preserves the prior candidate.
- **ISO review:** proposals only; a name match is never approval.
- **Persian localization review:** each pipeline run queries the configured live endpoint, preserves a timestamped raw response and SHA-256 provenance, and refreshes `reports/persian-localization-proposals.md`. Candidate snapshots are timestamped and immutable. Features are mapped to Wikidata only through Natural Earth's explicit `WIKIDATAID` attribute; no name-based or fuzzy entity matching is used. Missing QIDs and missing Persian labels are reported for review.
- **Run summary:** one Markdown report and one machine-readable JSON report per invocation.
- **Comparison:** added/removed identities, possible rekeys, metadata changes and geometry changes versus the approved snapshot.

## Safety boundaries

- The asset project prepares data; it does not update the game repository.
- Do not overwrite the identity registry automatically or regenerate stable IDs from source order, names, or ISO codes.
- Do not automatically approve ISO assignments or Persian labels. Persian labels are source candidates, not proof of an official or preferred translation.
- Do not replace approved data based only on successful compilation. Keep generated candidate data separate until the owner reviews the report.
- Do not claim an upstream version unless it was obtained from source metadata or release information; always record retrieval time and SHA-256.
- When a source changes schema or fails validation, stop the affected stage, write a failure summary, and preserve the last known-good approved output.

The default Natural Earth archive URL uses the Natural Earth S3 distribution endpoint. The older website download URL returned HTTP 500 during a local end-to-end run; existing `.env` files override defaults, so update `TCA_NATURAL_EARTH_URL` in `.env` when adopting a changed default.

The CLI implementation and each completed implementation phase are tracked in `docs/implementation/data-refresh.md`.
