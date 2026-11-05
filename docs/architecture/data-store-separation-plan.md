# Data-store separation and retention plan

**Status:** Proposed architecture; owner decisions A–C confirmed on 2026-11-05. This document is a plan only. No schema, database, importer, source policy, or data files are changed by this proposal.
**Scope:** Separate game-facing data from source research and acquisition; retain exactly two successful source-data versions per acquisition stream; reorganise the Markdown knowledge base.
**Current implementation:** `data/canonical/town_country_asset.sqlite`, schema v4, remains unchanged until this plan is verified and implementation begins.

## 1. Confirmed requirements

1. There are exactly two databases:
   - **Game database:** structured data the game actually needs. The game must not know source organisations, source URLs, source IDs, acquisition history, source-selection rules, licences, or provenance.
   - **Project source/research database:** source catalogue, URLs, dataset/release metadata, acquisitions, source observations, mappings, validation, comparison and application governance. The game never opens or depends on this database.
2. Keep exactly the **two latest successful acquired versions** for each source dataset/acquisition stream. A newly acquired version replaces the oldest retained version only after it has passed the required acquisition and source-data validation gates. The previous latest version remains available for comparison.
3. Remove obsolete version-specific data and files together. Do not leave orphaned snapshots, manifests, extracted text, normalized observations, validation outputs, or comparison artefacts.
4. The source catalogue itself is not rolling history: stable source identity, source organisations, URL records and URL roles, dataset definitions, field mappings, and source contracts remain available. The two-version limit applies to acquired/versioned source data and its version-specific derivatives, not to the stable catalogue.
5. The existing Markdown documentation remains the human-readable data dictionary and project/AI knowledge base. Do not create a third database for a game data dictionary.
6. JSON configuration remains machine-readable, version-controlled configuration/bootstrap. The Markdown knowledge base explains meaning, relationships, decisions and operational context. SQLite stores structured runtime/project records.

## 2. Database responsibilities

### 2.1 Game database

**Proposed path:** `data/canonical/town_country_asset.sqlite` (retain the established path to avoid unnecessary consumer/path changes).

Contains only game-facing records, such as:
- persistent `game_id` and game entity/type information;
- game-visible names, aliases and region membership;
- game-used geometry and asset references;
- curated game attributes and selected structured values;
- current scalar statistics and the reference year/period needed by game logic or display;
- game-facing availability/status only where the game needs it.

It must not contain:
- source/provider/organisation records or source IDs;
- source URLs, download/API endpoints, licences or attribution records;
- dataset/release/acquisition records, acquisition year or retrieval timestamps;
- raw or normalized source observations retained for research;
- source crosswalks, source-selection policy, validation/comparability evidence or research notes;
- source provenance columns on game-facing values.

A reference year is a property of the game value, not a source-acquisition year. Whether a game-facing value status such as observed/estimated/projected is retained will be decided during the schema mapping; it may remain only if it has a concrete game use.

### 2.2 Project source/research database

**Proposed path:** `data/project/project_data.sqlite` (local project state; not consumed by the game).

Proposed logical domains/tables (final names and normalization follow schema review):
- **Source catalogue:** stable source IDs, organisation/provider identity, homepage and descriptive metadata.
- **Source URLs:** one-to-many URL records with explicit roles such as homepage, documentation, API base, dataset page, download, terms/licence and evidence. URLs are first-class records, not a single overloaded URL column.
- **Datasets and acquisition streams:** stable dataset/download/API identifiers, source association, field coverage, format, acquisition method and validation contract.
- **Retained releases/acquisitions:** provider release label where available, acquisition timestamp/year, publication/reference period, status and links to manifests/artifacts.
- **Artifacts:** exact path, checksum, byte count, media type and artifact role for each retained acquisition.
- **Source observations:** normalized source-side values keyed by retained acquisition, source entity/country identifier, indicator and observation period; preserve original source value/unit/label alongside normalized values where useful.
- **Crosswalks and field mappings:** stable source entity IDs to `game_id`, source indicator to game field, units, transformations and mapping validity.
- **Validation and comparison:** source-contract validation outcomes, coverage/quality checks and comparisons between the two retained versions.
- **Governance/application:** approval records, application attempts, result status and enough evidence to reconcile project state with game DB state.

The project database is authoritative for acquisition/research records. It does not become a runtime dependency of the game.

## 3. Exact two-version retention contract

### 3.1 Retention unit

The retention unit is a **dataset acquisition stream**, identified by a stable source ID plus the stable dataset/download/API stream ID (not by a changing release label or year). A stream may contain several files/pages that together form one complete acquisition. Those files are one version bundle and count as one retained version.

Examples:
- one version of an annual statistical dataset export;
- one complete paginated API capture, including metadata and all record pages;
- one manual publication package containing a workbook and its supporting documents;
- one complete rolling-reference capture where the provider does not publish semantic release IDs.

Different datasets/download streams from the same provider have independent two-version windows. A supplemental dataset is its own stream unless its registered contract explicitly defines it as part of a parent bundle.

### 3.2 What counts as one of the two

