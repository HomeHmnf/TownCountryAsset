# Feature: Country identity and geographic metadata hardening

> **Status:** Implemented; automated/local validation records are historical and latest local verification is pending after the most recent commits. Crosswalk review remains in progress.  
> **Owner/work package:** Country identity and Natural Earth compiler hardening  
> **Target branch:** `work/compiler-hardening`  
> **Last updated:** 2026-11-05

## Problem and motivation

Natural Earth source IDs, ISO 3166-1 codes, names and regions are distinct concepts. The compiler must not treat an administrative identifier as an ISO code, and regional exceptions must remain visible. The game also has legacy Persian catalogs, map labels, flags and quiz content whose representation choices may differ from Natural Earth.

## Goals

- Preserve stable internal asset IDs and generated geometry keys.
- Keep source identifiers separate from ISO identity.
- Make region classification explicit and report exceptions.
- Record reproducible source/configuration provenance.
- Detect source and generated-asset changes before publication.
- Produce a read-only, reviewable game-country crosswalk without rewriting game data.

## Non-goals

- No gameplay catalog or runtime identity changes before the asset contract and crosswalk are reviewed.
- No automatic ISO assignment or approval.
- No merging entities based on name similarity.
- No changes to Iran province/city content.
- No changes to TownCountryGame or save data.

## Scope and dependencies

- **Compiler and tools:** Natural Earth offline compiler, generated-asset audit, snapshot comparison and game-country crosswalk audit.
- **Configuration:** generation and region configuration, persistent country identity registry.
- **Inputs:** verified Natural Earth source ZIP and existing game JSON catalogs, flag translations and regional color-map data.
- **Consumers:** generated country assets and later reviewed game crosswalk.
- **Dependencies:** stable Natural Earth source schema, source archive provenance, and human review of identity/entity classifications.

## Design and decisions

### Source identity and ISO identity

- Keep the stable internal asset `id` based on the configured Natural Earth stable-ID field so geometry keys remain compatible.
- Treat `id`/source ID and `iso3` as separate concepts. Never fall back from an ISO field to `ADM0_A3` when populating `iso3`.
- Normalize Natural Earth sentinel values such as `-99` to null.
- The configured stable-ID field must exist in the source schema, and every feature must have a usable, unique value. Missing fields, sentinel IDs and duplicate IDs fail clearly; no feature-order fallback or automatic suffixing is allowed.
- Generated metadata and manifest record source field names, the stable-ID field, missing configured name/ISO fields, and SHA-256 fingerprints of generation and region configuration files.
- A syntactically valid three-letter string is not, by itself, proof of ISO validity.

### Region classification

- Use source continent/subregion attributes rather than splitting the combined `REGION_UN=Americas` value.
- Map Natural Earth subregions to the project's North America and South America groupings; include Central America and the Caribbean in North America for the current game grouping.
- Report exceptional records that do not fit configured mappings, including open-ocean records. Do not silently guess a region.

### Provenance and deterministic generation

- Preserve the source archive SHA-256 in the manifest.
- Record the actual Natural Earth release/version and retrieval date before publishing a release asset set.
- Keep builds deterministic and do not add generation timestamps to output JSON.
- Do not guess a release/date from generated files; the current release/version and retrieval-date fields remain null until confirmed from the acquisition record.

### Snapshot and crosswalk review

- Snapshot comparison reports source archive/schema/config changes, added/removed IDs, possible rekeys inferred from unique ISO candidates, metadata changes and per-feature geometry changes. These are review signals, not approved identity changes.
- Crosswalk candidates are derived only through exact normalized text bridged by the game's existing English-to-Persian flag translation. They are suggestions, not approved mappings.
- Report missing, ambiguous, duplicate and one-to-many candidates for human review.
- Do not rewrite game content or merge entities based on name similarity alone.

## Implementation plan and current evidence

### 1. Source identity and schema safeguards

**Status:** Implemented; prior local tests were reported. Latest commits still require owner-side revalidation.

- Regression coverage includes administrative IDs that differ from ISO codes and records without an applicable ISO candidate.
- Compiler tests cover missing/invalid/duplicate stable IDs and provenance fingerprints.

### 2. Region classification

**Status:** Implemented; prior local tests were reported.

- Region mapping is explicit and unmapped exceptions are reported.

### 3. Source provenance

**Status:** Source archive was verified locally; its SHA-256 is recorded in the generated manifest. Release/version and retrieval-date fields remain null pending acquisition evidence.

### 4. Regeneration, comparison and generated-data audit

**Status:** Regenerated locally and audit passed at the recorded earlier checkpoint; rerun after the latest source-schema and audit-tool commits.

