# Feature Work: Country Identity and Geographic Metadata Hardening

**Status:** In progress  
**Target branch:** `work/compiler-hardening`  
**Scope:** Offline Natural Earth compiler, generated asset contract, and later game crosswalk. Do not change gameplay catalogs or runtime identity semantics until the asset contract is reviewed.

## Why this work is needed

The current generated snapshot contains 242 records and unique internal IDs, but the `iso3` field can contain Natural Earth administrative identifiers because the compiler currently tries `ADM0_A3` before `ISO_A3`. These identifiers are not interchangeable with ISO 3166-1 alpha-3 codes. The generated region list also leaves records unmapped because the configured source field (`REGION_UN`) uses the combined value `Americas`, while the configuration only declares North and South America. The manifest currently permits missing source release and retrieval-date provenance.

## Work items

### 1. Separate source identity from ISO identity
**Implementation status:** Compiler/config changes committed; regression tests added, awaiting local test run and regenerated-data verification.
- Keep the stable internal `id` based on the configured Natural Earth stable-ID field so geometry keys remain compatible.
- Treat `id`/source ID and `iso3` as separate concepts. Never fall back from an ISO field to `ADM0_A3` when populating `iso3`.
- Normalize Natural Earth sentinel values such as `-99` to null.
- Add regression fixtures where the administrative ID and ISO code differ, including South Sudan (`ADM0_A3=SDS`, `ISO_A3=SSD`) and a record with no ISO code (for example, Kosovo).
- Document that a syntactically valid three-letter string is not, by itself, proof of ISO validity. Any future use of alternate fields must be supported by an explicit field-semantics review.

### 2. Fix continent/region classification
**Implementation status:** Compiler now maps configured subregions and emits a `region_audit` with unmapped IDs; regression coverage added. Existing generated files still need a reproducible rebuild.
- Use the source's continent/subregion attributes rather than trying to split the single `REGION_UN=Americas` value.
- Map Natural Earth `SUBREGION` values to the project's `North America` and `South America` groupings; include Caribbean and Central America in North America for the current continent-based game grouping.
- Identify and explicitly review exceptional records whose source subregion does not fit these mappings (notably `Seven seas (open ocean)` records). Do not silently guess a region.
- Add tests proving that ordinary Americas records receive a region and that unmapped exceptions are visible/auditable.

### 3. Make source provenance reproducible
**Implementation status:** Source archive has been verified locally and its checksum is part of the established workflow; release/version and retrieval-date fields remain null until confirmed from the acquisition record.
- Record the exact Natural Earth release/version and the date the source archive was retrieved in `config/generation.json` before publishing a regenerated asset set.
- Preserve the source archive SHA-256 in the manifest.
- Keep builds deterministic: do not add generation timestamps to output JSON.
- Do not guess a release/date from the current generated files; obtain these values from the actual source archive or acquisition record.

### 4. Regenerate and audit generated data
**Implementation status:** Source archive is available locally and verified. An automated structural/manifest audit has been added; regenerate the committed snapshot locally, run the audit against the exact ZIP, and review the report before publishing.
- Regenerate `countries.json`, geometry profiles, and manifest from the reviewed source archive after compiler/config changes.
- Verify unique internal IDs, geometry keys matching metadata IDs, ISO candidate behavior, region assignment, deterministic checksums, and manifest provenance.
- Do not hand-edit generated metadata in a way that leaves geometry keys or checksums inconsistent.

### 5. Build a game-data crosswalk (after the asset contract is stable)
- Compare asset identities/names/aliases against the Persian game catalogs, map labels, flags, and quiz answers.
- Keep a versioned, explicit crosswalk between asset IDs and legacy game catalog keys.
- Report missing, ambiguous, duplicate, and one-to-many matches for human review.
- Do not rewrite game content or merge entities based on name similarity alone.
- Preserve existing legacy catalog behavior during migration until each discrepancy is reviewed.

## Acceptance criteria

- Internal/source IDs remain stable and continue to key the generated geometry files.
- `iso3` contains only values taken from the configured ISO field(s), with sentinel values normalized to null; it is never populated from `ADM0_A3` as a fallback.
- Region mapping is explicit, tested, and any intentional unmapped exceptions are reported rather than hidden.
- The manifest records source archive hash and, for release builds, the actual source version and retrieval date.
- Compiler tests and generated-data audits pass before game runtime/catalog changes are made.

## Current constraints

The Natural Earth source archive is intentionally not committed to this repository (`raw_data/` is ignored); use the verified local archive for regeneration. Do not infer a release version or retrieval date without the acquisition record. Keep this work on `work/compiler-hardening` and do not target `main` until reviewed.
