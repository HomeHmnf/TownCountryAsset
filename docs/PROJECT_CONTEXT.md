# Project context — TownCountryAsset

**Purpose:** Orientation and durable working context for developers and future ChatGPT sessions. This is a navigation and invariants document, not a replacement for the detailed architecture, feature, source-assessment or implementation records.
**Last reviewed:** 2026-11-05.

## Start here

1. [Documentation index](README.md) — subject-area indexes and documentation rules.
2. [Architecture index](architecture/README.md) — stable system contracts.
3. [Data-store separation plan](architecture/data-store-separation-plan.md) — owner-confirmed proposal awaiting plan verification; no implementation has started.
4. [Data-source index](data-sources/README.md) — providers, acquisition, validation, source selection and comparability.
5. [Implementation index](implementation/README.md) — implementation and owner-run validation history.
6. [Roadmap index](roadmap/README.md) — feature plans and work packages.
7. [Feature documentation standard](feature-documentation-standard.md) — required structure for new feature documentation.

## Architecture at the current checkout

The current implementation still has one canonical SQLite database at `data/canonical/town_country_asset.sqlite`, currently schema v4, with migrations 001–004. It contains both game-facing data and source/research/governance information. The current schema and table contracts are described in [canonical database architecture](architecture/canonical-database.md).

The owner has confirmed a target architecture with exactly two databases:

- **Game DB:** only the values, identities, names, regions, geometry and other records the game actually needs. It must have no source organisations, source IDs, source URLs, acquisition years, release metadata, provenance, source-selection policy or research dependencies.
- **Project source/research DB:** source catalogue and organisations, typed source URLs, dataset definitions, acquisitions, retained source versions, raw/normalized source observations, source-to-game mappings, validation/comparison evidence and approval/application governance. The game must never open this DB.

Proposed project DB path: `data/project/project_data.sqlite`. Proposed game DB path remains `data/canonical/town_country_asset.sqlite` to avoid unnecessary path/consumer changes.

**Important status distinction:** this is an approved design direction, not implemented behavior. Do not write code or change migrations until the owner verifies the complete plan. Follow the staged sequence and acceptance criteria in the [separation plan](architecture/data-store-separation-plan.md).

## Source-version retention invariant

The target project DB retains exactly the **two latest successful acquired versions per stable source dataset/acquisition stream**. A version may be a multi-file publication bundle or a complete paginated API capture. The stream is keyed by stable source and dataset/download/API IDs, not by a release year.

A candidate is eligible only after complete acquisition and required validation. On successful promotion, retain the newest two and delete older version-specific database rows and files together, including snapshots, manifests, PDF text derivatives, normalized observations and version-specific reports. Failed or incomplete acquisitions must not evict either valid retained version. Stable source catalogue entries, typed URL records, dataset definitions, field mappings and crosswalk definitions remain.

The exact contract and cleanup safety requirements are in the [separation plan](architecture/data-store-separation-plan.md). Until implementation is complete, existing source acquisition behavior remains authoritative; do not claim the two-version cleanup is active.

## Data and source policy

- `config/data_sources.json` is the central source identity/configuration registry and bootstrap.
- `config/source_selection.json` is the approved field-level source-selection policy.
- `data/manual/source_overrides.json` contains explicit manual overrides.
- Do not change source priorities, fallback rules, mixture policy or latest-validated semantics without a separate review and explicit approval.
- JSON is machine-readable configuration; the project DB will hold richer acquisition/research records; Markdown remains the human-readable data dictionary and durable project knowledge.
- Source acquisition, source validation, source selection, approval and application are distinct operations. A successful download is not proof of valid data and must not automatically update game data.
- Preserve source IDs and crosswalk IDs as stable identifiers across configuration and project records.

## Game-data scope

WP1.5 selected 41 fields. The canonical schema currently separates scalar `current_statistics` from structured `selected_game_data`. The game DB target should contain only selected game-facing values and their game-relevant reference periods; source metadata and source observations belong in the project DB. The final field dictionary, units, null semantics, source mappings and validation definitions remain Markdown documents indexed from the data documentation area.

Missing values must not be represented as zero. SQL NULL is explicit and must distinguish unavailable from not applicable. Do not infer values or silently substitute sources. Historical source observations are project-side and subject to the two-version retention rule; the game DB remains current/selected game data unless the owner separately changes scope.

## Existing data and safeguards

- Persistent `game_id` is the internal identity; source IDs, display names and ISO codes are not identity fallbacks.
- Existing country identity, names, regions, attributes, geometry, flags, selected data, statistics, review proposals and provenance must be inventoried before database separation.
- Migration 003 added statistic and selected-data provenance. Migration 004 added application approvals/events. These require explicit disposition; do not simply drop columns/tables.
- The existing approval gate and transactional/idempotent application behavior must be preserved. Cross-database recovery/reconciliation is a design requirement.
- Raw snapshots, manifests, derived PDF text and reports currently have established paths and tracking behavior. Preserve existing files until the approved retention migration inventories and safely disposes of them.
- Do not broadly stage files or delete directories. Preserve unrelated working-tree changes and generated reports.

## Completed and in-progress work

- WP1.1–WP1.4 database foundations, identity, metadata/geometry and review-domain work were owner-validated.
- WP1.5 is in progress. UN WPP population/demographic data were applied for fields 1, 2, 6, 12, 13 and 14. WDI and IMF WEO acquisition/coverage/comparability work has been assessed; ICASEES Central African Republic national accounts were acquired and assessed. Do not infer that assessed sources have been imported or approved.
- Shared PDF text extraction is implemented and owner-validated.
- The 41-field source-selection policy is established; do not change it as part of database separation.

Use the [data-source index](data-sources/README.md), provider assessments and [implementation logs](implementation/README.md) for exact evidence, reports, commands and validation outputs. This context guide intentionally avoids duplicating those details.

## Working and validation protocol

- Work on `work/compiler-hardening` unless the owner explicitly changes the target.
- The owner runs commands and validation locally and supplies terminal output. Do not claim local validation based on GitHub inspection or code changes.
- Keep changes scoped; never stage everything or overwrite unrelated local artifacts.
- Use Fish-compatible shell commands in operator instructions.
- Every implementation step updates its related Markdown documentation and indexes in the same step.
- Separate facts, evidence and hypotheses. Do not claim a task is complete until the owner supplies the required validation output.
