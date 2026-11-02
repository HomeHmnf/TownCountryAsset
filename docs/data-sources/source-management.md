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

The Bahrain annual unemployment API has a dedicated provider adapter, `tools.sources.bahrain_unemployment`, because it is a paginated live API rather than a static download. It reads the `bahrain_open_data` contract from the central registry and writes timestamped raw JSON pages under `raw_data/sources/bahrain_open_data/unemployment_yearly/<UTC timestamp>/` with a checksum manifest under `data_manifests/sources/bahrain_open_data/unemployment_yearly/`. See [Bahrain annual unemployment data acquisition](bahrain-unemployment-data-acquisition.md). The adapter is acquisition-only and does not normalize observations or write to SQLite.

The ICASEES Central African Republic national-accounts workbook and its two supporting PDFs are documented in [ICASEES national accounts](icasees-central-african-republic-national-accounts.md). The source is registered as `icasees_national_accounts` in `config/data_sources.json`, with manual release review and no generic download adapter. Because the three committed files use their existing publication-oriented paths, the dedicated `tools.assess_icasees_national_accounts` CLI records and verifies their checksums without relocating or downloading them. It reuses the central registry and shared source-report writer, inventories the workbook, extracts historical/revised GDP blocks, and inspects PDF text when run with pypdf. It does not promote a release or import observations. See the ICASEES source document for commands and the unresolved unit/scale-label issue.

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

An acquisition result is labelled `acquired_pending_source_validation`; it means the download and its generic registered response checks succeeded, not that provider-specific data semantics, coverage, identifiers, or release suitability have been validated. Existing valid snapshots are reported as unchanged. Invalid snapshots are retained for investigation and are never silently replaced. A dry run reports intended acquisitions without making network requests.

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

For multi-file provider adapters, the derived WP1.5 manifest may declare `additional_inputs` (raw snapshots) and `upstream_manifests` (the original source-manager manifests). The statistics importer validates the additional snapshot checksums and fingerprints every listed raw file and upstream manifest at proposal and apply time. This prevents a scoped supplement or secondary dataset from changing after approval without invalidating the application. The UN WPP adapter uses this mechanism for its main demographic file, main age-sex file and Togo interim update.

The WP1.5 statistics importer, identity-registry importer, country-data importer and review-data importer are integrated with this gate:
- Identity proposals fingerprint the registry, candidate countries payload and candidate manifest after validating their internal consistency.
- Country-data proposals fingerprint the manifest, countries payload and all three game-ID geometry profiles, after validating checksums, identity coverage and GeoJSON structure.
- Review-data proposals fingerprint the identity registry, ISO reference/provenance/proposal report, Persian candidates/provenance, entity taxonomy and flag mapping.
- WP1.5 proposals fingerprint normalized observations, the explicit identity crosswalk, source manifest, immutable raw snapshot, WP1.5 field contract and (when present) project source-selection policy.

All importers independently rebuild/recheck their artifacts and record application completion in the same transaction as their domain writes. Calling an importer without a valid approved application ID is rejected. A changed or missing input invalidates approval and requires a new proposal and review.

### Required application order

Identity records are a prerequisite for any application whose crosswalk references `game_id` values in the canonical `countries` table. Therefore, on a new or empty canonical database, apply the identity registry before country data, review data, or WP1.5 observations. A pending or approved identity proposal is not sufficient: the identity importer must complete successfully and its country rows must exist before downstream importers run.

The standard inspected sequence is:

1. Acquire immutable source snapshots and verify their manifests/checksums.
2. Parse, validate and normalize provider data; build and review the explicit identity crosswalk.
3. Generate the application manifest and proposal artifact.
4. Inspect the proposal's domain, metadata, artifact SHA-256, exact input paths, hashes and byte counts.
5. Explicitly approve that exact artifact.
6. Apply the identity registry first when canonical identity rows are absent.
7. Apply the domain dataset using its own separately approved artifact.
8. Audit domain counts, provenance, approval/event state, SQLite integrity and foreign keys.
9. Promote a release to `latest_validated` only through the separate release-validation process; database application does not implicitly promote a release.

### UN WPP 2024 Medium example (2026 observations)

