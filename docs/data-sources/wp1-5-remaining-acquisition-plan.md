# WP1.5 remaining acquisition and application plan

**Status:** active field-by-field execution plan; governed by the [WP1.5 review, approval and database application workflow](wp1-5-review-approval-application-workflow.md).  
**Last reviewed:** 2026-11-25.

## Completion rule

The unit of completion is one WP1.5 field, not a provider batch or a diagnostic report. Work on fields sequentially. Do not start the next field until the current field has completed source verification/acquisition, normalization, semantic and identity review, approval, Project/source database registration, Game database application, independent verification of both databases, and its durable documentation record.

For every field, explicitly account for the full project identity universe. Each identity must have an evidence-backed disposition: imported value, unavailable, not applicable, excluded with rationale, or held for specific evidence. A field may be closed with documented gaps; it may not be called complete while identities or source rows are silently omitted. Never invent values, infer observation status, or treat an absent row as zero.

The Project/source database and Game database have separate responsibilities. Source bytes, manifests, releases, acquisition events and artifact provenance must be present and verified in the Project/source database. Approved game-facing observations, source references and import linkage must be present and verified in the Game database. A successful write to one database does not imply completion in the other.

## Completed

- UN WPP fields 1, 2, 6, 12, 13 and 14 were previously applied; their field-level evidence and database state remain subject to the final completeness reconciliation.
- World Bank WDI fields 3, 33 and 34 were applied and independently owner-verified on 2026-11-25: approval `wp1-5-wdi-20261125-regenerated` (actor `project-owner`), import ID `4`, 561 scalar observations and 187 crosswalk mappings. The approval ledger is `applied`; persisted rows, SQLite integrity and foreign keys were independently checked. See the [application record](world-bank-wdi-wp1-5-application.md).
- IMF WEO October 2026 source capture and Project DB acquisition registration (acquisition ID `5`) exist. This establishes source acquisition/provenance only; it does not close any WEO field.

## Execution order — one field at a time

1. **Field 15 — GDP (IMF WEO, indicator NGDPD).** First active field. Reuse the captured October 2026 WEO CSV and Database Appendix and existing Project DB acquisition ID 5. Verify the exact source artifacts and Project DB records; inspect the field-15 candidate rows, country identities, unit/currency/scale, annual reporting periods, latest-actual metadata and WDI comparison. Resolve every field-15 identity and semantic edge case. Create a field-15-only review/decision package and normalized candidate, validate and fingerprint it, obtain owner approval, then verify the source database and apply the approved candidate to the Game DB. Independently verify both databases and record all imported, held, excluded, unavailable and not-applicable cases before closing field 15.
2. **Field 16 — GDP per capita (IMF WEO, NGDPDPC).** Start only after field 15 is closed. Explicitly review denominator population universe, currency/scale, period and status.
3. **Field 18 — GDP PPP (IMF WEO, PPPGDP).** Start only after field 16 is closed. Resolve PPP benchmark/factor construction and status metadata without inference.
4. **Field 20 — Inflation (IMF WEO, PCPIPCH).** Start only after field 18 is closed. Resolve annual-average versus end-period and calendar/fiscal reporting periods.
5. **Field 21 — Unemployment (IMF WEO, LUR).** Start only after field 20 is closed. Resolve unit, labour-force population, definition, reference period and country-specific comparability; preserve settled Bahrain findings unless new evidence justifies reopening.
6. **Field 22 — Labour force (ILOSTAT).** Inspect existing captures and Project DB records first; acquire immutable bytes only if the required source data are absent or invalid. Confirm indicator, age/sex scope, unit, annual aggregation, status and coverage.
7. **All other contracted fields.** Continue in the order recorded in `config/wp1_5_data_sources.json`, one field at a time. Where a provider acquisition covers multiple fields, register the acquisition once, but keep each field's review, approval, application and closure distinct.

## Per-field closeout checklist

- [ ] Primary source and exact indicator/dataset definition confirmed against the field contract.
- [ ] Exact release/vintage and immutable source bytes verified; manifest includes URL, retrieval date/time precision, release, byte count and SHA-256.
- [ ] Source acquisition and all relevant artifacts registered and independently verified in the Project/source database.
- [ ] Candidate normalized with explicit provider IDs, persistent `game_id` crosswalk, unit/scale, reference period, status and methodology.
- [ ] Full identity/coverage register accounts for every expected game identity and every source row; unresolved cases remain explicit.
- [ ] Field-specific semantic review and linked edge-case decisions complete; no blank decisions treated as approval.
- [ ] Exact candidate and dependencies validated and fingerprinted; owner approval recorded against those hashes.
- [ ] Approved observations applied transactionally to the Game DB; no source policy change or release promotion occurs implicitly.
- [ ] Independent read-only verification confirms expected Game DB values, source references, import linkage, counts, duplicates/conflicts, SQLite integrity and foreign keys.
- [ ] Independent Project DB verification confirms acquisition/artifact identities, hashes, registration state and database integrity/foreign keys.
- [ ] Field-specific implementation record and this plan updated with evidence, counts, gaps, approval ID, import/application IDs and commit.
- [ ] Only then mark the field complete and begin the next field.

