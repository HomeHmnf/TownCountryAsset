# WP1.5 remaining data acquisition plan

**Status:** next work package; source-by-source acquisition and field normalization remain incomplete  
**Reviewed:** 2026-11-23  
**Scope:** the remaining acquisition work for the 41 owner-confirmed WP1.5 fields  
**Authority:** `config/wp1_5_data_sources.json` and `config/data_sources.json`

## 1. Current position

WP1.5 has 41 selected fields. The following field groups have already been applied to the canonical database:

| Source | Fields | Status |
|---|---|---|
| UN WPP 2024 | 1, 2, 6, 12, 13, 14 | Acquired, crosswalked and applied; preserve estimate/projection status and the 2026 Medium selection |
| World Bank WDI area snapshot | 3, 33, 34 | Acquired, validated, approved and applied on 2026-11-23; 561 observations across 187 mapped entities |

The WDI application record is approval `wp15-wdi-20261123-688f77ac`, import ID 3, with 561 scalar observations and 187 crosswalk mappings. Its application and integrity checks were owner-verified. This closes the WP1.5 WDI area/density import task; do not repeat it.

The following evidence is acquired but is not equivalent to a completed WP1.5 field import:

- **IMF WEO October 2026:** the CSV and Database Appendix are captured and registered. Coverage, metadata and WDI comparability have been assessed for fields 15, 16, 18, 20 and 21. Country-level unit, vintage, identity and actual/estimate/projected distinctions remain relevant to preparing a source-specific normalized application.
- **World Bank WDI macro snapshots and ICP benchmark releases:** acquired as comparison and PPP/ICP evidence. They do not replace the selected IMF WEO source or authorize a source-selection change.
- **Bahrain, ICASEES, Guinea, Zimbabwe and Turkmenistan publications:** acquired for country-specific validation and reconciliation. These are supporting evidence, not complete global primary-source datasets for the selected WP1.5 fields.

Accordingly, **9 of 41 fields have been applied through the WPP and WDI work described above; the five IMF WEO fields have source captures and assessment work but are not recorded here as applied; the other 27 fields still need their selected primary-source acquisition/processing work.** A capture, Project DB provenance registration, assessment, approval and Game DB application are separate states.

## 2. Remaining primary-source acquisition inventory

The inventory below follows the current primary-source assignments. It does not authorize changing those assignments.

| Fields | Primary source | Remaining work | Main constraints / gate |
|---|---|---|---|
| 15, 16, 18, 20, 21 | IMF WEO | Complete source-specific normalization and field-level disposition, then prepare and apply the reviewed WEO artifact | Currency and scale, PPP basis, annual-average vs end-period inflation, unemployment definition, country identity, vintage and actual/estimate/projected status; licensing remains unclear |
| 22 | ILOSTAT | Discover and capture the exact labour-force series and required metadata | Age/sex scope, labour-force definition, period and country coverage |
| 41 | Köppen–Geiger | Acquire the chosen raster release and prepare reproducible country-area overlay | Raster resolution/period/scenario, project geometry version, area-weighting method and multiple classes per country |
| 42 | FAO FRA | Acquire the selected forest-area dataset | Choose forest area measure; preserve forest definition and reference year; distinguish forest area from tree cover |
| 45 | USGS MCS | Acquire the selected Mineral Commodity Summaries edition and define the fixed resource/metric catalogue | Commodity-level country coverage varies; missing rows do not mean absence; distinguish production, reserves and resources |
| 48 | Pew religion | Acquire the global religious-composition estimates | Seven broad categories, estimate year, coverage threshold and rounded-count guidance; licensing review |
| 51 | UNDP HDR | Acquire the selected HDI release/table | Use observation reference year, not report publication year; preserve series metadata |
| 52 | ITU | Acquire the selected Internet-use indicator | Exact indicator definition, denominator, country coverage and reference year |
| 54 | WHO GHED | Acquire the selected health-expenditure series | Decide canonical measure/denominator or retain distinct statistic keys; preserve dataset vintage and year |
| 55, 56 | World Bank PIP | Acquire poverty and Gini data for the chosen welfare concepts | Poverty line, welfare aggregate, survey year and original Gini scale; gaps between surveys remain missing |
| 57, 58, 65 | Official government sources | Build per-country evidence records for government system, structure and capital designation | No assumed global bulk source; cite official authority, effective date and rationale for each record |
| 62 | World Bank WGI | Acquire the political-stability series and metadata | Estimate vs 0–100 score must remain distinct; some underlying third-party inputs have redistribution restrictions |
| 66 | Official organization registers | Acquire/record membership status from each organization's official register | Organization-specific source, membership category/status and as-of/effective date |
| 67, 70, 71 | IISS Military Balance | Determine lawful access and acquire an edition only if rights permit | Proprietary subscription and redistribution terms; definitions for active/reserve personnel and force structure |
| 69 | SIPRI Milex | Confirm authorization and acquire the selected series if permitted | Commercial use requires authorization/licensing; retain year and edition |
| 73 | Global Carbon Project | Identify and acquire the exact per-capita series | Confirm territorial fossil CO₂ scope, methodology, denominator, country coverage and terms |
| 75, 76, 77, 78 | Energy Institute | Acquire the selected Statistical Review edition/workbook | Decide primary vs final energy, gross vs net electricity, crude oil/liquids scope and gas definition; preserve units and edition |
| 79 | Protected Planet | Resolve rights and permitted output shape before acquisition | Commercial use requires prior written permission and redistribution is restricted; decide aggregate-only vs site-level scope |
| 80, 81 | FAO AQUASTAT | Acquire the selected water-resources and water-stress series | Choose internal vs total renewable freshwater; preserve denominator, method and reporting year |