This is the first fully inspected WP1.5 provider application. The canonical population reference date is 1 July. The 2026 values are projections. The main demographic and age-sex files are separate immutable snapshots; the 2026-01-19 Togo interim ZIP is a scoped correction and applies only to Togo, not as a replacement for either main release. The adapter validates the three snapshots, upstream manifests, M49-based LocID crosswalk and age/sex structure before producing normalized observations. Taiwan is included through the specifically approved WPP-only exception (LocID 158); this does not change global identity, ISO or M49 assignments.

The reviewed candidate contained 199 approved game-country mappings and 1,194 projected observations: six fields per country (population, population growth, median age, age distribution, sex distribution and net migration). Four fields are scalar (796 scalar records total) and two are structured (398 structured records total). Small differences of a few people between published totals and sums of rounded age/sex components are retained rather than artificially adjusted.

For this inspected run, the identity application was:
- Approval ID: `identity-registry-2026-11-01`
- Artifact SHA-256: `dbc2e7d1f2ed14452c07ec10ff5e938276cf9e354d5baf4cf422e0360f049f1f`
- Result: 242 countries, 250 names, 237 region memberships and 242 source mappings; database integrity and foreign-key checks passed.

The WP1.5 application was:
- Approval ID: `un-wpp-2026-11-01`
- Artifact SHA-256: `000ec80bae30c890f1d4487e56908b809434b14c6fef7b477d6a29b655fdce24`
- Release: `2024-main-demographic+2026-01-19-togo-update`
- Result: 1,194 observations (796 scalar, 398 structured), 199 crosswalk mappings; database integrity and foreign-key checks passed.

The commands used for the identity proposal, approval and application are:

```fish
uv run python -m tools.manage_database_applications propose-identity \
  --approval-id identity-registry-2026-11-01

uv run python -m tools.manage_database_applications approve \
  --approval-id identity-registry-2026-11-01 \
  --actor project-owner \
  --note "Approved reviewed 242-country identity registry application."

uv run python -m tools.import_identity_registry \
  --approval-id identity-registry-2026-11-01
```

The commands used for the already-built and reviewed WPP candidate are:

```fish
uv run python -m tools.manage_database_applications propose-wp1-5 \
  --approval-id un-wpp-2026-11-01 \
  --observations generated/un_wpp_2026_candidate_20261101/normalized_observations.json \
  --crosswalk data/manual/source_crosswalks/un_wpp.json \
  --manifest generated/un_wpp_2026_candidate_20261101/application_manifest.json

uv run python -m tools.manage_database_applications approve \
  --approval-id un-wpp-2026-11-01 \
  --actor project-owner \
  --note "Approved reviewed UN WPP 2026 Medium candidate; 199 countries, 1194 projected observations, six fields."

uv run python -m tools.import_wp1_5 \
  --observations generated/un_wpp_2026_candidate_20261101/normalized_observations.json \
  --crosswalk data/manual/source_crosswalks/un_wpp.json \
  --manifest generated/un_wpp_2026_candidate_20261101/application_manifest.json \
  --approval-id un-wpp-2026-11-01
```

### Approval-gated source release validation and promotion

A provider release becomes eligible for normal source selection only after a separate release-validation proposal is reviewed and explicitly approved. This is distinct from the WP1.5 database-application approval: release validation changes source eligibility, not canonical database contents.

The initial implementation is scoped to the UN WPP WP1.5 provider. Start from a completed, passing automated validation report:

```fish
uv run python -m tools.validate_wp1_5 --source un_wpp
```

Use the exact report path printed by that command to prepare an immutable release proposal:

```fish
uv run python -m tools.validate_source_release propose \
  --source un_wpp \
  --approval-id un-wpp-release-2026-11-02 \
  --report reports/database/town_country_asset/wp1-5/un_wpp/<timestamp>/validation_report.json \
  --actor project-owner \
  --note "Reviewed WPP source validation and resolver compatibility evidence."
```

The proposal requires PASS results for the snapshot fingerprints, canonical database integrity, six-field coverage, WPP demographic semantics, canonical value parity, Togo supplement provenance, and source-selection resolver compatibility. It fingerprints the validation report, candidate manifest, normalized observations, source registry, selection policy, raw snapshots and upstream acquisition manifests. The proposal records that resolver release eligibility was simulated in memory; it does not represent an existing promotion.