A version enters the retained window only after:
1. acquisition is complete;
2. all expected files/pages are present and checksummed;
3. registered format/structure/identity checks pass;
4. provider-specific validation required for that stream passes;
5. its project-database records and artifact manifest are committed as one complete version.

Discovery alone, a partial download, an invalid response, or an incomplete paginated API run does not count as a retained version.

### 3.3 Promotion and cleanup sequence

For a new candidate version:
1. Acquire into a temporary staging area.
2. Validate completeness, checksums, schema, identifiers and source-specific semantics.
3. Write its metadata, artifacts and normalized observations to the project DB as a candidate.
4. In one controlled promotion operation, mark it retained and order the stream's retained versions newest-first.
5. Keep the two newest successful versions; remove every older version's version-specific DB rows and files.
6. Recompute the comparison between the two retained versions and publish only the current comparison artefacts.
7. Run a retention audit that proves there are no third retained versions, orphaned files, missing referenced files or unreferenced version-specific records.

If acquisition or validation fails, discard temporary candidate files and candidate rows; do **not** evict either valid retained version. This prevents a failed refresh from destroying the comparison baseline.

### 3.4 Data removed with an expired version

Delete all version-scoped material belonging exclusively to the expired version:
- raw snapshot files and API pages;
- manifests and checksums;
- extracted PDF text and extraction sidecars;
- parsed/normalized source observations;
- per-version validation details and comparison inputs;
- version-specific reports and generated derivatives.

Shared stable source/dataset catalogue records, URL definitions, field mappings, crosswalk definitions, and current policy/configuration are not deleted. A comparison report is regenerated for the current pair rather than accumulated indefinitely. Temporary staging is always cleaned after success or failure.

The retention audit must scan both database references and configured filesystem roots. Deletion must be manifest-driven and path-confined to approved source-data roots; it must reject path traversal, symlinks escaping those roots, checksum mismatches and attempts to delete unregistered files. Cleanup should be idempotent and produce a concise result report. No broad directory deletion.

### 3.5 Auditability boundary

Keep the current two versions' acquisition dates, provider labels, checksums, validation summaries and artifact manifests. Keep stable source metadata and current application/approval state. Do not retain obsolete source payloads or per-version derivatives after expiry. Any minimal operational event history retained for safe application recovery must not contain copies of expired source data; its exact fields and retention are part of the implementation design review.

## 4. Source configuration and Markdown authority

- `config/data_sources.json` remains the version-controlled source identity/configuration registry and bootstrap for stable source and dataset definitions.
- `config/source_selection.json` remains the approved source-selection policy. This project does not alter its priorities, fallbacks, mixture rules or latest-validated semantics.
- `data/manual/source_overrides.json` remains the explicit manual override input.
- The project database stores richer source URL records, acquired versions, source observations, validation and comparison results. A consistency check must compare the stable source/dataset IDs in JSON with the corresponding project catalogue records.
- URLs in the project DB are typed records; JSON can continue to provide initial/default URLs and acquisition configuration. The database records the URL actually used for each retained artifact as well as its configured role.
- Markdown defines the game-field dictionary: field ID/name, type, units, allowed values, null semantics, reference-period semantics, validation rules, source mapping links and game usage. It is not duplicated in a third database.

## 5. Existing schema migration and table disposition

The current canonical database is schema v4. Existing tables cannot simply be dropped or moved without an explicit, lossless mapping and a transition strategy.

| Existing area | Proposed destination / treatment |
|---|---|
| `countries` | Game DB, limited to stable game identity and game-facing entity/type state |
| `country_names`, `country_regions` | Game DB where used by the game |
| `country_geometries`, `country_flags` | Split: game-facing geometry/asset references stay in game DB; source URLs, source mappings and review evidence move to project DB |
| `country_sources` | Project DB |
| `dataset_imports`, `import_runs` | Project DB; version-scoped rows obey two-version retention |
| `country_attributes` | Classify each attribute by actual game use; game-required curated values only in game DB, source-side/raw attributes in project DB |
| `current_statistics`, `selected_game_data` | Game DB receives only game-facing values and reference periods; source/release/provenance fields and source-side observations move to project DB |
| `review_proposals` | Project DB |
| `application_approvals`, `database_application_events` | Project-side governance, with a crash-safe cross-database application/reconciliation design |
| `schema_migrations` | Each database owns its own independent migration ledger |

Migration must inventory every row and column, classify it, copy and verify counts/checksums/relationships, and only then remove source-only structures from the game DB in a later migration. No existing data is discarded as an incidental side effect. The old database is backed up before cutover. A rollback path remains available until owner validation and consumer cutover are complete.

### Cross-database approval/application

Migration 004 currently couples approval/event records and domain writes in one SQLite transaction. That guarantee must not be silently weakened. The new design must keep approvals in the project DB while ensuring game writes remain atomic within the game DB. Implement an explicit, idempotent application state machine with recovery/reconciliation for interruption between project approval and game commit, and prove that retries cannot duplicate or partially apply data. Do not add source/provenance columns or project-database dependencies to game records to solve this. The exact protocol and failure tests are a required design gate before implementation.

