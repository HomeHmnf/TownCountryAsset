# Data refresh implementation log

**Scope:** TownCountryAsset fetches online data and prepares game-ready candidate assets. Updating TownCountryGame is explicitly out of scope.

## Step 1 — Environment configuration and CLI contract

**Status:** Completed and locally validated.

Added `.env.example` with source URLs, fetched-data folders, candidate/approved output folders, report folder, compiler configuration paths, feature toggles, and HTTP timeout. Added `docs/cli-tool.md` describing the one-command interface, output/report behavior, and safety boundaries.

Design decisions captured:
- Local `.env` is not committed; `.env.example` is the shareable template.
- Process environment variables override values from `.env`.
- Candidate output is distinct from approved output.
- ISO matches remain proposals; the identity registry is persistent and must never be regenerated automatically.
- This repository does not modify the game repository.

## Step 2 — Environment-driven orchestration CLI

**Status:** Completed and locally validated.

Added `tools/run_data_pipeline.py` with:
- `.env` parsing without a new dependency; existing process environment values take precedence.
- Configurable source URLs, fetched-data folders, ISO evidence folders, candidate/approved output paths, report paths, generation settings, registry path, toggles, and network timeout.
- Natural Earth HTTPS download, ZIP-signature check, timestamped immutable archive, SHA-256 and provenance metadata.
- Orchestration of ISO proposal refresh, Natural Earth compilation with the persistent registry, optional SVG generation, generated-asset audit, identity-registry audit, and comparison to the approved snapshot.
- Markdown and JSON run summaries with per-stage status, command output, failure details, duration, and source checksum.
- Non-zero exit on failed stages; no automatic promotion to approved data and no writes to TownCountryGame.
- Pre-flight configuration validation and failure reporting for configuration errors.

Added `tests/test_run_data_pipeline.py` for environment precedence, boolean parsing, archive validation/provenance, and summary reporting. Added `.env` ignore rules and documented the CLI.

Safety detail: the implementation records the actual source URL, retrieval timestamp and hash, but leaves the release version null unless verified upstream metadata is available.

## Phase 3 — Fix the failed source download default

- Local validation confirmed all 61 tests passed and both CLI help commands worked at that point.
- The first online run failed before later stages because the legacy Natural Earth website download URL returned HTTP 500.
- Updated the CLI default and `.env.example` to use Natural Earth's S3 distribution endpoint: `https://naturalearth.s3.amazonaws.com/50m_cultural/ne_50m_admin_0_countries.zip`.
- The local `.env` overrides the default and was updated before the successful complete run.

## Phase 4 — Correct identity audit invocation

- The first full online run successfully fetched Natural Earth, refreshed ISO proposals, compiled 242 features, generated 726 SVGs, and passed the generated-asset audit.
- The run then failed because the pipeline passed an unsupported `--source-data` option to `audit_country_identity_registry.py`. That audit accepts `--registry` and `--output`.
- Updated orchestration to use supported options and write a read-only review report to `reports/data-refresh/country-identity-review.md`.
- No registry content was changed, no ISO proposals were approved, and no candidate output was promoted during the failed run.

## Phase 5 — Isolated candidate build and guarded publication

- The pipeline compiles and generates SVGs in a temporary sibling directory instead of writing directly into `TCA_GAME_DATA_OUTPUT_DIR`.
- Asset audits, identity-registry review, and approved-snapshot comparison run against that isolated candidate.
- Only after every required stage succeeds does the pipeline publish the candidate directory. If publication fails, it attempts to restore the previous candidate; failed stages clean up temporary output and leave the previous candidate untouched.
- Added tests for replacing a candidate on success and preserving the known-good candidate when publication fails.
- Updated the CLI documentation and README to explain the isolation/publication boundary.

## Phase 6 — Make snapshot comparison reports accurate

- The approved snapshot predates compiler metadata fields for source schema and build-input fingerprints. Missing legacy metadata is reported as “not comparable” rather than a misleading schema/configuration change.
- The comparison CLI accepts a logical candidate display path so reports identify `generated/town_country_asset_candidate`, not the temporary staging directory used during validation. The comparison still reads the isolated staging files.
- Added regression coverage for legacy snapshots without comparison metadata and for the logical candidate path.

## Phase 7 — Country identity and metadata review

**Status:** In progress; read-only audit hardening pushed for local validation.

Goal: improve the quality and auditability of the 242 persistent identity records without changing stable IDs or silently treating proposals as approved.

