# Project context — TownCountryAsset

**Purpose:** Orientation and durable working context for developers and future ChatGPT sessions. This is a navigation and invariants document, not a replacement for the detailed architecture, feature, source-assessment or implementation records.
**Last reviewed:** 2026-11-23.

## Start here

1. [Documentation index](README.md) — subject-area indexes and documentation rules.
2. [Architecture index](architecture/README.md) — stable system contracts.
3. [Data-store separation plan](architecture/data-store-separation-plan.md) — approved two-database architecture and two-version retention contract; implementation status is tracked in the implementation log.
4. [Data-source index](data-sources/README.md) — providers, acquisition, validation, source selection and comparability.
5. [WP1.5 remaining acquisition plan](data-sources/wp1-5-remaining-acquisition-plan.md) — completed WPP/WDI field applications, outstanding source groups and next acquisition sequence.
6. [Implementation index](implementation/README.md) — implementation and owner-run validation history.
7. [Roadmap index](roadmap/README.md) — feature plans and work packages.
8. [Feature documentation standard](feature-documentation-standard.md) — required structure for new work.

## Architecture at the current checkout

The project has two distinct SQLite stores:

- **Game/canonical DB:** `data/canonical/town_country_asset.sqlite`, retaining the established path and schema-v4 migration history. This is the database used for the canonical/game-facing data and existing application workflows.
- **Project source/research DB:** `data/project/project_data.sqlite`, with its own connection and migration path. It holds source organisations and catalogue records, typed source URLs, dataset and acquisition-stream definitions, acquisition/artifact provenance, and the project-side records introduced by the separation stages.

The Project DB foundation, source/dataset catalogue registration, manifest auditing and acquisition provenance registration have been implemented and owner-validated. Subsequent source-specific acquisition and semantic-assessment work is also recorded in the implementation log. This does **not** mean the full separation is finished: migration/disposition of all legacy source/research/governance data, complete source-observation and crosswalk domains, cross-database application reconciliation, and the complete retention promotion/cleanup lifecycle remain governed by their own stages and acceptance criteria.

See [canonical database architecture](architecture/canonical-database.md), [data-store separation plan](architecture/data-store-separation-plan.md), and the [implementation index](implementation/README.md). Do not claim the entire legacy canonical schema has already been reduced to a pure Game DB.

## Source-version retention invariant

The target project DB retains exactly the **two latest successful acquired versions per stable source dataset/acquisition stream**. A version may be a multi-file publication bundle or a complete paginated API capture. The stream is keyed by stable source and dataset/download/API IDs, not by a release year.

A candidate is eligible only after complete acquisition and required validation. On successful promotion, retain the newest two and delete older version-specific database rows and files together, including snapshots, manifests, PDF text derivatives, normalized observations and version-specific reports. Failed or incomplete acquisitions must not evict either valid retained version. Stable source catalogue entries, typed URL records, dataset definitions, field mappings and crosswalk definitions remain.

The architecture contract is in the [separation plan](architecture/data-store-separation-plan.md). Do not assume the complete two-version promotion and filesystem cleanup lifecycle is active merely because catalogue/provenance registration exists.

## Data and source policy

- `config/data_sources.json` is the central source identity/configuration registry and bootstrap.
- `config/source_selection.json` is the approved field-level source-selection policy.
- `data/manual/source_overrides.json` contains explicit manual overrides.
- Do not change source priorities, fallback rules, mixture policy or latest-validated semantics without a separate review and explicit approval.
- JSON is machine-readable configuration; the Project DB holds structured acquisition/research records; Markdown remains the human-readable data dictionary and durable project knowledge.
- Source acquisition, source validation, source selection, approval and application are distinct operations. A successful download or Project DB provenance registration is not proof of valid data and must not automatically update game data.
- Preserve source IDs and crosswalk IDs as stable identifiers across configuration and project records.

## Game-data scope

WP1.5 contains 41 owner-confirmed fields. The canonical schema distinguishes scalar `current_statistics` from structured `selected_game_data`. Source metadata, source observations and acquisition history belong on the project/research side; the Game DB should retain only selected game-facing values and the reference period needed by the game.

As of 2026-11-23:
- UN WPP fields 1, 2, 6, 12, 13 and 14 have been acquired and applied.
- World Bank WDI fields 3, 33 and 34 have been acquired, validated and applied. The 2026-11-23 application contains 561 scalar observations across 187 mapped entities.
- IMF WEO fields 15, 16, 18, 20 and 21 have a captured October 2026 release and substantial coverage/comparability assessment, but are not to be described as applied by this record.
- The remaining 27 fields still require primary-source acquisition/processing. See [WP1.5 remaining data acquisition plan](data-sources/wp1-5-remaining-acquisition-plan.md) for the source-by-source inventory and recommended sequence.

Missing values must not be represented as zero. SQL NULL is explicit and must distinguish unavailable from not applicable. Do not infer values or silently substitute sources. Historical source observations are project-side and subject to the two-version retention rule; the Game DB remains current/selected game data unless the owner separately changes scope.

## Existing data and safeguards

- Persistent `game_id` is the internal identity; source IDs, display names and ISO codes are not identity fallbacks.
- Preserve country identity, names, regions, attributes, geometry, flags, selected data, statistics, review proposals and provenance according to their approved database disposition.
- Migration 003 added statistic and selected-data provenance in the earlier canonical schema; migration 004 added application approvals/events. These historical contracts require explicit disposition; do not simply drop columns/tables.
- The existing fingerprinted approval gate and transactional/idempotent application behavior must be preserved. Cross-database recovery/reconciliation is a design requirement.
- Raw snapshots, manifests, derived PDF text and reports have established paths and tracking behavior. Preserve existing files until the approved retention migration inventories and safely disposes of them.
- Do not broadly stage files or delete directories. Preserve unrelated working-tree changes and generated reports.

## Completed and in-progress work

- WP1.1–WP1.4 database foundations, identity, metadata/geometry and review-domain work were owner-validated.
- WP1.5 WPP and WDI field applications listed above are complete and locally verified. The October 2026 IMF WEO release is captured and assessed but is explicitly not ready for canonical application: field-definition, country-identity and country-year status gates remain. Close those gates before any WEO candidate can proceed through guarded application. ILOSTAT field 22 is the first new primary-source acquisition; its ICLS13/ICLS19 series candidates and acquisition requirements are documented separately. The 41-field source-selection policy remains unchanged. See [WP1.5 remaining data acquisition plan](data-sources/wp1-5-remaining-acquisition-plan.md) and [ILOSTAT acquisition research](data-sources/ilostat-labour-force-acquisition.md).
- Shared PDF text extraction is implemented and owner-validated.
- Project DB catalogue and acquisition-provenance stages have been implemented and owner-validated; see the [implementation index](implementation/README.md) for exact stage boundaries and outstanding work.

Use the [data-source index](data-sources/README.md), provider assessments and [implementation logs](implementation/README.md) for exact evidence, reports, commands and validation outputs. This context guide intentionally avoids duplicating those details.

## Working and validation protocol

- Current work is on `work/wp1-5-wdi-import`; use the branch/worktree explicitly selected for the task rather than assuming the historical default branch.
- The owner runs commands and validation locally and supplies terminal output. Do not claim local validation based on GitHub inspection or code changes.
- Keep changes scoped; never stage everything or overwrite unrelated local artifacts.
- Use Fish-compatible shell commands in operator instructions.
- Every implementation step updates its related Markdown documentation and indexes in the same step.
- Separate facts, evidence and hypotheses. Do not claim a task is complete until the owner supplies the required validation output.
