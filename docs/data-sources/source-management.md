# Project-wide data source management

> Configuration authority and the project-wide configuration inventory are documented in [the configuration reference](../configuration-reference.md).

## Purpose and authority

`config/data_sources.json` is the single authoritative registry for external and local sources across the project. It covers WP1.5 providers and sources used by identity, geography, localization, flags, and asset refresh workflows. Domain contracts describe data requirements and refer to stable provider IDs; edition years belong in release identifiers and manifests, never in source IDs. Historical IDs are declared in `legacy_source_ids` and remain readable for existing snapshots; historical manifests and raw snapshot paths are not rewritten. The WP1.5 field contract (`config/wp1_5_data_sources.json`) therefore contains its approved 41 field definitions and references this registry.

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
uv run python -m tools.manage_sources show un_wpp
uv run python -m tools.manage_sources check
uv run python -m tools.manage_sources check --online
uv run python -m tools.manage_sources acquire --source un_wpp
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

The generic manager acquires explicitly configured HTTPS resources, including downloadable files and HTML pages. HTML page entries use the same immutable snapshot mechanism and may declare a reusable response contract (`validation.content_types` and `validation.required_text`). Acquisition checks the returned media type and required text before writing a manifest; a changed page is rejected and the untrusted snapshot is removed. The manifest records the validation contract used. This is a lightweight structural guard, not a substitute for a parser/schema validator: extracting table rows, checking row counts, uniqueness, identifier formats, and semantic consistency remains a separate provider-specific validation/import step.

API, Git, manual, subscription, and per-country evidence sources are centrally registered and their endpoint defaults are resolved from this registry, while their existing protocol-specific refreshers retain their specialized validation. Dedicated adapters can be added without changing the registry authority. The shared HTML table extractor is in `tools/sources/html_tables.py`; providers select tables by required headings and receive normalized row dictionaries. Provider adapters add domain-specific identifier, uniqueness, coverage, and semantic checks. The UNSD M49 adapter (`tools/sources/m49.py`) retains all source rows and region columns, while excluding rows without both ISO alpha codes from ISO candidate proposals. Partial or duplicate codes fail validation.

Run the official M49 identity-review refresh with `uv run python -m tools.refresh_m49_iso_review`. It stores the original HTML, a full normalized JSON table retaining M49 codes and regional hierarchy, a normalized ISO candidate CSV, parser/version metadata, checksums, and rows lacking ISO codes; then generates the existing review-only proposal report. It does not change the identity registry or approve assignments. The third-party CSV workflow remains available separately. The M49 page is a rolling reference rather than a versioned file release; to intentionally recapture it, assign a new release identifier to its download entry in `config/data_sources.json` before acquisition. Existing snapshots are never overwritten.

## Pipeline integration

The data pipeline and the existing flag, ISO-reference, and Persian-localization refresh tools now resolve their default source endpoints from the central registry. Existing `.env`/process-environment overrides remain supported. The WP1.5 source contract no longer owns a second source catalogue: its 41 fields refer to source IDs in `config/data_sources.json`.

The WP1.5 compatibility acquisition function delegates its default project-root downloads to the shared immutable acquisition service. Explicit custom roots/configurations remain available for isolated tests and compatibility use.

## Safety and governance

Acquisition does not parse/import data into SQLite, alter country identity, approve review proposals, or publish game assets. Those remain separate explicit pipeline steps. A successful HTTP response is not dataset validation; provider-specific format, schema, coverage, identity crosswalk, and release checks are required before import.

License status is informational and does not block acquisition. Record whether terms are open, attribution-required, non-commercial, require commercial authorization, restrict redistribution, are proprietary/subscription, or remain unclear. Do not describe restricted or unverified material as open. License reporting does not grant rights; users must comply with source terms.

Natural Earth is registered for geography/cartography only and is not an accepted source for WP1.5 statistics or classifications. Raw snapshots remain outside Git; manifests and source metadata are versioned. Review-only ISO, localization, and flag proposal workflows retain their existing human-review and approval safeguards.


## Shared database reports

Database reports use one standard directory and artifact contract:

```text
reports/
└── database/
    └── <database_id>/
        └── <domain>/
            └── <report_id>/
                ├── summary.md
                ├── records.csv
                ├── unmatched_registry.csv
                ├── unmatched_reference.csv
                └── provenance.json
```

The provider-neutral writer is `tools/database/reporting.py`; report-specific analysis belongs in reusable domain components such as `tools/database/identity_reconciliation.py`. Database ID, domain and report ID are validated path segments. Markdown is the human-readable summary, CSV files contain record-level data and unmatched rows, and JSON records source/parser versions, checksums, field mappings, matching policy and read-only status. The writer accepts domain-specific CSV column definitions so statistics, provenance and completeness reports can reuse the same artifact contract. New database report types should use this writer rather than inventing another directory or artifact layout.

