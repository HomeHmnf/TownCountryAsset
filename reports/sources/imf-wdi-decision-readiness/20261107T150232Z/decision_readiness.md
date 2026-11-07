# IMF WEO–WDI decision-readiness assessment

- Matrix rows: 13310
- Project identities: 242
- Decision: **not_ready_for_source_policy_change_or_canonical_application**
- Source priority: existing IMF WEO priority assignments remain unchanged for fields 15, 16, 18, 20 and 21

## Global gates

| Gate | Status | Finding | Required action |
|---|---|---|---|
| country_identity | blocking | Every one of the 242 project identities is still mapped_review_required; no row has verified identity mapping. | Resolve country identity and ISO assignment through the separate identity-governance process before any country-level canonical application. |
| source_vintage | blocking | The IMF input is the fixed October 2026 WEO export; the WDI input is a timestamped capture of the rolling API, not a provider-declared vintage. | Retain snapshot provenance and acquire aligned provider vintages where possible; do not describe the comparison as vintage-aligned. |
| observation_status | blocking_for_status_sensitive_use | WDI provides no explicit observation status in this capture; IMF latest-actual metadata is only a boundary hint and does not classify later years as projections. | Preserve unclassified/missing states; obtain explicit source status or country-specific evidence before classifying actual, estimate or projection. |
| approval_and_application | not_started_by_design | No semantic approval, source-selection change, release promotion or Game DB write has been made. | After blockers close, prepare a separate evidence-backed approval artifact; do not bypass the existing approval/application gate. |

## Field decisions

| Field | Concept | Current disposition | Readiness |
|---:|---|---|---|
| 15 | Qualified comparability: nominal GDP, current USD. | Retain existing IMF WEO priority; do not promote WDI. | blocked_semantic_and_identity_gates |
| 16 | Qualified comparability: nominal GDP per capita. | Retain existing IMF WEO priority; do not promote WDI. | blocked_semantic_and_identity_gates |
| 18 | Not demonstrated comparable: current PPP international dollars. | Retain existing IMF WEO priority; do not promote WDI. | blocked_semantic_and_identity_gates |
| 20 | Not demonstrated comparable: annual CPI inflation. | Retain existing IMF WEO priority; do not promote WDI. | blocked_semantic_and_identity_gates |
| 21 | Generally non-equivalent products: IMF country-desk/national series versus WDI ILO modelled estimates. | Retain existing IMF WEO priority; do not promote WDI modelled or national-estimate series. | blocked_semantic_and_identity_gates |

### Field 15 blockers and next actions

**Blockers**
- IMF October 2026 and WDI rolling-API snapshot are not provider-vintage aligned.
- National-accounts compilation, revision vintage and USD conversion are not reconciled country by country.
- CAR, Guinea and Turkmenistan have material documented cases with remaining year-level gaps.

**Next actions**
- Acquire or identify an immutable WDI provider vintage aligned to the WEO release, if available.
- Reconstruct source national-accounts levels and USD conversion for the material country cases.
- Resolve the 2018 Turkmenistan divergence onset and CAR post-2021/other-year series lineage.

Evidence record: `docs/data-sources/field-15-16-gdp-comparability-assessment.md`

### Field 16 blockers and next actions

**Blockers**
- All field 15 numerator-vintage and USD-conversion issues also apply.
- Population denominator vintage, reference date and universe are not independently reconstructed.

**Next actions**
- Complete the field 15 GDP numerator reconciliation.
- Acquire matching population series and reconstruct both providers' denominators by year.

Evidence record: `docs/data-sources/field-15-16-gdp-comparability-assessment.md`

### Field 18 blockers and next actions

**Blockers**
- ICP benchmark, linking/extrapolation and nominal-GDP input pipelines are not decomposed.
- IMF PPPGDP has no latest-actual metadata or reporting-period classification in the acquired WEO export.
- Zimbabwe's 2017 special conversion is documented but exact October 2026 WEO and current WDI record-level factors remain unverified.

**Next actions**
- Acquire immutable ICP 2017/2021 benchmark records and relevant PPP time series.
- Reconstruct provider-implied PPP factors and underlying nominal GDP by country-year.
- Keep actual/estimate status and reporting period unclassified until explicit evidence is available.

