# Project-wide data source management

## Purpose and authority

`config/data_sources.json` is the single authoritative registry for external and local sources across the project. It covers WP1.5 providers and sources used by identity, geography, localization, flags, and asset refresh workflows. Domain contracts describe data requirements and refer to stable source IDs; they do not duplicate source definitions. The WP1.5 field contract (`config/wp1_5_data_sources.json`) therefore contains its approved 41 field definitions and references this registry.

Each source record can hold its homepage, domain, acquisition mode, direct download definitions, formats, releases, applicable WP1.5 field IDs, terms, attribution, license classification, and source-specific settings. Manual, API, Git, subscription, and per-record evidence sources remain registered even when no generic file download is configured.

## Storage conventions

- Raw snapshots: `raw_data/sources/<source-id>/<download-id>/<release>/<filename>` (local only; never commit raw source bytes).
- Provenance manifests: `data_manifests/sources/<source-id>/<download-id>/<release>.json` (tracked).
- Operational reports: `reports/sources/`.
- Registry and domain contracts: tracked in Git.

Snapshots are immutable. The manager refuses to overwrite an existing raw file or manifest. A new upstream release or intentional recapture uses a new release identifier. Manifests record original/final URL, retrieval timestamp, source/download IDs, release, terms/license metadata, content type, byte count, and SHA-256.

## Commands

Run from the repository root:

```sh
uv run python -m tools.manage_sources list
uv run python -m tools.manage_sources show un_wpp_2024
uv run python -m tools.manage_sources check
uv run python -m tools.manage_sources check --online
uv run python -m tools.manage_sources acquire --source un_wpp_2024
uv run python -m tools.manage_sources acquire --all
uv run python -m tools.manage_sources status
uv run python -m tools.manage_sources licenses
```

- `list` lists registered sources and acquisition modes.
- `show` prints one source record.
- `check` verifies local snapshot/manifest presence, identity, size, and checksum.
- `check --online` additionally probes configured HTTPS download endpoints. Endpoint reachability is not proof that a dataset is valid or current.
- `acquire --source ID` captures all configured direct downloads for one source; `acquire --all` attempts every configured direct download. Batch runs continue after individual failures and return non-zero if any item fails.
- `status` reports local snapshot status.
- `licenses` reports recorded license classifications and terms links. The current tracked register is `reports/sources/source-licenses.md`; update it when source metadata changes.

The generic manager acquires explicitly configured HTTPS resources, including downloadable files and HTML pages. HTML page entries use the same immutable snapshot mechanism and may declare a reusable response contract (`validation.content_types` and `validation.required_text`). Acquisition checks the returned media type and required text before writing a manifest; a changed page is rejected and the untrusted snapshot is removed. The manifest records the validation contract used. This is a lightweight structural guard, not a substitute for a parser/schema validator: extracting table rows, checking row counts, uniqueness, identifier formats, and semantic consistency remains a separate provider-specific validation/import step.\n\nAPI, Git, manual, subscription, and per-country evidence sources are centrally registered and their endpoint defaults are resolved from this registry, while their existing protocol-specific refreshers retain their specialized validation. Dedicated adapters can be added without changing the registry authority. The shared HTML table extractor is in `tools/sources/html_tables.py`; providers select tables by required headings and receive normalized row dictionaries. Provider adapters add domain-specific identifier, uniqueness, coverage, and semantic checks. The UNSD M49 adapter (`tools/sources/m49.py`) retains all source rows and region columns, while excluding rows without both ISO alpha codes from ISO candidate proposals. Partial or duplicate codes fail validation.\n\nRun the official M49 identity-review refresh with `uv run python -m tools.refresh_m49_iso_review`. It stores the original HTML, normalized ISO candidate CSV, parser/version metadata, checksum, and rows lacking ISO codes; then generates the existing review-only proposal report. It does not change the identity registry or approve assignments. The third-party CSV workflow remains available separately.

## Pipeline integration

The data pipeline and the existing flag, ISO-reference, and Persian-localization refresh tools now resolve their default source endpoints from the central registry. Existing `.env`/process-environment overrides remain supported. The WP1.5 source contract no longer owns a second source catalogue: its 41 fields refer to source IDs in `config/data_sources.json`.

The WP1.5 compatibility acquisition function delegates its default project-root downloads to the shared immutable acquisition service. Explicit custom roots/configurations remain available for isolated tests and compatibility use.

## Safety and governance

Acquisition does not parse/import data into SQLite, alter country identity, approve review proposals, or publish game assets. Those remain separate explicit pipeline steps. A successful HTTP response is not dataset validation; provider-specific format, schema, coverage, identity crosswalk, and release checks are required before import.

License status is informational and does not block acquisition. Record whether terms are open, attribution-required, non-commercial, require commercial authorization, restrict redistribution, are proprietary/subscription, or remain unclear. Do not describe restricted or unverified material as open. License reporting does not grant rights; users must comply with source terms.

Natural Earth is registered for geography/cartography only and is not an accepted source for WP1.5 statistics or classifications. Raw snapshots remain outside Git; manifests and source metadata are versioned. Review-only ISO, localization, and flag proposal workflows retain their existing human-review and approval safeguards.
