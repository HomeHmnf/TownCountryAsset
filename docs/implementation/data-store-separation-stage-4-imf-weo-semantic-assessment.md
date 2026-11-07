# Stage 4 — IMF WEO semantic assessment and evidence workspace

**Assessment date:** 2026-11-05  
**Scope:** WP1.5 fields 15, 16, 18, 20 and 21; IMF WEO October 2026 compared with World Bank WDI and country-level primary evidence.  
**Status:** consolidated diagnostic assessment; not a semantic approval, release validation, or source-selection decision.

## 1. Executive disposition

The comparison and targeted investigations materially improve coverage and identify country-specific explanations, but they do not support changing any source-selection assignment. Keep the existing IMF WEO priority assignments for all five fields unchanged. Do not promote WDI as a fallback, create country overrides, approve the October 2026 release, or write observations to the Game DB on the basis of these diagnostics.

| Field | Concept | Assessment | Current disposition |
|---:|---|---|---|
| 15 | GDP, current US dollars | **Qualified comparability** | Same broad concept/unit after normalization; national-account vintage, exchange-rate conversion and source revision differences remain material. Keep IMF priority. |
| 16 | GDP per capita, current US dollars | **Qualified comparability** | Related to field 15 and population denominator; inherit national-account, exchange-rate and population-vintage issues. Keep IMF priority. |
| 18 | GDP at PPP | **Not yet demonstrated comparable** | PPP benchmark, ICP vintage, conversion treatment and WEO construction need explicit reconciliation; actual/estimate status is unavailable in the WEO export metadata. Keep IMF priority. |
| 20 | CPI inflation | **Not yet demonstrated comparable** | Annual period-average convention and fiscal-year alignment are unresolved for important country cases; WEO reporting-period metadata is blank. Keep IMF priority. |
| 21 | Unemployment | **Non-equivalent series in the general case; country-specific corroboration exists** | WDI modelled ILO estimates are a distinct product from country-desk and national series. Primary evidence corroborates selected WEO values, with population/reference-period caveats. Keep IMF priority. |

These are evidence classifications, not approval states. “Qualified” does not mean every country-year is validated.

## 2. Reproducible comparison evidence

Owner-run comparison (2026-11-05):
- Tests: 15 passed across the IMF WEO assessment, WDI assessment and comparison suites.
- Comparison period: 2015–2025.
- Candidate matrix: **13,310 rows** = 242 unique project `game_id` identities × 5 fields × 11 years.
- Matched numerical observations: **9,324**.
- Coverage: both sources 9,324; IMF only 450; WDI only 1,354; neither 2,182.
- The matrix preserves all four coverage states and marks semantics `diagnostic_only_not_approved`.
- No database writes, source-policy changes or release promotion occurred.

Per-field coverage:

| Field | Both present | IMF only | WDI only | Neither |
|---:|---:|---:|---:|---:|
| 15 | 2,087 | 52 | 168 | 355 |
| 16 | 2,080 | 52 | 175 | 355 |
| 18 | 2,062 | 77 | 95 | 428 |
| 20 | 1,951 | 186 | 28 | 497 |
| 21 | 1,144 | 83 | 888 | 547 |

The candidate matrix is the completeness artifact. The matched-pair CSV is not the full country/field/year universe.

## 3. Country identity and code matching gate

All 242 project identity records in the current registry remain proposed, with unverified ISO assignments. Consequently all 13,310 matrix rows correctly carry `mapped_review_required`; this is not a comparison defect and must not be “fixed” by auto-promoting plausible codes.

- IMF code `WBG` remains unresolved; do not force it into a sovereign country.
- WDI codes `CHI`, `GIB` and `XKX` remain unresolved pending governed identity records/mappings.
- Country identity approval is a separate governance workstream. A numerical match does not approve an identity.
- Identity promotion is not a prerequisite to retain the diagnostic matrix, but is a gate before production application for affected identities.

## 4. Field-level semantic findings

### Field 15 — GDP

IMF `NGDPD` and WDI `NY.GDP.MKTP.CD` are both current-price GDP in US dollars after unit normalization. This is a reasonable broad-concept comparison, not proof of equal source construction or vintage.