Planned work:
1. Inspect the current identity registry schema, compiler expectations, ISO proposal generator, and audits before changing any data model.
2. Produce a review artifact that groups records needing ISO review, entity-type classification, and Persian localization, preserving a clear source/evidence trail for each proposed value.
3. Verify ISO alpha-2 and alpha-3 candidates against the captured reference dataset; keep exact matches, explicit variants, ambiguous cases, and no-match cases distinguishable. A match is evidence, not automatic approval.
4. Explicitly identify features for which an ISO code may legitimately not apply. Do not invent codes; require a documented rationale and source for exceptions.
5. Define controlled entity-type values and validation rules based on the actual feature set and source attributes. Keep uncertain classifications unreviewed.
6. Define a source-backed Persian-name workflow; do not machine-invent or silently transliterate names as verified localization.
7. Add read-only audits and tests for proposal/evidence completeness, invalid codes, unsupported statuses, and preservation of all existing `game_id` values.
8. Document this phase and its local validation results before moving to any approval workflow.

### Phase 7b — ISO proposal evidence review

**Status:** Completed and locally validated on 2026-10-22.

Implemented `tools/audit_iso_proposal_evidence.py` to compare the saved proposal table with freshly computed proposals from the persistent registry and captured ISO reference. It checks registry/proposal coverage, duplicate or stale `game_id` rows, edited/stale candidate fields, reference code-pair and label consistency, malformed candidate pairs, and duplicate alpha-2/alpha-3 proposals across distinct records. It writes a Markdown report and exits non-zero when issues are found. It does not modify the registry or approve any assignment.

Added `tests/test_iso_proposal_evidence_audit.py` for clean evidence, missing/stale/duplicate rows, edited code candidates, and cross-record code conflicts. Local validation: `uv run pytest -v` — **71 passed**; the saved proposal/reference/registry audit reported **0 consistency issues** across 242 registry IDs, 249 reference rows, and 242 proposal rows (234 candidate code pairs). `git diff --check` passed and the working tree was clean.

Before applying any candidate to the registry:
- Treat the captured ISO CSV as a third-party reference distribution, not an ISO-hosted authoritative export; retain its URL, retrieval date, and checksums in review evidence.
- Triage the 234 current candidates into exact-name matches and explicit variants. Variants involving entity scope or political/status semantics (including Holy See/Vatican, Taiwan, Saint Martin, South Georgia, and territory labels) require explicit review rather than bulk acceptance.
- Investigate the eight unmatched records individually. Do not infer codes from Natural Earth source IDs or current registry alpha-3 fields; document when ISO 3166-1 is not applicable and why.
- Add a read-only evidence audit that compares proposal rows to the captured reference and persistent game ID set, detects missing/stale/duplicate proposal rows, and reports proposed code conflicts without writing to the registry.
- Preserve every existing `game_id`; do not populate `alpha2`, change assignment statuses, approve records, or modify the approved snapshot/game repository during evidence-audit implementation.
- Record local tests and report counts before any human-reviewed registry update workflow is designed.
### Phase 7c — Controlled entity-classification vocabulary and worksheet

**Status:** Implemented; local validation pending.

Added `config/entity_types.json` as a controlled, explicitly provisional vocabulary: `sovereign_state`, `dependent_territory`, `special_administrative_region`, `disputed_or_partially_recognized_entity`, `geographic_territory`, `other_administrative_entity`, and `unreviewed`. Definitions specify the kind of source evidence and policy decision required. These categories are a review vocabulary, not a geopolitical adjudication.

Added `tools/audit_entity_classification.py` to create a record-level review worksheet using persistent registry IDs and the saved ISO proposal table. It reports controlled-type distribution, ISO match context, evidence expectations, missing/stale proposal rows, and invalid type values. It is read-only and does not assign classifications or mutate any registry, ISO assignment, generated asset, approved snapshot, or game-repository file.

Added `tests/test_entity_classification_review.py` for stable-ID preservation, keeping unreviewed values unaltered, invalid types, missing/stale proposal rows, and report safeguards.

Important schema finding: the current registry stores `entity_type` but does not have a separate entity-classification review status or evidence record. A non-`unreviewed` type must therefore not be treated as verified until the evidence model is designed. All 242 existing classifications remain `unreviewed`; this phase intentionally does not populate them.

### Phase 7a — Read-only ISO metadata validation

