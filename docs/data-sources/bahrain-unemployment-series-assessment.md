# Bahrain unemployment series assessment

**Assessment date:** 2026-11-02  
**WP1.5 field:** 21 — unemployment  
**Decision:** retain IMF WEO as the priority source; describe Bahrain's WEO series as a national-definition measure aligned with the official Bahraini-citizen unemployment rate, while retaining a year-specific corroboration caveat. Do not substitute WDI's modelled ILO estimate.

## Executive finding

The large difference between IMF WEO `LUR` and World Bank WDI `SL.UEM.TOTL.ZS` for Bahrain is not evidence that the IMF observations are erroneous. Bahrain's official national statistics explicitly publish unemployment rates for Bahraini citizens aged 15 and above; the 2024 and 2025 rates (6.2% and 5.6%) exactly match IMF WEO.

The acquired official annual API dataset establishes an exact match with IMF WEO for 2017–2025, while confirming a 0.4 percentage-point discrepancy in 2016 (official 4.3%, WEO 3.9%). The earlier 2022 primary-source verification gap is closed.

## Year-by-year evidence

The official Bahrain Open Data Portal dataset `03-unemployment-yearly` was acquired directly through the project's API adapter on 2026-11-02. The supplied API response contains 50 records: 20 sex-specific unemployed-person counts (male and female for each year 2016–2025) and 30 sex-specific/total unemployment-rate observations (male, female and total for each year 2016–2025). The provider labels the count series “Bahraini Unemployed (15 years and above) by Sex (Yearly)” and the rate series “Bahraini Unemployment Rate by Sex (Yearly)”.

### Total unemployment rate: official portal versus IMF WEO

| Year | Bahrain official total | IMF WEO `LUR` | Difference (official − IMF) | Assessment |
|---:|---:|---:|---:|---|
| 2016 | 4.3% | 3.9% | +0.4 pp | Unresolved discrepancy |
| 2017 | 4.1% | 4.1% | 0.0 pp | Exact match |
| 2018 | 4.3% | 4.3% | 0.0 pp | Exact match |
| 2019 | 4.7% | 4.7% | 0.0 pp | Exact match |
| 2020 | 5.9% | 5.9% | 0.0 pp | Exact match |
| 2021 | 5.9% | 5.9% | 0.0 pp | Exact match |
| 2022 | 5.4% | 5.4% | 0.0 pp | Exact match; primary record now verified |
| 2023 | 6.3% | 6.3% | 0.0 pp | Exact match |
| 2024 | 6.2% | 6.2% | 0.0 pp | Exact match |
| 2025 | 5.6% | 5.6% | 0.0 pp | Exact match |

**Result: 9 of 10 years match exactly.** The official primary dataset resolves the earlier 2022 verification gap. The 2016 discrepancy is confirmed by the dataset itself: official 4.3% versus IMF WEO 3.9%. No cause for the 0.4 percentage-point difference is established.

### Sex-specific rates

| Year | Male | Female | Total |
|---:|---:|---:|---:|
| 2016 | 1.00% | 9.30% | 4.30% |
| 2017 | 0.97% | 9.22% | 4.10% |
| 2018 | 1.20% | 8.50% | 4.30% |
| 2019 | 1.64% | 10.92% | 4.70% |
| 2020 | 2.90% | 10.20% | 5.90% |
| 2021 | 2.40% | 10.90% | 5.90% |
| 2022 | 2.10% | 10.10% | 5.40% |
| 2023 | 3.00% | 11.10% | 6.30% |
| 2024 | 3.2338% | 10.0342% | 6.20% |
| 2025 | 2.70% | 8.8635% | 5.60% |

Female unemployment is materially higher than male unemployment in every year in this dataset. The total rate is a labour-force-weighted aggregate; it is not the arithmetic mean of the male and female rates.

### Sex-specific unemployed-person counts

| Year | Male unemployed | Female unemployed |
|---:|---:|---:|
| 2016 | 1,487 | 6,998 |
| 2017 | 1,431 | 6,821 |
| 2018 | 1,924 | 6,475 |
| 2019 | 2,473 | 8,322 |
| 2020 | 4,444 | 10,839 |
| 2021 | 3,606 | 11,576 |
| 2022 | 3,286 | 10,746 |
| 2023 | 4,695 | 12,283 |
| 2024 | 5,206 | 12,196 |
| 2025 | 4,483 | 10,950 |