The 2015–2025 targeted investigation confirms persistent discrepancies:
- Central African Republic: median absolute relative difference **51.670%**, IMF higher in all 11 years.
- Guinea: **52.534%**, IMF higher in all 11 years.
- Turkmenistan: **55.200%**, IMF higher in all 11 years.

Existing evidence remains the controlling interpretation: Guinea's 2018-base SNA 2008 rebasing materially raised its GDP level and current UN/INS evidence is closer to WEO than to the compared WDI values; CAR's May 2026 SNA 2008 / 2019-base national-accounts release supersedes the older series and must be aligned by vintage; Turkmenistan's dual exchange-rate and alternative conversion-factor regime can materially affect dollar conversion. Do not repeat or overwrite those investigations. The latest WEO metadata identifies CAR's SNA 2008 source and May 2026 rebasing.

The WEO latest-actual year is a hint, not an observation-level WDI status classification. For CAR, the WEO metadata latest actual year is 2022; 2023–2025 are after that threshold. WDI actual/estimate status is not classified by the comparison.

**Gate:** obtain the exact national-account vintages and exchange-rate/conversion inputs underlying each compared provider series before treating outliers as resolved.

### Field 16 — GDP per capita

IMF `NGDPDPC` and WDI `NY.GDP.PCAP.CD` are current US dollars per person, but the denominator introduces population vintage, population universe and revision differences in addition to field 15's national-account and exchange-rate issues.

Targeted medians:
- Central African Republic: **53.023%**, IMF higher in all 11 years.
- Guinea: **45.902%**, IMF higher in all 11 years.
- Turkmenistan: **71.800%**, IMF higher in all 11 years.

Treat these as coupled investigations with field 15, not independent evidence of a separate GDP-per-capita error. Confirm numerator and population denominator vintages before decomposing the differences.

**Gate:** reconcile GDP numerator, population denominator, population coverage and conversion basis for the same vintage and reference year.

### Field 18 — GDP at PPP

IMF `PPPGDP` and WDI `NY.GDP.MKTP.PP.CD` are expressed in current international dollars, but the label/unit match does not establish benchmark or construction equivalence.

Targeted medians:
- Central African Republic: **53.792%**, IMF higher in all 11 years.
- Guinea: **57.176%**, IMF higher in all 11 years.
- Zimbabwe: **26.415%** median absolute relative difference, mixed direction.

For CAR and Guinea, PPP discrepancies are similar in scale to nominal GDP discrepancies, consistent with underlying national-account vintage effects; the nominal-GDP versus PPP-factor decomposition remains outstanding. Zimbabwe's WDI 2017 PPP observation reflects the ICP benchmark history; WDI API and older WITS displays can differ by ICP vintage. The existing IMF methodological evidence describes a special desk exchange-rate conversion of Zimbabwe's 2017 ICP PPP factor before applying it to WEO nominal GDP submitted in USD.

The October 2026 WEO export does not provide `LATEST_ACTUAL_ANNUAL_DATA` for PPPGDP. Its actual/estimate/projected status is therefore unclassified. Do not infer it from adjacent WEO indicators or from the year label.

**Gate:** reconcile ICP benchmark vintage, extrapolation/linking method, PPP conversion factor, nominal GDP input and any country-desk adjustment. Retain unknown status explicitly.

### Field 20 — CPI inflation

IMF `PCPIPCH` and WDI `FP.CPI.TOTL.ZG` are annual CPI inflation rates, but annual period-average conventions and reference periods must be aligned before treating values as equivalent.

Targeted medians:
- Palau: **64.133%**, mixed direction.
- Samoa: **65.067%**, mixed direction.
- Tonga: **97.666%**, mixed direction.

Existing country evidence identifies fiscal-year/calendar-year alignment as a strong explanation for much of the discrepancy: Samoa uses July–June; Tonga's fiscal year begins 1 July; Palau's fiscal year ends 30 September. Tonga also changed its CPI basket/methodology in September 2021. The WEO reporting-period metadata for this series is blank, so the comparison cannot establish the exact period convention and must not shift year labels.

The Samoa 2025 residual and earlier Tonga/Palau observations remain open. Large relative differences should be interpreted with absolute percentage-point differences, not relative percentages alone.