## 6. Documentation architecture

The existing Markdown structure remains authoritative and should be extended rather than replaced with a parallel documentation tree.

- `docs/README.md`: root index and navigation.
- `docs/architecture/README.md`: architecture index; link this plan and, after approval, the final store-boundary contract.
- `docs/data-sources/README.md`: source, acquisition, release, validation and comparison index.
- `docs/implementation/README.md`: implementation procedures and owner-validated evidence.
- `docs/roadmap/README.md`: feature plans, stages and acceptance criteria.
- A concise project context document: repository purpose, architecture boundaries, key indexes, current status, commands, workflow conventions, important invariants and links to detailed documents. It is an orientation/memory aid, not a duplicate of every feature document.
- Field definitions remain in Markdown under the data-dictionary documentation area, with an index and links to source assessments. If the current repository has no dedicated data-dictionary index, add one only after checking and mapping the existing field-contract documents; do not move or duplicate them blindly.

Every implementation stage updates the relevant indexes and documents in the same change as code/config/schema. Feature documents follow `docs/feature-documentation-standard.md`.

## 7. Implementation sequence

No implementation starts until the owner verifies this plan.

| Stage | Scope | Required documentation in the same stage |
|---|---|---|
| 0. Inventory and freeze contract | Inventory current DB schema/data, JSON registries, manifests, snapshots, reports, derived files, consumers and approval workflow. Produce a table/column/file disposition and baseline counts/checksums. No deletion. | Architecture plan, source-management rules, implementation checklist |
| 1. Project DB foundation | Add project DB path, connection/migration framework, schema and integrity tests. Add source catalogue, typed URLs, datasets and two-version release model. | Project DB architecture, schema reference, CLI/config docs |
| 2. Acquisition retention | Adapt generic and dedicated acquisition paths to version bundles, staging, validation-gated promotion, exact two-version cleanup, orphan audit and failure recovery. | Source-management and provider acquisition docs |
| 3. Source observations and mappings | Move/implement source observations, crosswalks, field mappings, validation and pairwise comparison in project DB. Keep source-selection policy unchanged. | Data dictionary, source mapping, validation/comparability docs |
| 4. Approval/application protocol | Move approvals/events to project DB and implement idempotent crash-safe apply/reconciliation into game DB. | Approval workflow and operator runbook |
| 5. Game DB separation | Migrate only game-facing records, remove source metadata/provenance from game schema, update importers/resolvers/consumers to use project DB before application and game DB at runtime. | Game DB architecture and affected feature docs |
| 6. Documentation and consumer cutover | Complete indexes/context guide; verify game has no project DB imports or source metadata access; retire obsolete compatibility paths only after proof. | All affected indexes and architecture/context docs |
| 7. Owner validation and closure | Run migration, retention, data parity, failure recovery, integrity, FK, test suite and game-isolation checks locally. Close only after owner reports results. | Validation evidence, implementation log and roadmap status |

## 8. Acceptance criteria

### Separation
- Game runtime opens only the game DB and has no dependency on project DB, source registry, acquisition tools or source URLs.
- Game DB schema and records contain no source IDs, provider names, acquisition years, source URLs, source release IDs or provenance fields.
- Every game-facing record has a valid persistent `game_id`; required game data are preserved through migration.

### Project data and retention
- Each acquisition stream has no more than two successful retained versions.
- The retained versions are the two newest successful acquisitions, not merely the two newest discovered candidates.
- Each retained version has complete source URL, acquisition timestamp/year, manifest, checksum, artifact and validation metadata.
- A new successful version replaces the oldest; failed/incomplete acquisition leaves the two retained versions untouched.
- Expired version rows and all version-specific files/derivatives are removed; no dangling DB references or orphan files remain.
- Source catalogue, URL roles, field mappings and stable crosswalk definitions remain available.
- Comparisons use the two retained versions only and are regenerated rather than accumulated.

### Governance and migration
- Existing data are fully inventoried and accounted for; migration parity is demonstrated before cleanup.
- Source-selection policy and manual overrides are unchanged.
- Approval cannot be bypassed; application retries are idempotent and crash recovery is tested.
- Both databases pass SQLite integrity and foreign-key checks.
- Migration backup and rollback procedure are tested.

### Documentation
- Root and subject indexes are complete and accurate.
- The Markdown data dictionary remains the field-definition authority.
- The project context guide makes the architecture, relationships, workflow and key docs discoverable to a future developer/ChatGPT session.
- Each implementation stage updates documentation with its code and tests.

## 9. Owner verification

The following requirements are confirmed:
- Exactly two latest successful versions per source acquisition stream.
- The older retained version is replaced only when a new version has been acquired and validated successfully.
- Version-specific files and database rows are cleaned together; stable catalogue metadata is retained.
- Game DB contains no source identity or provenance knowledge.
- Markdown remains the data dictionary and persistent human/AI project knowledge base.
- Existing source-selection policy is not changed by this work.

The plan is ready for owner review. Any requested correction should be made here before Stage 0 begins.