The API response contains male and female counts, but no total-count rows. Do not manufacture a provider total count. Male/female unemployed counts can be summed for a derived combined count if needed, but that derived value must be labelled as calculated, not provider-published. The rates and counts are separate provider observations; deriving labour-force denominators from rounded rates would be approximate and is not necessary to establish the official/IMF rate comparison.

### Primary-source acquisition and provenance

- Dataset: [Bahrain Open Data Portal — Unemployment (Yearly)](https://data.gov.bh/explore/dataset/03-unemployment-yearly/), identifier `03-unemployment-yearly`.
- API adapter: `uv run python -m tools.sources.bahrain_unemployment`.
- Reviewed raw snapshot: `raw_data/sources/bahrain_open_data/unemployment_yearly/20261102T141738Z/records_page_0001.json`.
- Manifest: `data_manifests/sources/bahrain_open_data/unemployment_yearly/20261102T141738Z.json`.
- Retrieval time: 2026-11-02T14:17:38.347094+00:00.
- API response: `total_count=50`, one page, 50 result records.
- The raw snapshot is retained locally and is not committed to Git; the manifest is the tracked provenance record.

Earlier government statements and reports provide historical corroboration, but the acquired official API records now supersede the previous incomplete secondary-source checks for 2016–2025. In particular, they directly establish the official 2016 rate and 2022 rate. The 2015 figure remains outside this dataset's 2016–2025 coverage.

## IMF WEO country metadata

For `BHR.LUR.A`, the October 2026 IMF WEO CSV records:

- `HISTORICAL_DATA_SOURCE`: Other.
- `LABOR_SECTOR_EMPLOYMENT_TYPE`: National definition.
- `METHODOLOGY_NOTES`: “Historical data source: LMRA, SIO and IMF staff projections”.
- `LATEST_ACTUAL_ANNUAL_DATA`: 2025.
- `COUNTRY_UPDATE_DATE`: 2026-09-24.
- `UNIT` is blank. Do not claim that the IMF export itself explicitly declares the unit.

The metadata and official-value matches strongly support the national-definition interpretation. However, the WEO note explicitly includes IMF staff projections, and `LATEST_ACTUAL_ANNUAL_DATA=2025` is a metadata hint rather than proof that every value is a direct national observation.

## WDI / ILO modelled estimate

- WDI `SL.UEM.TOTL.ZS` is an ILO modelled estimate, not a direct reproduction of Bahrain's national annual series.
- In the comparison run, WDI modelled values were approximately 1.084% (2024) and 1.102% (2025), versus IMF/official national values of 6.2% and 5.6%.
- WDI `SL.UEM.TOTL.NE.ZS` (national estimate) was present in the comparison only for 2015 (0.894%). It was unavailable for 2016–2025 in that API response. Do not fill those missing years or treat the 2015 value as representative of later years.
- The 2015 WDI national estimate is close to the WDI modelled estimate (1.164%) but far below the IMF value (3.5%). This does not resolve the historical population/definition difference.

The population-coverage explanation is supported by Bahrain's national dataset being explicitly Bahraini-citizen-focused and by the very different WDI modelled values. Nevertheless, the precise population universe and model inputs underlying every WDI year were not independently reconstructed here. Do not state that expatriate exclusion alone quantitatively explains the gap.

## Bahrain labour-force survey context

Bahrain's Information & eGovernment Authority (iGA) describes the Labour Force Survey as a household survey designed to measure employment, unemployment and economic participation across demographic characteristics, using ILO standards and recommendations.

- [iGA: Labour Force Survey 2026 launch (7 January 2026)](https://www.iga.gov.bh/en/article/iga-launches-the-labour-force-survey-2026) describes a survey planned across 2026 and a random sample of more than 8,000 households.
- [iGA: Labour Force Survey 2026 update (8 October 2026)](https://iga.gov.bh/en/article/iga-continues-the-labor-force-survey-2026-targeting-more-than-4-000-households-across-bahrains-governorates) reports fieldwork from October to December 2026, targeting more than 4,000 households.
- [iGA Labour Force Survey page](https://www.iga.gov.bh/en/category/labour-force-survey) describes a household survey and ILO-aligned methodology.

This survey may provide a more suitable source for an all-resident, internationally comparable measure once published with definitions and results. It is not yet a historical replacement for the 2015–2025 national-citizen series.

## Interpretation and limitations

1. **Population coverage:** The official annual dataset is explicitly about Bahraini unemployed people aged 15 and above. WDI's ILO modelled estimate is a different statistical product. This supports a population/methodology mismatch, but the exact WDI model population and all model inputs were not independently reconstructed.
2. **Historical coverage:** The acquired official annual dataset directly verifies 2016–2025. Nine of ten total-rate observations (2017–2025) exactly match WEO; 2016 differs by 0.4 percentage points. The dataset does not cover 2015.
3. **Reference period:** Some historical Ministry figures are monthly or quarterly observations; they must not automatically be treated as annual averages. Confirm the annual series' construction from the Ministry dataset/report metadata.
4. **Administrative measures:** Historical ILO documentation describes registered-unemployment measures with eligibility and registration conditions. Such administrative measures are not automatically equivalent to a household-survey unemployment rate. Do not use historical registration rules as proof of the current official annual series' methodology.
5. **IMF status:** `LATEST_ACTUAL_ANNUAL_DATA=2025` is a metadata hint, not proof that every value is an observed national statistic. IMF notes explicitly mention IMF staff projections.
6. **Units:** The IMF WEO CSV's `UNIT` is blank. Official rate corroboration supports interpreting the values as percentages for Bahrain, but the source metadata gap should remain recorded.

## Source-selection disposition

- Keep field 21's approved `imf_weo` priority-source assignment unchanged.
- For Bahrain, describe the selected series as a national-definition unemployment rate aligned with the official Bahraini-citizen annual measure (15 years and above), with direct official-value corroboration for 2024 and 2025 and historical corroboration of most, but not all, earlier years.
- Preserve the 2016 discrepancy as unresolved; do not adjust or overwrite the IMF value based on the currently located 4.3% government statement.
- Do not substitute WDI `SL.UEM.TOTL.ZS` for the IMF values. Retain it as an international-comparability diagnostic with distinct population/methodology.
- Do not create a Bahrain-only manual override or change the source-selection policy on the basis of this assessment.
- Revisit the decision if a primary Ministry source explains the 2016 discrepancy, if the 2015 historical value is needed, or when iGA publishes the 2026 Labour Force Survey results and methodological metadata. The 2022 verification is complete.

## Reproducibility and side-effect boundary

The underlying comparison and targeted investigation are read-only reports:

- Comparison: `reports/sources/imf-wdi-comparison/20261102T130617Z/`
- Targeted investigation with retained IMF/WDI national-estimate metadata: `reports/sources/imf-wdi-discrepancy-investigation/20261102T131406Z/`

This assessment does not change `config/source_selection.json`, source registry entries, approval records, release ledgers or canonical SQLite. No data has been imported or promoted.

## Reproducible primary-data acquisition

The official [Bahrain Open Data Portal annual unemployment dataset](https://data.gov.bh/explore/dataset/03-unemployment-yearly/) is the primary record-level source for the remaining reconciliation. Its description is “Bahraini Unemployed (15 years and above) and the Unemployment Rate by Sex (Yearly)”. The dataset is exposed through the portal's Opendatasoft Explore API v2.1.

Use the project adapter and acquisition procedure documented in [Bahrain annual unemployment data acquisition](bahrain-unemployment-data-acquisition.md):

```fish
uv run python -m tools.sources.bahrain_unemployment
```

The adapter captures dataset metadata and all paginated records as immutable JSON under `raw_data/sources/bahrain_open_data/unemployment_yearly/<UTC timestamp>/`, with SHA-256 manifest under `data_manifests/sources/bahrain_open_data/unemployment_yearly/`. It preserves provider fields and categories, including sex-specific and total observations, without deriving or changing values.

After acquisition, inspect the actual schema and reconcile each year, sex and indicator separately. Counts and rates must remain distinct. A total rate must not be calculated as the arithmetic mean of male and female rates. The dataset is explicitly Bahraini-focused, so retain its population-universe limitation when comparing it with all-resident or modelled ILO series.

This adapter is acquisition-only. It does not normalize observations, approve a source release, change the IMF WEO priority policy, create a WP1.5 application approval, or write to SQLite. The reviewed API snapshot establishes official total rates for 2016–2025, resolves the 2022 verification gap, and confirms the 2016 discrepancy (official 4.3% versus IMF 3.9%). The 50 raw records include male/female counts and male/female/total rates; no provider total-count rows are present.

