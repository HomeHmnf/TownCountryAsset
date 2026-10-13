# Feature Work: Country Identity and Geographic Metadata Hardening

**Status:** Asset compiler and generated snapshot validated locally; crosswalk audit reviewed at summary level; explicit mapping review remains in progress.  
**Target branch:** `work/compiler-hardening`  
**Scope:** Offline Natural Earth compiler, generated asset contract, and later game crosswalk. Do not change gameplay catalogs or runtime identity semantics until the asset contract is reviewed.

## Why this work is needed

Natural Earth source IDs, ISO 3166-1 codes, names, and regions are distinct concepts. The compiler must not treat an administrative identifier as an ISO code, and regional exceptions must remain visible. The game also has legacy Persian catalogs, map labels, flags, and quiz content whose representation choices may differ from Natural Earth.

## Work items

### 1. Separate source identity from ISO identity
**Implementation status:** Implemented and locally tested.
- Keep the stable internal asset `id` based on the configured Natural Earth stable-ID field so geometry keys remain compatible.
- Treat `id`/source ID and `iso3` as separate concepts. Never fall back from an ISO field to `ADM0_A3` when populating `iso3`.
- Normalize Natural Earth sentinel values such as `-99` to null.
- Regression coverage includes administrative IDs that differ from ISO codes and records without an applicable ISO candidate.
- A syntactically valid three-letter string is not, by itself, proof of ISO validity.

### 2. Fix continent/region classification
**Implementation status:** Implemented and locally tested.
- Use the source's continent/subregion attributes rather than splitting the combined `REGION_UN=Americas` value.
- Map Natural Earth subregions to the project's North America and South America groupings; include Central America and the Caribbean in North America for the current game grouping.
- Report exceptional records that do not fit configured mappings, including open-ocean records. Do not silently guess a region.

### 3. Make source provenance reproducible
**Implementation status:** Source archive verified locally; its SHA-256 is recorded in the generated manifest. Release/version and retrieval-date fields remain null until confirmed from the acquisition record.
- Record the actual Natural Earth release/version and retrieval date before publishing a release asset set.
- Preserve the source archive SHA-256 in the manifest.
- Keep builds deterministic and do not add generation timestamps to output JSON.
- Do not guess a release/date from generated files.

### 4. Regenerate and audit generated data
**Implementation status:** Regenerated locally and audit passed.
- The user ran the compiler against the verified ZIP and compiled 242 features.
- `tools/audit_generated_assets.py` passed against the generated data and source ZIP.
- All three SVG profiles were generated: 726 SVG files total.
- Local test result: 18 tests passed before the game-crosswalk audit tests were added. Re-run the suite after pulling the latest audit-tool commits.
- Do not hand-edit generated metadata in a way that leaves geometry keys or checksums inconsistent.

### 5. Compare game data and prepare a reviewed crosswalk
**Implementation status:** Read-only audit tool and tests committed; local report reviewed at summary level; no game data changed.
- `tools/audit_game_country_crosswalk.py` reads the generated asset metadata and game JSON catalogs, color-map labels, map question answers/choices, flag tiers/translations, general-information country entries, and existing aliases.
- It produces Markdown and JSON reports under `reports/country-crosswalk-audit/`.
- Candidate links are derived only through exact normalized text bridged by the game's existing English-to-Persian flag translation. They are suggestions, not approved mappings.
- Report missing, ambiguous, duplicate, and one-to-many candidates for human review.
- Latest local validation: `uv run pytest -v` passed 20 tests; audit found 242 asset records, 241 regional catalog entries, 175 single-candidate country-catalog labels, 66 unmatched country-catalog labels, and no ambiguous country-catalog labels.
- Latest regional catalog/color-map differences: America has catalog-only label `دومینیکن`; Africa has nine catalog-only labels: `اسواتینی`, `جزایر قناری`, `جزایر مایوت`, `جمهوری دموکراتیک عربی صحرا`, `جمهوری دموکراتیک کنگو`, `جمهوری کنگو`, `سبته`, `مادیرا`, and `ملیلیه`. Asia and Europe have no catalog/color-map label differences.
- The report found zero question answers absent from their region's catalog; this is only a structural consistency check, not proof that the answers resolve to valid/selectable entities.
- Next: review the 66 unmatched catalog labels and all proposed single-candidate IDs in small batches, checking source attributes, ISO assignment, region, and whether each game entry is a sovereign state, territory, dependency, constituent country, or disputed entity. Resolve the America/Africa color-map discrepancies separately.
- Do not rewrite game content or merge entities based on name similarity alone.
- Preserve existing legacy catalog behavior until each discrepancy is reviewed.
- Keep Iran's province/city content separate from the Natural Earth country crosswalk.

## Acceptance criteria

- Internal/source IDs remain stable and continue to key generated geometry files.
- `iso3` contains only values from configured ISO candidate field(s), with sentinel values normalized to null; it is never populated from `ADM0_A3` as a fallback.
- Region mapping is explicit, tested, and unmapped exceptions are reported.
- The manifest records the source archive hash and, for release builds, the actual source version and retrieval date.
- Compiler tests, generated-data audit, and SVG generation pass before runtime/catalog changes.
- Every game crosswalk entry has a review status; unresolved or ambiguous mappings remain explicit.
- Existing GDScript interfaces, Persian UI, legacy SVG hit-testing, and save data remain compatible during migration.

## Current constraints

The Natural Earth source archive is intentionally not committed to this repository (`raw_data/` is ignored); use the verified local archive for regeneration. Do not infer a release version or retrieval date without the acquisition record. Keep this work on `work/compiler-hardening` and do not target `main` until reviewed.