- The owner previously ran the compiler against the verified ZIP and compiled 242 features.
- All three SVG profiles were generated: 726 SVG files total.
- `tools/audit_generated_assets.py` passed against generated data and the source ZIP before the new source-schema contract was added.
- `tools/compare_asset_snapshots.py` compares a known-good snapshot with a candidate and reports source archive/schema/config changes, added/removed IDs, possible rekeys, metadata changes and geometry changes.
- An earlier local run reported 18 tests passed before game-crosswalk audit tests were added. Do not treat this as validation of the latest code.

### 5. Game data crosswalk audit

**Status:** Read-only audit tool and tests committed; local report reviewed at summary level; no game data changed.

- `tools/audit_game_country_crosswalk.py` reads generated asset metadata and game JSON catalogs, color-map labels, map question answers/choices, flag tiers/translations, general-information country entries and existing aliases.
- It produces Markdown and JSON reports under `reports/country-crosswalk-audit/`.
- Latest previously reported local validation: `uv run pytest -v` passed 20 tests. The audit found 242 asset records, 241 regional catalog entries, 175 single-candidate country-catalog labels, 66 unmatched country-catalog labels and no ambiguous country-catalog labels.
- Latest reported regional catalog/color-map differences: America has catalog-only label `دومینیکن`; Africa has nine catalog-only labels: `اسواتینی`, `جزایر قناری`, `جزایر مایوت`, `جمهوری دموکراتیک عربی صحرا`, `جمهوری دموکراتیک کنگو`, `جمهوری کنگو`, `سبته`, `مادیرا` and `ملیلیه`. Asia and Europe have no catalog/color-map label differences.
- The report found zero question answers absent from their region's catalog. This is a structural consistency check, not proof that answers resolve to valid/selectable entities.
- Review the 66 unmatched catalog labels and proposed single-candidate IDs in small batches. Check source attributes, ISO assignment, region, and whether each game entry is a sovereign state, territory, dependency, constituent country or disputed entity.
- Resolve America/Africa color-map discrepancies separately.
- Preserve existing legacy catalog behavior until each discrepancy is reviewed.
- Keep Iran's province/city content separate from the Natural Earth country crosswalk.

## Data, provenance and compatibility

The Natural Earth source archive is intentionally not committed to this repository under the documented raw-data storage convention; use the verified local archive for regeneration. Preserve the source archive hash in the manifest. Do not infer release version or retrieval date without acquisition evidence.

Generated internal IDs continue to key geometry files. Existing GDScript interfaces, Persian UI, legacy SVG hit-testing and save data must remain compatible during migration.

## Safety and operational boundaries

- Compilation, asset audits, snapshot comparison and crosswalk audit are offline/read-only with respect to game catalogs and runtime data.
- Candidate identity links and possible rekeys are review evidence only.
- No game data is rewritten, no ISO assignment is approved and no runtime behavior is changed by this feature work.
- Keep this work on `work/compiler-hardening`; do not target `main` until reviewed.

## Validation and acceptance criteria

- [ ] Compiler tests cover missing/invalid/duplicate stable IDs and provenance fingerprints.
- [ ] Snapshot comparison tests cover added/removed IDs, possible rekeys, metadata changes and duplicate-ID rejection.
- [ ] Rerun compiler tests, generated-data audit, snapshot comparison and SVG generation against the latest commits.
- [ ] Every game crosswalk entry has a review status; unresolved or ambiguous mappings remain explicit.
- [ ] Existing GDScript interfaces, Persian UI, legacy SVG hit-testing and save data remain compatible.
- [ ] Owner supplies the latest local command output before this feature is marked locally validated.

Previously reported results are historical checkpoints only; they are not evidence that the latest branch state has passed local validation.

## Documentation and related records

- Area index: [Roadmap and feature documentation index](README.md)
- Documentation standard: [Feature documentation standard](../feature-documentation-standard.md)
- Architecture: [Country identity contract](../architecture/country-identity-contract.md)
- Implementation: [Data refresh implementation log](../implementation/data-refresh.md)
- Review: [Country crosswalk review](country-crosswalk-review.md) and [country crosswalk audit](country-crosswalk-audit.md)
- Project documentation index: [Documentation home](../README.md)

## Open questions and next steps

1. Re-run the compiler, generated-asset audit, snapshot comparison and complete test suite after pulling the latest commits.
2. Confirm the Natural Earth release/version and retrieval date from the acquisition record.
3. Review unmatched labels and candidate crosswalk entries in bounded batches.
4. Resolve the America/Africa catalog/color-map differences.
5. Do not begin runtime/catalog migration until the asset contract and crosswalk decisions are explicitly reviewed.