**Gate:** obtain exact annual-average CPI construction and source reference period for both providers, country by country; do not infer fiscal-year labels from country practice alone.

### Field 21 — Unemployment

IMF `LUR`, WDI `SL.UEM.TOTL.ZS` and WDI `SL.UEM.TOTL.NE.ZS` are not interchangeable by default:
- WDI `SL.UEM.TOTL.ZS` is an ILO modelled estimate with imputation.
- WDI `SL.UEM.TOTL.NE.ZS` is a national-estimate series and is retained as a separate diagnostic.
- IMF WEO country-desk metadata can describe national definitions, source populations and methods, but the IMF `UNIT` field is blank in the October 2026 export and must be confirmed before production interpretation.

Targeted 2015–2025 median absolute relative differences against the modelled WDI series are high: Bahrain **281.137%**, Moldova **182.145%**, Philippines **107.852%**. These relative metrics are sensitive to small denominators; compare levels and percentage-point differences as well.

Primary-source assessment already documents:
- **Bahrain:** keep the settled disposition. The official API total-rate series matches WEO for 2017–2025. In 2016 the API's 4.3% matches the Ministry's December value; the Ministry gives 4.0% annual average, while GCC-STAT reports 3.9% annual citizen unemployment matching WEO. Classify as a likely reference-period mismatch; the API does not explicitly expose its reference period. Do not reopen this case.
- **Moldova:** WEO matches NBS national LFS values for 2024 (3.955% vs 4.0%) and 2025 (3.802% vs 3.8%). Preserve the 2025 EMDOS 3 sample/population-weight redesign and NBS warning that 2025 is not fully comparable with 2019–2024.
- **Philippines:** WEO closely matches PSA annual LFS rates for 2023–2025 (4.358% vs 4.4%; 3.817% vs 3.8%; 4.208% vs 4.2%). Preserve the annualized LFS convention and preliminary status of the 2025 annual result.

The comparison does not classify WDI observations as actual or estimates. National-estimate series coverage and definitions must be checked country by country; it is not an automatic replacement for the ILO-modelled series.

**Gate:** confirm the IMF unit and country metadata, exact reference population, survey/register basis, reference period and annual aggregation. Keep Bahrain closed under its documented disposition.

## 5. Actual, estimate and projection status

No universal three-way status classification is currently supported:
- IMF `LATEST_ACTUAL_ANNUAL_DATA` can identify an actual-data boundary for supported WEO country series; years after it are not automatically distinguishable as estimate versus projection.
- PPPGDP has no latest-actual metadata in this export.
- The snapshot-backed comparison preserves WDI obs_status; only explicit API status F is labelled forecast. Blank and other statuses remain unclassified, so WDI actual/estimate status is not generally established.
- National source publications can be preliminary or revised; that status must be sourced independently and retained with the country-year evidence.
- Country groups and aggregates must not inherit country-level status rules.

Do not populate a definitive `actual | estimate | projection` field where source metadata does not support it. Use explicit `unknown` / `not_classified` states.

## 6. Release-vintage and reproducibility limitation

The original 2026-11-05 comparison combined the fixed IMF October 2026 CSV export with live WDI API responses. On 2026-11-07, an immutable response snapshot was captured and replayed. The snapshot remains a timestamped rolling API capture, not a provider-declared WDI vintage; it does not align the WDI source publication vintage with the IMF October 2026 release.

Owner-run capture, full manifest audit, Project DB provenance registration, database integrity checks and frozen comparison have now completed. The exact manifest, fingerprint and equivalence results are recorded in [World Bank WDI immutable API snapshot acquisition](../data-sources/world-bank-wdi-snapshot-acquisition.md). The snapshot reproduces all 13,310 candidate keys, WDI and IMF values, coverage states, IMF status hints and IMF reporting-period classifications from the 2026-11-05 live comparison. This confirms input-value stability across those two runs, not semantic equivalence between providers.

The captured WDI `obs_status` field is blank for all 13,310 candidate rows. Of these, 10,678 rows have a WDI observation but remain `not_classified_by_this_comparison`; 2,632 rows have no WDI observation and are classified `missing`. No WDI observation is thereby established as actual, estimate or projection. The snapshot does not authorize redistribution beyond verified dataset/indicator terms.

