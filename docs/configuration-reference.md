# Project configuration reference

## Purpose and authority

This document is the central human-readable reference for meaningful project configuration. It explains the purpose, ownership, semantics, dependencies, and change rules for configuration files and environment settings across TownCountryAsset.

Machine-readable files remain authoritative for runtime values. This document is authoritative for understanding what those values mean and how they may safely be changed. When implementation and documentation disagree, do not guess: verify the implementation, then update this reference in the same change.

Do not add explanatory pseudo-comments to JSON. JSON files must remain valid JSON. Put durable explanations, policy definitions, field names, examples, and change guidance here.

## Configuration inventory

| Configuration | Purpose | Main consumers |
|---|---|---|
| `config/data_sources.json` | Authoritative catalogue of external and local data sources, acquisition definitions, terms, license metadata, and storage conventions | Shared source manager and provider refreshers |
| `config/wp1_5_data_sources.json` | WP1.5 field contract: approved field IDs, keys, storage types, units, candidate source references, and field-specific methodology | WP1.5 acquisition, normalization, and import |
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

- Source IDs are stable machine identifiers. Human-readable names and descriptions belong in the source record.
- Domain/field contracts refer to source IDs rather than copying source definitions.
- The catalogue may include downloadable, API, Git, manual, subscription, and per-record evidence sources.
- Acquisition settings do not constitute approval to use a source for a field.
- License classification is informational for acquisition; it does not grant redistribution rights or make restricted material open.
- Raw snapshots remain local and immutable; manifests, checksums, source metadata, and policy documentation are tracked.

### Source-selection policy (planned configuration)

The future `config/source_selection.json` will be the manually reviewed policy for choosing sources per field. It is deliberately separate from `data_sources.json`: availability and acquisition metadata must not be confused with a decision to use a source.

Exactly three selection modes are approved:

1. **Priority source** (`priority_source`): designate one source as the sole selected source for the field. If it has no usable value, leave the value missing. Do not fall back automatically.
2. **Primary with missing-value fallback** (`primary_with_fallback`): use the primary source where it provides a valid value; fill only missing values from explicitly ordered fallback sources. A lower-priority source must never overwrite a valid higher-priority value.
3. **Custom mixture with manual overrides** (`custom_mixture`): explicitly combine source selections by country, record, or other declared scope, with manually supplied values taking precedence where an override is defined. The policy must make precedence and scope explicit.

The third mode supports a manual override dataset/file, but the override data itself should be stored separately from the policy. The policy points to it and defines how it wins. This prevents source preference changes from erasing manual work.

No source-selection file or assignments are to be introduced as approved selections until the M49 identity/reference review has been completed and the owner has reviewed the candidates. The approved policy must be versioned and auditable.

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
- `primary_source` values in the current contract identify candidates, not final owner-approved source-selection policy.
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