- Extended `tools/audit_country_identity_registry.py` to validate uppercase ISO alpha-2/alpha-3 syntax, detect duplicate code assignments across distinct `game_id` records, and flag unsupported record/ISO/localization workflow statuses.
- Added review counts and safeguards to the Markdown report. Missing ISO values remain review items rather than errors by themselves, because some features may legitimately have no applicable code.
- Added regression tests for malformed codes, duplicate assignments, unsupported statuses, and read-only behavior.
- This is a syntax/consistency audit only: it does not prove that a code belongs to an entity, approve assignments, modify registry records, or change stable IDs.
- Local validation completed on 2026-10-22: `uv run pytest -v` — **67 passed**. The read-only registry audit reported 242 records, 242 unique non-empty `game_id` values, zero structural issues, zero malformed ISO codes, and zero duplicate ISO assignments. All 242 records remain review rows because their status, entity type, ISO assignment status, or Persian localization is still unreviewed. This result validates structure, not semantic correctness of any code.

Safety constraints:
- Do not regenerate, rename, or replace persistent `game_id` values.
- Do not automatically approve ISO assignments, entity types, or Persian names.
- Do not edit the approved asset snapshot or TownCountryGame as part of this phase.
- Missing codes are not inherently errors when no code applies; exceptions must be evidence-backed and documented.
- Preserve raw source snapshots and provenance for reproducibility. Never commit local `.env`.

### Phase 7d — Live Persian localization source and refresh workflow

**Status:** Implemented; local validation pending.

Added `TCA_PERSIAN_LABEL_SOURCE_URL` to the environment-driven configuration (default: Wikidata SPARQL endpoint), plus `TCA_PERSIAN_DATA_DIR`, `TCA_PERSIAN_LOCALIZATION_REPORT`, and `TCA_RUN_PERSIAN_LOCALIZATION`. These settings are listed in `.env.example` and `--help-config`; local `.env` values and process-environment precedence follow the existing pipeline behavior.

Added `tools/refresh_persian_localization.py`. On each normal pipeline run, it queries the configured endpoint for the current Persian (`fa`) labels of QIDs explicitly present in Natural Earth's `WIKIDATAID` field. It joins those source IDs to persistent registry records through `current_source_id`; names, ISO codes, row order, and fuzzy matching are not used to infer Wikidata identity. The refresh preserves a timestamped raw response, a timestamped candidate JSON snapshot, source URL/retrieval timestamp/SHA-256/size provenance, and a latest Markdown review worksheet. Missing QIDs and missing labels are reported distinctly.

All labels remain unreviewed candidates. The script never updates the identity registry, candidate game assets, approved snapshot, or TownCountryGame. By default, a localization refresh failure fails the overall pipeline before candidate publication; `TCA_RUN_PERSIAN_LOCALIZATION=false` is available as an explicit opt-out. The configured endpoint can be changed without editing code.

Added tests for source-field mapping, SPARQL query construction and response parsing, stable-ID preservation, snapshot provenance, and review-only behavior. Local validation is pending; do not treat this phase as validated until the owner runs the test suite and CLI checks.

## Phase 8 — Country flag assets and identity coverage

**Status:** Planned; documentation-first stage.

**Goal:** Add reproducible, source-backed flag assets for the complete persistent country/entity identity registry, without changing stable IDs or silently adjudicating disputed political representations.

### Agreed design

1. Use the MIT-licensed `lipis/flag-icons` SVG collection as the initial flag asset source, subject to verifying the selected revision's license and source layout during implementation. Pin the source to an explicit Git ref/commit for reproducible refreshes rather than relying on a moving branch alone.
2. Add environment settings to `.env.example` for the flag source URL/ref, raw source cache, generated flag output directory, mapping configuration, review report, refresh toggle, and HTTP timeout. Local `.env` remains untracked.
3. Add a dedicated, version-controlled mapping file that maps persistent `game_id` values to reviewed source flag identifiers. Do not derive the mapping from row order, display names, or current game data. ISO alpha-2 codes may identify source files only when their applicability and intended flag representation have been reviewed.
4. Generate deterministic asset filenames keyed by `game_id`, so downstream consumers do not depend on source naming conventions or mutable country names.
5. Preserve source revision, retrieval time, source URL, SHA-256 checksums, and license/attribution information. Validate downloaded files and reject missing, empty, malformed, duplicate, or unexpected assets.
6. Add a read-only mapping/asset audit that checks every registry `game_id` has exactly one reviewed mapping and exactly one generated flag, detects mappings to unknown IDs and source identifiers, and reports unresolved political/entity cases explicitly.
7. Integrate refresh, generation, and audit into the existing isolated candidate pipeline. A required-stage failure must preserve the previous candidate. Never write to TownCountryGame or promote the approved snapshot automatically.
8. Add tests for coverage, duplicate mappings, unknown IDs, unresolved mappings, malformed/missing assets, source provenance, deterministic filenames, environment precedence, and failure-safe pipeline publication.
9. Update the CLI documentation, README, and this implementation log as the feature progresses. Validate locally before marking each implementation stage complete.

