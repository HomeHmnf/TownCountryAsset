# Project configuration reference

## Purpose and authority

This document is the central human-readable reference for meaningful project configuration. It explains the purpose, ownership, semantics, dependencies, and change rules for configuration files and environment settings across TownCountryAsset.

Machine-readable files remain authoritative for runtime values. This document is authoritative for understanding what those values mean and how they may safely be changed. When implementation and documentation disagree, do not guess: verify the implementation, then update this reference in the same change.

Do not add explanatory pseudo-comments to JSON. JSON files must remain valid JSON. Put durable explanations, policy definitions, field names, examples, and change guidance here.

## Configuration inventory

| Configuration | Purpose | Main consumers |
|---|---|---|
| `config/data_sources.json` | Authoritative catalogue of external and local data sources, acquisition definitions, terms, license metadata, and storage conventions | Shared source manager and provider refreshers |
| `config/wp1_5_data_sources.json` | WP1.5 field contract: approved field IDs, keys, storage types, units, and field-specific methodology | WP1.5 acquisition, normalization, and import |
| `config/source_selection.json` | Versioned project-wide policy for primary sources, fallbacks, release selection, manual overrides, compatibility, and missing values | Source refresh, resolution, reporting, and later explicit application |
| `config/wp1_5_resource_catalog.json` | Candidate structured catalogue of natural-resource groups, resource keys, metrics, and required record fields | WP1.5 natural-resources handling |
| `config/country_identity_registry.json` | Persistent country/entity identity registry; stable `game_id`, names, source identifiers, ISO attributes, and review state | Identity, source crosswalk, review and import workflows |
| `config/country_flag_mapping.json` | Explicit mapping from persistent identities to flag-source codes, including review status and evidence | Flag refresh and asset generation |
| `config/entity_types.json` | Entity-type definitions used by the project | Identity and entity validation |
| `config/regions.json` | Region definitions and memberships used by asset generation | Country data compilation |
| `config/generation.json` | Asset-generation and geometry/output settings | Data-refresh and asset-generation pipeline |
| `.env` (local; not committed) | Machine-specific paths, endpoint overrides, and operational switches | CLI and refresh pipeline |

The inventory must be updated whenever a meaningful configuration file is added, removed, renamed, or changes responsibility. This table is a starting index, not permission to duplicate a setting across files.

## Source catalogue and source-selection policy

### Source catalogue

`config/data_sources.json` is the single catalogue of source identities and acquisition metadata. It answers: *what sources exist, where they are, what they provide, how they are acquired, and what terms apply?*

- Source IDs are stable provider identifiers, not release identifiers. For example, use `un_wpp` as the source ID and `2024-main-demographic` as a release key. Edition years, versions and vintages belong in release metadata/manifests, while the source record keeps a stable provider name.
- When a provider ID is normalized, list the previous ID in `legacy_source_ids`. Existing raw snapshot paths and manifests remain immutable and readable; new acquisitions use the stable ID. Never rewrite historical provenance just to rename a provider.
- Domain/field contracts refer to source IDs rather than copying source definitions.
- The catalogue may include downloadable, API, Git, manual, subscription, and per-record evidence sources.
- Acquisition settings do not constitute approval to use a source for a field.
- License classification is informational for acquisition; it does not grant redistribution rights or make restricted material open.
- Raw snapshots remain local and immutable; manifests, checksums, source metadata, and policy documentation are tracked.

### Source-selection policy

`config/source_selection.json` is the manually reviewed, versioned policy for choosing sources per field. It is deliberately separate from `data_sources.json`: availability and acquisition metadata must not be confused with a decision to use a source. The initial policy covers the 41 owner-approved WP1.5 fields and is project-wide in design.

Exactly three selection modes are approved:

1. **Priority source** (`priority_source`): designate one source as the sole selected source for the field. If it has no usable value, leave the value missing. Do not fall back automatically.
2. **Primary with missing-value fallback** (`primary_with_fallback`): use the primary source where it provides a valid value; fill only missing values from explicitly ordered fallback sources. A lower-priority source must never overwrite a valid higher-priority value.
3. **Custom mixture with manual overrides** (`custom_mixture`): explicitly combine source selections by country, record, or other declared scope, with manually supplied values taking precedence where an override is defined. The policy must make precedence and scope explicit.

The third mode supports a manual override dataset/file, but the override data itself should be stored separately from the policy. The policy points to it and defines how it wins. This prevents source preference changes from erasing manual work.

The current policy is version 1 and has owner-approved status. Its 41 field assignments encode the approved source priorities and fallback modes. A `primary_with_fallback` field may have a conditional fallback requirement that is not yet executable because a suitable provider is not registered; such a fallback must not be guessed or silently substituted. For example, the capital-city policy records the need for a suitable UN official source but does not mis-use the UN M49 identity reference as a capital source. The natural-resources policy requires resource/metric-specific specialist providers to be registered and mapped before they can fill USGS coverage gaps.

### Resolution and provenance rules

All modes must follow these rules:

- A missing value is not zero, an empty string, or an inferred value.
- Never silently substitute or merge sources.
- Preserve each original source observation and its source ID, release/version, observation period, source reference, retrieval time, and methodology.
- Record the exact winning source for every resolved value. For a manual override, record the override record, reason, and effective/change timestamp.
- Keep source values separate from resolved values so resolution can be reproduced.
- Report conflicts, missing values, rejected candidates, fallback use, and manual overrides.
- A changed source release may trigger a new validation/review report; it must not silently change the approved selection or resolved dataset.
- A policy change must be explicit, reviewed, versioned, and reproducible against preserved source snapshots.

### Release selection and refresh boundary

`release_policy.selection` is `latest_validated`, not `latest_available`. These terms are distinct:

- **Latest available**: newest release identified at the provider, whether or not it has been acquired or checked.
- **Latest validated**: newest acquired release that passed the registered acquisition and source/data-contract checks; this is the release eligible for selection.
- **Latest applied**: release actually imported into the canonical dataset. It may lag the latest validated release.

The refresh architecture separates release discovery, acquisition, provider-specific validation, selection, and application. The current command (`uv run python -m tools.refresh_sources`) attempts missing configured HTTPS snapshots, verifies existing snapshot checksums, and writes operational reports. Content-fingerprint discovery is implemented for the Natural Earth Admin 0 rolling URL, the third-party ISO reference mirror, and the UN M49 current HTML reference. GitHub default-branch commit discovery is also implemented for the `lipis_flag_icons` source; it records the immutable commit SHA, provider commit timestamp, and UTC `fetched_at` time (the first retrieval of that release metadata, preserved across later checks), but does not acquire the repository archive. These adapters update only `latest_available`; they do not promote a release to validated or applied. API metadata, subscription, and manual sources still require protocol-specific adapters or manual review. A successful acquisition passes only the registered response checks; source-specific semantic validation is still required, and no `latest_validated` promotion is made by this command. Refresh does not resolve or import values automatically. Resolution uses the approved policy and records decisions; applying resolved data to the canonical database remains a separate explicit step. See `docs/data-sources/source-management.md` for the current command contract and limitations.

The manual override dataset is `data/manual/source_overrides.json`; it is intentionally separate from policy. The file need not exist until actual overrides are supplied. The policy defines its precedence and expected scope, while each override must retain its reason and provenance.

## Identity and identifier configuration

- `game_id` is the permanent internal identity. Never replace it with a source ID or ISO code.
- Source identifiers and ISO alpha-2/alpha-3 codes are separate attributes, even when their character strings happen to match.
- ISO assignment authority and review/approval rules are described in the identity contract and ISO review documentation. A candidate/reference match is not an approval.
- Identity reconciliation is read-only. It may report exact names, normalized name variations, explicitly reviewed variants, ambiguities, and unmatched rows; it must not infer identity from code coincidence or force ambiguous matches.
- Explicit registry-name-to-reference-name variants are maintained in `REVIEWED_NAME_VARIANTS` in `tools/propose_iso_assignments.py` and shared by ISO proposal generation and identity reconciliation. Each mapping targets an exact reference label and carries a rationale; it is matching evidence only, never an ISO assignment or verification.
- Identity registry changes and assignment approvals require explicit review. Do not mark an assignment verified merely because a reference source publishes a code.

Related references: `docs/architecture/country-identity-contract.md`, `docs/architecture/iso-assignment-review-log.md`, and `docs/review/iso-alpha2-gap-investigation.md`.

## WP1.5 data configuration

- The WP1.5 contract contains the 41 owner-approved field IDs. Do not add fields or reinterpret a field without an explicit scope decision.
- `primary_source` values in the contract describe the source candidates; `config/source_selection.json` is authoritative for approved source priorities, selection mode and fallback rules.
- Scalar observations and structured collections use their declared storage types. Preserve units, definitions, reference periods, actual/estimated/projected status, source release, and methodology.
- Keep resource catalogue definitions distinct from observations. A catalogue entry does not imply that a country has that resource.
- Do not infer absence from a missing provider row.
- Population density may be derived only when source periods and definitions align and the derivation is documented.
- Current statistics are not a historic time-series store unless the project scope is explicitly changed.

Related reference: `docs/data-sources/wp1-5-sources.md`.

## Environment and CLI configuration

- `.env.example` documents supported environment variables; `.env` is local and must not be committed.
- Process environment values take precedence over `.env` values where the CLI supports both.
- Paths may be absolute or repository-root-relative according to the consuming CLI's contract.
- Never put credentials, tokens, or private secrets in tracked JSON or Markdown configuration.
- Environment overrides are operational settings, not a replacement for the tracked source catalogue or approved source-selection policy.
- Fish-compatible commands should be used in project instructions and validation examples.

Related references: `docs/cli-tool.md` and `docs/implementation/data-refresh.md`.

## Database, migrations, pipeline, and reporting

- Database schema changes are defined by ordered migration files. The local SQLite database is generated state and is not committed.
- Canonical database path and migration responsibilities are documented in `docs/architecture/canonical-database.md` and `docs/implementation/database.md`.
- Pipeline configuration must preserve the existing JSON workflow until parity and consumer cutover are explicitly approved.
- Acquisition, validation, normalization, database import, review approval, and asset publication are separate steps. Success in one step must not imply success or approval in another.
- Shared database reports use `reports/database/<database_id>/<domain>/<report_id>/` with a Markdown summary, record-level CSVs, unmatched CSVs where applicable, and JSON provenance. Reuse `tools/database/reporting.py`; do not invent parallel report layouts.
- Report provenance should identify source/release, checksums, parser/schema version, field mappings, selection policy version, and read-only/approval state where applicable.

## Change and review policy

For every meaningful configuration change:

1. Identify the owning configuration file and avoid duplicating the same setting elsewhere.
2. Update this reference when the file's purpose, fields, semantics, or operational use changes.
3. Validate JSON syntax and the relevant schema/contract before running imports.
4. Add or update tests for parsing, validation, precedence, and safety behaviour.
5. Record source release/version and provenance where data acquisition is involved.
6. Produce the relevant standardized report and review its unresolved items.
7. Do not approve identity assignments, source selections, or manual overrides implicitly as a side effect of refresh/import.
8. Preserve unrelated local working-tree changes; do not stage or overwrite them.

## Documentation ownership

This file is the central index for meaningful configuration. More specialized documents may explain implementation details, source-specific limitations, or domain methodology, but should link back here rather than redefining project-wide configuration authority.
