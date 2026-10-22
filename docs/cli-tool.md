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
| `TCA_FLAG_SOURCE_URL` | Flag source repository URL (initial source: `lipis/flag-icons`, MIT licensed) |
| `TCA_FLAG_SOURCE_REF` | Configured source ref; refresh tooling must record the resolved immutable commit |
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
| `TCA_FLAG_REFRESH_ENABLED` | Enable the planned flag-source refresh stage |
| `TCA_HTTP_TIMEOUT_SECONDS` | Network timeout per download |

Paths may be absolute or relative to the repository root. Boolean values accept `true/false`, `1/0`, and `yes/no`.

## Usage

The CLI builds into a temporary sibling directory. Compilation, SVG generation, asset audits, identity-registry review, and comparison must all pass before the validated directory replaces `TCA_GAME_DATA_OUTPUT_DIR`. On a failed build or audit, the previous candidate directory is preserved and temporary output is removed. This publication step never changes `TCA_APPROVED_DATA_DIR`.

The target interface is:

```fish
uv run python tools/run_data_pipeline.py
```

Use `--help` to inspect supported CLI options. The command should be safe to rerun, report each stage, preserve timestamped upstream evidence, and return non-zero if a required stage fails. It must not silently promote candidate output over the approved snapshot.

## Flag source refresh (staged rollout)

The standalone flag-source refresh command is available while the flag feature is being built out:

```fish
uv run python tools/refresh_flag_source.py
```

It reads `TCA_FLAG_SOURCE_URL`, `TCA_FLAG_SOURCE_REF`, `TCA_FLAG_SOURCE_DIR`, and `TCA_HTTP_TIMEOUT_SECONDS` from `.env` (process environment overrides file values). Optional flags `--source-url`, `--source-ref`, `--output-dir`, `--timeout`, and `--env-file` override those values for one invocation.

The command accepts only an HTTPS GitHub repository URL, resolves the configured ref to a full commit SHA using GitHub's API, then downloads the archive for that immutable commit. It validates the ZIP structure, rejects traversal paths and symlinks, requires SVGs under a `flags/` directory and an MIT license file, and records archive/license SHA-256 hashes, sizes, retrieval time, configured ref, resolved commit, and source URL. Timestamped snapshots are not overwritten when the upstream commit changes; the cache filenames are commit-keyed. It does not extract files or assign flags.

This stage refreshes and records upstream source evidence. It does not assign flags and is not yet part of the main data-refresh pipeline.

### Generate and audit reviewed flag assets (Stage 8c)

After the source archive is refreshed and the mapping contains reviewed decisions, run:

```fish
uv run python tools/generate_country_flags.py
```

The command reads the persistent identity registry, `TCA_FLAG_MAPPING`, and the commit-keyed archive in `TCA_FLAG_SOURCE_DIR`. It verifies the archive checksum against provenance, reads the source's `flags/4x3/<code>.svg` files, validates each selected SVG, and writes output as `<game_id>.svg` with a manifest containing per-file hashes and source revision metadata. The output directory is replaced only after complete one-to-one coverage validates; failed audits preserve existing output. A Markdown audit is written to `TCA_FLAG_REPORT`.

Only mapping records with `status: "reviewed"` and a valid lowercase two-letter source code are eligible. Missing mappings, duplicate IDs/codes, unknown IDs, missing source files, and malformed SVGs fail closed. The current mapping intentionally has null codes and `unreviewed` statuses, so the audit is expected to fail until mapping decisions are reviewed. It does not guess flags, use generic fallbacks, or modify the identity registry. This generator is not yet wired into the main pipeline; that is Stage 8d.

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
