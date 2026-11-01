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

```fish
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

Every source records `automation_status`. Content-fingerprint discovery is implemented for `natural_earth_admin0` (`rolling_url`), `iso_reference_mirror` (`rolling_url`), and `un_m49` (`website_page`). GitHub default-branch commit discovery is implemented for `lipis_flag_icons` (`git_ref`) through the GitHub REST API. The Git adapter records the immutable commit SHA, provider commit timestamp, and UTC `fetched_at` timestamp as a candidate release; `fetched_at` records when the refresh process retrieved the provider metadata and remains stable for that release across later checks. It does not acquire the repository archive. The remaining sources stay `not_implemented` and require manual review or a future protocol-specific adapter. In particular, `wikidata_sparql` remains `manual_review`: the live Wikidata Query Service is continuously updated and does not expose a stable versioned release identifier for query results. Wikidata's weekly JSON dumps have dated releases, but those are separate snapshot products; their release dates must not be presented as versions of live SPARQL results. A dump-based adapter would require a separately registered acquisition contract. The three fingerprint adapters GET the configured resource, verify that redirects remain HTTPS, and compute a SHA-256 fingerprint. A changed fingerprint becomes a content-addressed candidate release in `reports/sources/releases/<source-id>.json`. The release ledger retains history and updates `latest_available` only. It does not infer semantic edition labels.

Each configured download also declares a `release_kind`:

- `edition_or_snapshot`: a named provider edition or immutable source snapshot.
- `current_reference`: a current/rolling reference page or dataset.
- `rolling`: a mutable endpoint without a stable edition identifier.
- `supplement`: a scoped update supplement that must be applied only to its stated scope.

The global `release_management` section defines the state meanings and release-record contract. Release state records are intended for `reports/sources/releases/<source-id>.json`; they distinguish provider publication/commit time, metadata fetch time (`fetched_at`), discovery, acquisition, validation and application timestamps and retain release history. `fetched_at` is the first successful retrieval time for a release, stored in UTC ISO 8601 format; subsequent checks update the record-level `checked_at` without overwriting the release entry’s original `fetched_at`. The registry itself remains source configuration, not a mutable ledger of changing release events.

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

The command writes timestamped JSON and Markdown reports below `reports/sources/refreshes/`. Sources without configured generic HTTPS downloads are explicitly reported for manual review or a future protocol-specific adapter. The three implemented rolling/current-reference adapters discover content-fingerprint candidates and persist them in the release ledger. A matching fingerprint reuses the existing immutable snapshot; a new fingerprint is acquired under a new content-addressed release ID. If the content changes between discovery and acquisition, the acquired snapshot is retained but reported as a race and is not marked acquired in the ledger. Dry runs do not contact providers. This generic fingerprint check does not establish a provider's semantic release, publication date, or data correctness. It updates `latest_available` only; provider-specific semantic validation must succeed before a separate process can promote `latest_validated`.

The refresh command never imports into SQLite, changes approved data, or approves review proposals. Acquisition, provider validation, policy-based selection, and canonical application remain separate steps.

## Source-selection boundary

The approved field policy is in `config/source_selection.json`. The shared resolver in `tools/database/source_selection.py` accepts only observations from a source's `latest_validated` release and returns a provenance-rich decision. It enforces priority/fallback/custom-mixture semantics and manual override precedence; it does not acquire or validate provider datasets, calculate derived values, write SQLite, or publish assets. Fallback observations require explicit compatibility evidence. See `docs/data-sources/source-selection.md` for the normalized observation contract and limitations.

## Standardized source-management reports

Source refresh and policy resolution use the shared writer in `tools/sources/reporting.py`. Each run receives its own immutable report directory:
- Refresh: `reports/sources/refreshes/<run-id>/`
- Selection: `reports/sources/selections/<run-id>/`

The shared bundle contains `summary.md`, `records.csv`, `missing.csv`, `fallbacks.csv`, `conflicts.csv`, `overrides.csv`, `release_changes.csv`, `failures.csv`, and `provenance.json`. CSVs that do not apply to a report type are still written with headers, so downstream review tools can consume one stable artifact contract. The existing timestamped refresh JSON/Markdown files remain available for compatibility; their JSON report also points to the bundle directory. Each run ID is write-once: an existing bundle directory is never overwritten. Repeated or corrected analyses must use a new run ID.

Run policy resolution against an already-normalized observation file:

```fish
uv run python -m tools.resolve_source_selection --input raw_data/normalized/source-observations.json
```

The input's `game_id` values must already use the reviewed identity crosswalk. The command reads `config/source_selection.json`, selects only each source's `latest_validated` release, and writes the complete scalar/structured decision audit. It can accept an explicit `release_states` mapping, manual overrides, mixture assignments, and expected structured-record catalogues in the input JSON; see [source-selection documentation](source-selection.md) for the input contract.

The refresh bundle distinguishes unchanged snapshots, newly discovered/acquired release candidates, manual-review states, and acquisition/validation failures. A download marked `acquired_pending_source_validation` has not passed provider-specific semantic validation. Release changes do not promote `latest_validated`; selection reports do not promote `latest_applied`. Both commands are read-only with respect to the canonical database.

## Current implementation matrix

The registry currently contains 29 sources. Automated release discovery is implemented only for the three configured content-fingerprint sources (`natural_earth_admin0`, `iso_reference_mirror`, and `un_m49`) and Git commit metadata for `lipis_flag_icons`. This is release discovery, not universal provider refresh: the Git adapter does not download an archive, and fingerprint acquisition is not semantic dataset validation. Other API, subscription, manual and specialist sources remain registered but require manual review or a dedicated adapter.

The generic refresh command supports configured HTTPS downloads and the adapters above. It does not yet provide a complete provider-specific acquisition/normalization adapter for every source in the catalogue. A source can therefore be registered and policy-selected while still having no current normalized observations. The absence of an adapter or snapshot must be reported as unavailable/review-required, never as a zero value or proof that a country lacks the attribute.

The selection CLI consumes normalized JSON observations; it does not generate that file from raw provider snapshots. Identity matching/crosswalk review, provider parsing and semantic validation must occur before resolution. The report bundle records decisions and provenance but does not apply them to SQLite. These boundaries are intentional until provider adapters, semantic validation and explicit application workflows are separately implemented and reviewed.

## Project-wide approval-gated SQLite application

Canonical database writes are governed by one provider-neutral approval contract. A provider adapter may acquire, validate, normalize and resolve data, and produce review reports; it must not write canonical domain tables directly.

The shared approval primitives are implemented in:
- `migrations/004_application_approval.sql`
- `tools/database/application_approval.py`

An application artifact fingerprints every reviewed input file (normalized observations, source manifests/snapshots, identity crosswalks, policy and resolver outputs as applicable) and records the application domain plus metadata such as source releases and policy version. Paths are repository-relative and inputs must be inside the repository. At apply time, the shared guard re-reads and hashes every input; a changed or missing file invalidates the approval. A new proposal and review are then required.

The approval ledger distinguishes `pending`, `approved`, `rejected`, `invalidated` and `applied`. The event ledger records proposal, decision, invalidation and application events. The domain importer must verify an approved artifact before domain writes and mark it applied in the same SQLite transaction as those writes. Approval is single-use.

This establishes the common approval data model and reusable enforcement primitives. It does **not yet mean every existing import command has been migrated to require an approval ID**; provider/domain import integrations and user-facing proposal/approve/apply commands are follow-on work. Until those integrations are complete, do not treat legacy import commands as approval-gated. The WP1.5 importer is specifically still on its existing direct-import interface.