Evidence record: `docs/data-sources/field-18-ppp-gdp-comparability-assessment.md`

### Field 20 blockers and next actions

**Blockers**
- Period-average versus end-period definitions and calendar versus fiscal-year windows require explicit alignment.
- WEO reporting-period metadata is blank for the compared CPI observations.
- Samoa 2025 residual and earlier Tonga/Palau years remain unresolved; CPI revisions/vintages differ.

**Next actions**
- Acquire immutable WDI/IFS observations and exact country-year national/IMF fiscal-year tables.
- Record period start/end, annual-average or end-period convention, CPI basket and revision vintage.
- Resolve Samoa 2025 and the earlier Tonga/Palau observations before any full-period reconciliation.

Evidence record: `docs/data-sources/field-20-inflation-comparability-assessment.md`

### Field 21 blockers and next actions

**Blockers**
- IMF LUR unit is blank in the acquired WEO export; reference population and period need country-level verification.
- WDI modelled ILO estimates and WDI national estimates are distinct products, neither automatically interchangeable with WEO.
- WDI observation status is unclassified for all present observations in this snapshot.

**Next actions**
- Establish IMF LUR unit, reference population and annual aggregation for each country.
- Keep modelled and national-estimate WDI indicators separate in any future comparison.
- Use country-specific national-source corroboration only within its documented years and preserve survey redesign/preliminary flags.

Evidence record: `docs/data-sources/field-21-unemployment-comparability-assessment.md`

## Country evidence cases

Recorded case groups: 15. These are context or bounded corroboration, not approvals.

- Guinea — field 15 (`guinea_sna2008_2018_base_rebasing`): bounded evidence years: 2018, 2019, 2020, 2021, 2022, 2023, 2024; identity gate: blocking.
- Guinea — field 16 (`guinea_gdp_population_denominator`): bounded evidence years: 2018, 2019, 2020, 2021, 2022, 2023, 2024; identity gate: blocking.
- Guinea — field 18 (`guinea_ppp_decomposition`): bounded evidence years: none; identity gate: blocking.
- Zimbabwe — field 18 (`zimbabwe_icp_2017_benchmark`): bounded evidence years: 2017; identity gate: blocking.
- Tonga — field 20 (`tonga_fiscal_year_july_start_and_cpi_rebase`): bounded evidence years: 2022, 2023, 2024, 2025; identity gate: blocking.
- Bahrain — field 21 (`bahrain_reference_period_settled`): bounded evidence years: 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025; identity gate: blocking.
- Palau — field 20 (`palau_fiscal_year_september_end`): bounded evidence years: 2023, 2024, 2025; identity gate: blocking.
- Turkmenistan — field 15 (`turkmenistan_exchange_rate_regime`): bounded evidence years: 2019, 2020, 2021, 2022, 2023, 2024, 2025; identity gate: blocking.
- Turkmenistan — field 16 (`turkmenistan_gdp_population_denominator`): bounded evidence years: 2019, 2020, 2021, 2022, 2023, 2024, 2025; identity gate: blocking.
- Samoa — field 20 (`samoa_fiscal_year_july_june`): bounded evidence years: 2021, 2022, 2023, 2024, 2025; identity gate: blocking.
- Moldova — field 21 (`moldova_2025_lfs_redesign`): bounded evidence years: 2024, 2025; identity gate: blocking.
- Central African Republic — field 15 (`car_national_accounts_rebasing`): bounded evidence years: 2019, 2020, 2021; identity gate: blocking.
- Central African Republic — field 16 (`car_gdp_population_denominator`): bounded evidence years: 2019, 2020, 2021; identity gate: blocking.
- Central African Republic — field 18 (`car_ppp_decomposition`): bounded evidence years: none; identity gate: blocking.
- Philippines — field 21 (`philippines_annualized_lfs`): bounded evidence years: 2023, 2024, 2025; identity gate: blocking.

## Governance

- No source-selection priority changed.
- No identity was approved or promoted.
- No semantic approval was created.
- No release was promoted.
- Neither SQLite database was written.
- Country evidence must not be generalized beyond its bounded years; explicit missing/unclassified status is preserved.