### Policy and safety constraints

- The persistent identity registry remains the single source of truth for the set of `game_id` values; flag mappings are a separate explicit reviewed relationship.
- A flag choice is a representation decision, not something to infer automatically from a name or ISO match. Disputed territories, special administrative regions, and entities with multiple plausible representations must remain unresolved until an explicit decision is recorded.
- Do not use a generic fallback flag to disguise missing coverage. The audit must fail when required mappings or assets are absent or ambiguous.
- Do not regenerate or change any `game_id`, approve ISO proposals, edit the approved snapshot, or modify TownCountryGame as part of this feature.
- Source refresh must be reproducible and license-aware; document upstream attribution and preserve provenance with the assets.

### Stage 8a — Configuration and mapping contract

**Status:** Implemented and focused local validation passed on 2026-10-22.

Added the following flag settings to `.env.example` and the pipeline configuration defaults:
- `TCA_FLAG_SOURCE_URL`
- `TCA_FLAG_SOURCE_REF`
- `TCA_FLAG_SOURCE_DIR`
- `TCA_FLAG_ASSET_OUTPUT_DIR`
- `TCA_FLAG_MAPPING`
- `TCA_FLAG_REPORT`
- `TCA_FLAG_REFRESH_ENABLED`

The source defaults to the MIT-licensed `lipis/flag-icons` repository. The configuration and CLI documentation state that the resolved immutable source revision and provenance must be recorded during refresh. The environment template remains free of local machine-specific values.

Added `config/country_flag_mapping.json` with one explicit mapping record for each of the **242** persistent registry IDs. Every record currently has a null source flag code and `unreviewed` status by design. No flag assignments have been inferred or approved in this configuration stage. Records include fields for a decision note and evidence so later reviews can record why a particular source flag is appropriate.

Updated `docs/cli-tool.md` with the configuration contract. The mapping file is only a reviewed-decision input at this stage; flag download, mapping validation, SVG generation, and pipeline integration are not implemented yet.

### Stage 8b — Source refresh and provenance

**Status:** Implemented in the repository; local validation pending.

Added `tools/refresh_flag_source.py`. The standalone command:
- Reads the flag source URL/ref, cache directory, and HTTP timeout from environment configuration, preserving process-environment precedence over `.env`.
- Accepts only an HTTPS GitHub repository URL, resolves the configured ref to a full commit SHA via the GitHub API, and downloads the archive for that immutable commit.
- Rejects malformed ZIPs, unsafe traversal paths, symbolic links, archives without SVGs under a `flags/` directory, and archives without an MIT license file.
- Saves a commit-keyed archive, the source license text, a provenance JSON document, and a latest-snapshot pointer. Provenance records the configured ref, resolved commit, source/archive URLs, retrieval time, archive SHA-256 and size, license path/hash, and SVG count.
- Writes archive, license, and provenance files via temporary files and atomic replacement. It does not extract files, map identities, generate game assets, or modify approved/game data.

Added `tests/test_refresh_flag_source.py` covering GitHub URL validation, source archive/license checks, path traversal rejection, environment precedence, and malformed configuration. Added the standalone command's usage and current scope to `docs/cli-tool.md`.

**Validation:** Not yet run locally. Do not mark this stage validated until the owner runs the targeted test and CLI help/refresh checks. The main pipeline does not call this command yet.

### Planned implementation stages

- **8c — Flag asset generation and validation:** resolve reviewed mappings to SVGs, emit deterministic `game_id`-keyed assets, and audit file validity and complete coverage.
- **8d — Pipeline integration and documentation:** add isolated pipeline stages, reports, regression tests, and usage guidance; validate end-to-end before marking complete.

## Validation record