Inspect the proposal JSON and its SHA-256, then make the explicit decision:

```fish
uv run python -m tools.validate_source_release approve \
  --approval-id un-wpp-release-2026-11-02 \
  --actor project-owner \
  --note "Approved the exact release-validation evidence."
```

To reject instead, use the `reject` subcommand with the same approval ID and a reason. A decision is single-use; a rejected or approved proposal cannot be decided again.

Only after approval, promote the release:

```fish
uv run python -m tools.validate_source_release promote \
  --approval-id un-wpp-release-2026-11-02
```

Promotion rechecks every evidence fingerprint and the PASS report before writing `reports/sources/releases/un_wpp.json`. It updates only `latest_validated` and release history; it does not change `latest_applied`, the source registry, or canonical SQLite data. The current implementation refuses to replace a different already-validated release; supersession requires a separately reviewed workflow. The source-selection resolver will then read this ledger state instead of requiring a simulated `release_states` mapping.

## Automation backlog

The current workflow is intentionally inspected one provider/application at a time. Future orchestration should automate repeatable mechanics without weakening the approval boundary:

- Preflight the canonical database and check that all crosswalk `game_id` values exist; if not, report the identity prerequisite and stop before beginning a domain transaction.
- Check existing application records and never silently create duplicate proposals or approvals.
- Acquire/verify immutable snapshots, run provider-specific validation, normalize data and build crosswalks through registered adapters.
- Produce a review bundle with coverage, unmatched identities, held/excluded records, field counts, units, statuses, provenance and rounding/reconciliation diagnostics.
- Propose an immutable artifact and display its exact SHA-256 and input fingerprints for human review.
- Wait for explicit human approval; automation must not approve its own proposal or silently reuse an approval for changed inputs.
- Apply identity prerequisites before dependent domains, then apply the approved domain artifact transactionally.
- Run post-application audits and report approval/event state, counts, provenance, integrity and foreign-key results.
- Keep release promotion separate from database application; never automatically promote merely because import succeeded.

The orchestrator should expose separate `prepare`, `review`, `approve`, `apply` and `audit` states (or equivalent commands). A failed preflight must not invalidate or consume an otherwise valid approval unless one of its fingerprinted inputs has actually changed. Provider-specific adapters and domain importers remain responsible for their contracts; the orchestrator coordinates them and does not bypass them.


## Automated WP1.5 candidate validation

Run the provider validation suite with one stable command:

```fish
uv run python -m tools.validate_wp1_5 --source un_wpp
```

The validator discovers the newest complete candidate for the requested source by the candidate manifest retrieval timestamp. It rejects tied newest candidates and incomplete newest candidates rather than silently selecting an older run. It verifies the candidate manifest, normalized observation metadata, raw snapshot checksums and upstream acquisition-manifest fingerprints.

The canonical database is mandatory and resolved from the project default at `data/canonical/town_country_asset.sqlite`. Validation opens it in SQLite read-only/query-only mode. Missing or inaccessible canonical databases and failed integrity/foreign-key checks stop the run.

The shared runner is in `tools/wp1_5_validation.py`; provider semantic validators are registered in `tools/wp1_5_validators/`. The initial UN WPP validator checks six-field country coverage, duplicate country-field observations, projected 2026 status, units, all 21 ordered age bands, finite/non-negative age and sex counts, population reconciliation tolerances, absolute net-migration semantics, canonical database value parity when the candidate release has been applied, and Togo source-reference evidence for review.

Reports are written to a unique UTC timestamp directory under:

```text
reports/database/town_country_asset/wp1-5/<source>/<timestamp>/
  validation_report.json
  validation_report.md
  validation_exceptions.csv
```

The validator is read-only: it does not create approvals, import observations, update the canonical database, or promote a release. A warning means a review item remains; a failure returns a non-zero exit status. Add future provider validators through the registry in `tools/validate_wp1_5.py` and implement provider-specific rules behind the shared validator interface. Extend the shared runner for reusable checks rather than adding one-off audit commands.
