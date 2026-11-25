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