- Latest local validation reported by the owner on 2026-10-21: `uv run pytest -v` — **64 passed**.
- The online pipeline completed successfully with all nine stages successful: Natural Earth fetch, ISO proposal refresh, isolated candidate preparation, compilation, SVG generation, asset audit, identity registry audit, snapshot comparison, and candidate publication.
- Candidate contains 242 features and 726 SVG files. Identity audit found 242 records, 242 unique non-empty IDs, and zero structural issues.
- Comparison correctly reports source-schema and build-input comparisons as “not comparable” because metadata is missing from at least one snapshot; it does not claim false-positive changes.
- The owner committed raw Natural Earth/ISO evidence and refresh reports in commits `e4d3c42` and `8b143ef` on `work/compiler-hardening`. The approved snapshot and game repository were not modified.

Each phase is recorded here before implementation and updated with results. Any product/data-policy decision that cannot be safely inferred must be asked before proceeding.


- Additional local validation reported on 2026-10-22: `uv run pytest -v` — **71 passed**; `tools/audit_iso_proposal_evidence.py` reported **0 consistency issues**. Phase 7c implementation is now awaiting local validation.

### Stage 8c — Flag asset generation and coverage audit

**Status:** Implemented in the repository; local validation pending.

Added `tools/generate_country_flags.py` and `tests/test_generate_country_flags.py`. The generator:
- Reads the persistent identity registry, explicit flag mapping, cached source archive, and provenance written by `tools/refresh_flag_source.py`.
- Verifies the cached archive SHA-256 and resolved commit against its provenance before reading any source assets.
- Reads SVGs from the source collection's `flags/4x3/` directory, rejects unsafe archive paths and symbolic links, validates XML and the SVG root element, and rejects duplicate source codes.
- Requires one mapping per registry ID, rejects duplicate/unknown IDs and duplicate source-code assignments, and accepts only `status: "reviewed"` plus a lowercase two-letter source code. It does not infer a flag from names, ISO proposals, or row order.
- Produces deterministic `<game_id>.svg` filenames and a manifest with the source revision, retrieval metadata, archive/license hashes, and per-asset SHA-256/size.
- Writes a Markdown coverage report to `TCA_FLAG_REPORT`. It replaces the output directory only after full coverage and all assets validate; a failed audit returns non-zero and preserves the previous output.

Updated `docs/cli-tool.md` with source-refresh and generation/audit commands and the current review gate. The existing mapping still has 242 records with null source codes and `unreviewed` statuses, so a full generation run is expected to fail until explicit decisions are reviewed. This is intentional; no flags have been guessed or approved automatically.

**Local validation:** The owner ran `uv run pytest -v tests/test_generate_country_flags.py tests/test_refresh_flag_source.py`: **26 passed**. Both `tools/generate_country_flags.py --help` and `tools/refresh_flag_source.py --help` succeeded, and `git diff --check` reported no issues. The owner then pulled commit `1180bdb7be487841e91d6fe04fe1eba74ad290fa` containing Stage 8c.

**Safety boundary:** This stage does not modify the identity registry or approved snapshot and does not write to TownCountryGame.


### Stage 8d — Pipeline integration and operator documentation

**Status:** Implemented in the repository; local validation pending.

Integrated flag handling into `tools/run_data_pipeline.py`:
- When `TCA_FLAG_REFRESH_ENABLED=true`, refresh the configured flag source before candidate compilation and preserve immutable commit/archive/license provenance. A refresh failure is a required-stage failure.
- After compiling the candidate, run `tools/generate_country_flags.py` with the isolated staging directory as its output. Complete reviewed mappings produce `flags/<game_id>.svg` and a manifest as part of the candidate directory.
- Classify only explicitly unreviewed/missing mapping gaps as `review_required`; do not write partial flag assets and allow unrelated country-data refresh to continue. Source/provenance errors, malformed SVGs, duplicate or unknown mapping IDs, and other validation errors still fail the pipeline.
- Added `flag_report_contains_only_review_gaps` and unit coverage for the review gate and configuration defaults.
- Updated `.env.example`, README, and CLI documentation for the source refresh, mapping, generated assets, and temporary review gate.

**Important limitation:** The mapping currently has 242 unreviewed records. Until every registry ID has exactly one reviewed, valid mapping and the flag audit passes, the pipeline may publish candidate country data without a flag directory. This is an explicit temporary review gate, not a claim that flag coverage is complete. No assignment is inferred from names, source order, or unverified ISO proposals.

**Local validation:** Pending. Run the focused pipeline tests, all flag tests, full test suite, lint, architecture check, and diff check before marking Stage 8d complete.

**Safety boundary:** Candidate assets remain in TownCountryAsset. The approved snapshot, identity registry, and TownCountryGame are not modified by this integration.