## 7. Remaining work, ordered by dependency

1. **Freeze comparison inputs — complete:** the 2026-11-07 WDI snapshot was captured, all 14 artifacts passed byte-count and SHA-256 audit, provenance was registered in the Project DB, and the frozen comparison reproduced the 2026-11-05 live-run values and coverage exactly. Preserve both reports and the manifest as the reproducibility evidence.
2. **Close field-definition gates:** confirm field 21 IMF unit and source population; CPI annual convention; PPP benchmark/construction. The capture now preserves WDI observation-status metadata, but does not classify blank/unknown statuses.
3. **Reconcile country cases:** CAR new national accounts (fields 15/16/18), Guinea national accounts (15/16/18), Turkmenistan conversion (15/16), Zimbabwe ICP (18), Tonga/Samoa/Palau period conventions (20), Moldova/Philippines source vintages (21). Bahrain remains closed.
4. **Separate identity governance:** resolve 242 proposed/unverified identities and the explicit unmatched codes through the identity registry workflow; do not silently map.
5. **Produce a semantic disposition matrix — implementation complete, owner run pending:** `tools/build_imf_weo_wdi_semantic_disposition.py` now enriches every frozen candidate row with identity gate, field concept/method gate, period disposition, IMF/WDI status, existing country-case evidence and document links. The generated matrix remains diagnostic and not approved; see [Stage 4C](data-store-separation-stage-4c-semantic-disposition-matrix.md).
6. **Only then** prepare a separate source-selection recommendation and approval artifact. Application remains gated by existing approval and transactional safeguards.

## 8. Evidence files and owner-run provenance

Comparison outputs: `reports/sources/imf-wdi-comparison/20261105T103220Z/` (live API baseline) and `reports/sources/imf-wdi-comparison/20261107T144614Z/` (frozen snapshot replay).  
WDI snapshot implementation: `tools/acquire_world_bank_wdi_snapshot.py`, `tests/test_world_bank_wdi_snapshot.py`, and `docs/data-sources/world-bank-wdi-snapshot-acquisition.md`.  
Targeted investigation: `reports/sources/imf-wdi-discrepancy-investigation/20261105T104531Z/`  
IMF assessment: `reports/sources/imf-weo/20261105T101443Z/`

The targeted investigation contains 15 groups and 165 observations; it reads the comparison CSV only and fetches no new source data. Its output is descriptive evidence, not independent corroboration.

The comparison tests passed (15 tests) and the earlier IMF assessment tests passed (4 tests). Stage 4B snapshot tests and related suites passed (19 tests), and `compileall` completed without errors. Owner-run capture completed for snapshot `api_snapshot_20261107T133112433299Z`: 14 artifacts, 4,226,626 bytes, 296 country catalogue records, six indicators, 2,926 observation rows per indicator. Manifest audit: 1 manifest, 14/14 artifacts valid, zero errors. Project DB acquisition ID 6 has status `acquired`, integrity `verified`, and 14 artifacts; SQLite integrity is `ok` and foreign-key violations are empty. Frozen comparison output is `reports/sources/imf-wdi-comparison/20261107T144614Z/`; candidate matrix is 13,310 rows and reproduces all tested values and coverage from the 2026-11-05 live run. These are owner-reported local results; repository inspection does not replace local validation.

## 9. Next execution batch\n\nStage 4C implements the structured disposition matrix over the frozen 2026-11-07 candidate matrix. Run its focused tests, generate the matrix, and inspect the country-case and identity counts. Then use the generated unresolved-gate summary to prioritize any remaining source evidence. Do not rerun the already-completed WDI capture or discrepancy investigation, and do not reopen Bahrain.\n\n## 10. Governance and side-effect boundary

This assessment does not:
- modify source-selection configuration or priority assignments;
- create approval records or mark any release semantically validated/retained;
- change `latest_validated` or `latest_applied`;
- write or migrate either SQLite database;
- import or normalize WP1.5 observations;
- promote country identities or ISO assignments.

The October 2026 WEO acquisition remains acquired with byte integrity verified, not semantically approved. No Game DB write has occurred.