## Current gate

**Field 15 is next; it is not yet approved or applied.** Existing Stage 4C diagnostics and Stage 4E's multi-field package builder are supporting evidence/tooling, not field-15 approval. Adapt or invoke the review tooling in a field-15-only mode; do not approve or import fields 16, 18, 20 or 21 as part of the field-15 work. First inspect the local source files, Project DB acquisition ID 5 and existing candidate outputs read-only. Do not reacquire valid evidence.

The combined canonical Game DB remains the active target for this phase. Do not begin the future Game DB/Project DB separation cutover during this work; verify the existing Project/source database and combined Game DB independently under their current contracts.

### Field 15 audit update — 2026-11-25

The IMF WEO `NGDPD` source has 210 country/area series and 10,026 nonblank annual values. The existing canonical Game DB has 9,329 matching observations; matched values and compared metadata reconcile with zero mismatches and no extra database keys. The 697 absent source keys comprise 624 values across 12 aggregate/regional series, 41 Euro Area aggregate values (`G163`), and 32 West Bank and Gaza values (`WBG`, 1994–2025).

The 665 aggregate/regional values must be explicitly dispositioned as non-country series in the field-15 review package, rather than silently omitted. The 32 WBG values remain an identity-review hold. The canonical database contains a `PSE` ISO alpha-3 identity, but its ISO assignment is unverified; there is no `WBG` row in `country_sources`, no WBG historical observation, and no “West Bank” name match in `country_names`. Do not map WBG to PSE without authoritative evidence and an explicit decision.

Schema note for future audits: `countries` contains identity/ISO state but no name column; `country_names` stores names by `game_id`; `country_sources` stores provider crosswalk attributes (`dataset`, `source_id`, `is_current`, `import_id`). The earlier audit's attempted `countries.name` reference was invalid; the schema inspection established these actual columns. Both completed read-only integrity checks reported SQLite `ok` and zero foreign-key violations.

This evidence does not approve field 15 or authorize a write. The field-15-only identity and semantic review, full explicit disposition register, approval, dual-database verification and documentation remain outstanding. Field 16 remains blocked.

## Owner-run validation and evidence

The owner runs local tests and database commands. Record exact commands, counts, approval IDs, artifact fingerprints, Project DB acquisition/artifact IDs, Game DB import/application IDs, integrity results and commit references only after receiving the output. Repository documentation or code changes alone do not establish successful local acquisition or database application.


### Field 15 WBG identity evidence update — 2026-11-25

The 32 unmatched nonblank WBG.NGDPD.A values (1994–2025) now have additional authoritative context. The official October 2026 IMF WEO Database Appendix:
- lists West Bank and Gaza as an individual economy within Emerging and Developing Economies and Middle East and Central Asia (pages 6 and 8);
- defines the WEO use of “country/economy” to include some separately maintained territorial statistical entities that are not states under international law (page 3);
- identifies WBG as West Bank and Gaza in the country-data documentation, with Israeli new shekel, NSO historical data, latest actual annual data 2025, 2015 base year and SNA 2008 (page 14);
- notes that 2022–23 data previously excluded pending methodological adjustments are included again, while projections for 2024–29 are excluded due to uncertainty (page 19). This note is not an observation-level status classifier.

Official appendix: https://data.imf.org/-/media/iData/External-Storage/Documents/C4182C5C54794FC48892DE8F6C74FF82/en/October-2026-WEO-Database-Appendix.pdf

The existing project UN M49 snapshot explicitly matched the registry display name Palestine to M49 formal name State of Palestine (M49 275, ISO PS/PSE) using a reviewed name variant; alpha-3 agrees. The matched registry record is game_id=tc_50c420df8b2c4c6eaae47d795f9a1ea2, Natural Earth source ID PSX. M49 snapshot provenance is in reports/database/town_country_asset/identity/m49-current/; the registry PSE status remains unverified.

This makes that persistent identity a strong candidate for an IMF WBG crosswalk, but no direct IMF-to-M49 concordance is recorded. The owner must explicitly decide the mapping. Until then, all 32 values remain held for identity evidence: no aggregate exclusion, no inferred mapping, no country_sources write, no registry edit, and no Game DB write. The evidence and proposed target game_id must be included in the field-15 review register. Do not alter the PSE ISO verification state as a side effect.

