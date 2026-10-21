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
| `TCA_FETCHED_DATA_DIR` | Local directory for fetched source archives |
| `TCA_ISO_DATA_DIR` | Raw snapshots and normalized ISO reference |
| `TCA_GAME_DATA_OUTPUT_DIR` | Candidate game-data output directory |
| `TCA_APPROVED_DATA_DIR` | Existing approved snapshot used only for comparison |
| `TCA_REPORT_DIR` | Run summaries and comparison reports |
| `TCA_GENERATION_CONFIG` | Generation settings JSON |
| `TCA_REGIONS_CONFIG` | Region mapping JSON |
| `TCA_IDENTITY_REGISTRY` | Persistent identity registry; the pipeline must never bootstrap or overwrite it |
| `TCA_GENERATE_SVGS` | Generate static SVG files after successful compilation |
| `TCA_COMPARE_WITH_APPROVED` | Compare candidate output with approved output if present |
| `TCA_RUN_ISO_REVIEW` | Refresh the ISO proposal report without approving assignments |
| `TCA_HTTP_TIMEOUT_SECONDS` | Network timeout per download |

Paths may be absolute or relative to the repository root. Boolean values accept `true/false`, `1/0`, and `yes/no`.

## Usage

The target interface is:

```fish
uv run python tools/run_data_pipeline.py
```

Use `--help` to inspect supported CLI options. The command should be safe to rerun, report each stage, preserve timestamped upstream evidence, and return non-zero if a required stage fails. It must not silently promote candidate output over the approved snapshot.

## Outputs and reports

- **Fetched source data:** immutable/timestamped source downloads and provenance.
- **Candidate game data:** metadata, geometry profiles, manifest and optional SVGs in `TCA_GAME_DATA_OUTPUT_DIR`.
- **ISO review:** proposals only; a name match is never approval.
- **Run summary:** one Markdown report and one machine-readable JSON report per invocation.
- **Comparison:** added/removed identities, possible rekeys, metadata changes and geometry changes versus the approved snapshot.

## Safety boundaries

- The asset project prepares data; it does not update the game repository.
- Do not overwrite the identity registry automatically or regenerate stable IDs from source order, names, or ISO codes.
- Do not automatically approve ISO assignments.
- Do not replace approved data based only on successful compilation. Keep generated candidate data separate until the owner reviews the report.
- Do not claim an upstream version unless it was obtained from source metadata or release information; always record retrieval time and SHA-256.
- When a source changes schema or fails validation, stop the affected stage, write a failure summary, and preserve the last known-good approved output.

The CLI implementation and each completed implementation phase are tracked in `docs/implementation/data-refresh.md`.