The identity reconciliation engine compares every registry identity with every supplied reference row. It matches only normalized English names and explicit, maintained name variants. It does not use source IDs or ISO codes to establish identity, does not perform fuzzy matching, and marks duplicate or many-to-one name matches as ambiguous. Alpha-2 and alpha-3 are compared independently after a unique name match. Source-ID/alpha-3 coincidence is reported separately and is not treated as an ISO conflict. The component is read-only and does not approve or verify identity assignments.

The M49 refresh now writes the full reconciliation bundle to `reports/database/town_country_asset/identity/m49-current/`, alongside the existing ISO proposal report at `reports/iso-assignment-proposals.md` (kept at its existing path for importer compatibility).

### Terminal output modes

Report-producing database commands share the same output policy:

- Default: write all report artifacts and print a concise terminal summary with counts and report location.
- `--quiet`: write the same artifacts but suppress the successful summary. Errors and non-zero exit status are not suppressed.
- `--verbose`: write the same artifacts and print expanded classification counts and record-level reconciliation results.

For example, the M49 refresh supports:

```fish
uv run python -m tools.refresh_m49_iso_review
uv run python -m tools.refresh_m49_iso_review --quiet
uv run python -m tools.refresh_m49_iso_review --verbose
```

Quiet mode changes only terminal presentation; it never disables report generation or validation.


## Release discovery and selection

Release discovery is declared per source in `release_discovery` within `config/data_sources.json`. It is deliberately separate from acquisition: a provider page or API may identify a candidate release without providing a downloadable snapshot, and a reachable download URL does not prove that its contents are current or valid.

Supported discovery modes are:

- `manual_review`: check the authoritative provider publication or release page manually.
- `website_page`: inspect a provider page for a publication/update and record a release label only when supported by evidence.
- `rolling_url`: the URL can change in place; a changed checksum is a candidate update, not proof of a new semantic edition.
- `provider_metadata`: use a documented provider API/feed that exposes release identifiers or publication dates. A mode declaration does not mean an adapter is implemented.
- `git_ref`: record an immutable tag or commit, not a moving branch name.

Every source currently records `automation_status`; `not_implemented` means discovery remains manual and no automated latest-release claim is made. The `latest_available`, `latest_validated`, and `latest_applied` fields remain null until supported release records are produced. Current declarations are metadata contracts, not a claim that all sources are automatically monitored.

Each configured download also declares a `release_kind`:

- `edition_or_snapshot`: a named provider edition or immutable source snapshot.
- `current_reference`: a current/rolling reference page or dataset.
- `rolling`: a mutable endpoint without a stable edition identifier.
- `supplement`: a scoped update supplement that must be applied only to its stated scope.

The global `release_management` section defines the state meanings and release-record contract. Release state records are intended for `reports/sources/releases/<source-id>.json`; they distinguish discovery, acquisition, validation and application timestamps and retain release history. The registry itself remains source configuration, not a mutable ledger of changing release events.

**Promotion rules:** discovery does not imply validation; acquisition does not imply validation; validation does not imply application. Only a successfully acquired snapshot that passes its registered source/data contract can become `latest_validated`. Applying it to the canonical database is a separate explicit operation. Older snapshots and manifests remain immutable.

## Project-wide refresh command

Run the generic refresh from the repository root:

```fish
uv run python -m tools.refresh_sources
uv run python -m tools.refresh_sources --source un_wpp
uv run python -m tools.refresh_sources --dry-run
```

The refresh runner uses the central registry and shared immutable acquisition service. It skips snapshots whose raw file and manifest pass checksum/identity checks, reports invalid snapshots without overwriting them, and attempts missing configured HTTPS downloads. A batch continues after an individual acquisition failure. Use repeated `--source` arguments to limit a run to selected registered sources.

An acquisition result is labelled `acquired_pending_source_validation`: it means the download and its generic registered response checks succeeded, not that provider-specific data semantics, coverage, identifiers, or release suitability have been validated. Existing valid snapshots are reported as unchanged. Invalid snapshots are retained for investigation and are never silently replaced. A dry run reports intended acquisitions without making network requests.

The command writes timestamped JSON and Markdown reports below `reports/sources/refreshes/`. Sources without configured generic HTTPS downloads are explicitly reported for manual review or a future protocol-specific adapter. A discovery mode declaration alone is not an implemented discovery adapter. This first generic runner does not discover new provider editions, does not promote `latest_available` or `latest_validated`, and does not update the release-state ledger. In particular, it does not treat a rolling URL's existing snapshot as proof that the provider has not published an update. Provider-specific discovery and semantic validators must be implemented and tested before a source can be automatically promoted.

The refresh command never imports into SQLite, changes approved data, or approves review proposals. Acquisition, provider validation, policy-based selection, and canonical application remain separate steps.