Field 15 remains open; fields 16 onward remain blocked.


### Field 15 WBG crosswalk owner approval — 2026-11-25

The project owner approved the exact IMF-specific mapping: `imf_weo / WBG` → `tc_50c420df8b2c4c6eaae47d795f9a1ea2` (Palestine registry identity). It is recorded in `data/manual/source_crosswalks/imf_weo.json`, with the IMF October 2026 appendix evidence and the existing reviewed UN M49 name-variant reconciliation. Scope is limited to field 15 (`NGDPD`) in the current sequential pass. This does not alter the identity registry or PSE verification status, nor authorize the other WEO fields.

The candidate builder/importer will treat the crosswalk file as an exact hashed input. The field-15 candidate must contain the 32 WBG observations; the 13 aggregate series remain explicit non-country review exceptions. No DB write or approval has been performed.


### Field-15 implementation update — 2026-11-25

The owner-approved `imf_weo / WBG` → Palestine `game_id` crosswalk is now in `data/manual/source_crosswalks/imf_weo.json`, separate from the global identity registry. The IMF candidate builder accepts the crosswalk, hashes it into candidate metadata, and supports a field-15-only build. The approval importer verifies the crosswalk hash and includes the file as an application artifact dependency. The WEO–WDI review-package builder now accepts `--field-id 15` to avoid mixing fields in the review surface.

Regression tests were added for the mapping, field scoping, unsupported field IDs, and importer fingerprint checks; they remain unexecuted until the owner syncs and runs them locally. No local IMF candidate or field-15 review package has yet been generated; no database, approval or observation data has been written.

After syncing, build the field-15 candidate with:

```fish
uv run python -m tools.build_imf_weo_historical_candidate --field-id 15
```

Expected acceptance check: 9,361 observations (9,329 previously reconciled country observations plus 32 WBG values), only field 15, and all 13 aggregate series represented as identity exceptions. Verify rather than assume these counts.

Then build the field-scoped review package from the existing Stage 4C semantic matrix:

```fish
uv run python -m tools.build_imf_weo_wdi_review_package --input reports/sources/imf-wdi-semantic-disposition/20261107T145725Z/semantic_disposition_matrix.csv --field-id 15
```

Reconcile that package against the new candidate and crosswalk before entering review decisions. Field 15 remains open; fields 16 onward remain blocked.


### Field 15 aggregate dispositions and candidate build — 2026-11-25

The owner approved `excluded` for all 13 IMF aggregate and regional NGDPD series. The explicit register is:

`reports/sources/imf-weo-historical-candidate/20261125T152006Z/field_15_exclusion_register.csv`

It accounts for 665 populated annual source observations across 13 series. Twelve series have 52 populated years each; G163 (Euro Area) has 41 populated years, 1991–2031. The excluded source codes are G001, G110, G119, G163, G200, G205, G400, G505, G510, G603, G903, G998 and GX123. The register records source names, series codes, year coverage, latest-actual metadata, disposition and rationale.

The common rationale is that IMF regional, economic-group and global aggregates are outside the country-level game identity universe. They remain represented in source evidence and are excluded from country-level field 15 application. They are not country identities and must not be mapped to game IDs.

The field-15-only candidate was successfully built at:
`reports/sources/imf-weo-historical-candidate/20261125T152006Z/`

Verified candidate metadata:
- 9,361 NGDPD observations.
- 197 distinct game IDs.
- Year range 1980–2031.
- 13 identity exceptions, corresponding to the aggregate codes in the exclusion register.
- Source SHA-256: `a19b2bd65b050a91d593cb6bcfc77a303e6359e058f03c3c92cf5ad849cda74d`.
- Crosswalk SHA-256: `df72a50e9fd37cbc05088a074367be05e3e067194b932997f7e7ec95589f91a9`.
- Candidate observation SHA-256: `47d8e3ac053eb0842e632ba71aaca02dc76fe780d9665ee431ab775dfcb9f76d`.
- Candidate exception SHA-256: `b35a2984fd5704fa3c47fed01e067b9baed16e8c8785a1ca4218938c3d1c148e`.
- `database_written=false`; `approval_created=false`.

The 32 WBG observations are included under the owner-approved IMF-specific field-15 crosswalk and are not excluded as aggregates. The earlier WBG identity hold is superseded by that explicit owner decision.

**Current gate:** aggregate dispositions and candidate construction are complete. Field 15 is not yet approved or applied. The field-15 semantic review must still be reconciled against the candidate, crosswalk and exclusion register. Approval, application and independent verification of both databases remain outstanding. Field 16 remains blocked.