## 3. Recommended execution order

### Phase A — close the already-captured macro source

Finish the IMF WEO fields 15, 16, 18, 20 and 21 as a distinct source-normalization/application work package. Do not reacquire the October 2026 release. Reuse its immutable capture, Appendix, existing WDI/ICP comparison evidence and reviewed source mappings. The deliverable is a reproducible normalized artifact with explicit country crosswalk, units, reference periods and value statuses, followed by the existing guarded application workflow.

### Phase B — public statistical bulk sources

For each source, first verify the exact release, direct download/API endpoint, country identifiers, indicator definitions, observation years, update cadence, attribution and terms. Then capture immutable raw bytes and a manifest before building a source-specific parser/normalizer.

A practical grouping is:
1. ILOSTAT (field 22);
2. FAO FRA and FAO AQUASTAT (fields 42, 80, 81);
3. UNDP HDR and ITU (fields 51, 52);
4. WHO GHED (field 54);
5. World Bank PIP and WGI (fields 55, 56, 62), with rights review before reuse;
6. Energy Institute (fields 75–78);
7. USGS MCS and Global Carbon Project (fields 45, 73);
8. Pew religious composition (field 48).

This order is a work-planning sequence, not a source-priority change. Reorder only when exact provider availability, release timing or rights evidence justifies it.

### Phase C — spatial and per-country structured sources

- Field 41 requires a reproducible spatial processing pipeline, not a simple country-level CSV import.
- Fields 57, 58 and 65 require a country-by-country official evidence register and controlled classification vocabulary.
- Field 66 requires organization-specific membership captures with explicit as-of dates.

### Phase D — rights-gated sources

Do not begin bulk extraction or store redistributable normalized values for IISS, SIPRI or Protected Planet until the project has documented the applicable access and reuse permission. A publicly viewable page or subscription access is not by itself permission to redistribute data in the project or game.

## 4. Required acquisition lifecycle for every source

1. Confirm the selected source and exact dataset/series definition against the approved WP1.5 contract.
2. Verify provider endpoint, release/edition, country universe, stable source identifiers, reference periods, value-status semantics and update cadence.
3. Review attribution, licence and third-party restrictions at the dataset/indicator level.
4. Capture immutable raw bytes; record requested/final URL, retrieval timestamp, release, content type, byte count and SHA-256 in a tracked manifest. Keep raw files local-only under the project policy.
5. Register the acquisition and artifacts in the Project DB through the established manifest audit and registration workflow.
6. Build a source-specific adapter and explicit source-ID-to-`game_id` crosswalk. Never join by display name or infer ISO identity.
7. Produce coverage, missingness, duplicate, unit, period, status and anomaly reports. Keep unavailable and not-applicable distinct; never fill missing values with zero.
8. Prepare a normalized candidate artifact and use the existing fingerprinted approval/application path. Preserve candidate status unless a separate, explicit review decision changes it.
9. Verify row counts, crosswalk counts, provenance, idempotency, database integrity and foreign keys after application.

## 5. Out of scope for this phase

- Changing the 41 selected field IDs or their primary-source assignments.
- Changing source priorities, fallback rules, or manual overrides.
- Treating WDI comparison data, ICP benchmarks or country-specific research publications as replacements for the selected primary source.
- Guessing values, country mappings, observation years, status or units.
- Treating acquisition or Project DB registration as semantic approval or Game DB application.
- Implementing retention promotion or deleting historical snapshots as part of acquisition.

## 6. Immediate next work package

Start with **WP1.5-WEO-application** using the already captured October 2026 IMF WEO release. Once its five fields have a source-specific normalized artifact and complete coverage/status/identity review, proceed to **WP1.5-ILOSTAT-22** as the first new primary-source acquisition. This closes the gap between the already substantial macro assessment work and the remaining source groups without repeating completed WPP/WDI acquisition.
