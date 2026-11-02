# Bahrain unemployment series assessment

**Assessment date:** 2026-11-02  
**WP1.5 field:** 21 — unemployment  
**Decision:** retain IMF WEO as the priority source; document the Bahrain series as a national-definition measure that corresponds to the official Bahraini-citizen unemployment rate. Do not substitute WDI's modelled ILO estimate.

## Executive finding

The large difference between IMF WEO `LUR` and World Bank WDI `SL.UEM.TOTL.ZS` for Bahrain is best explained by different statistical populations/series, not by evidence that the IMF observation is erroneous.

Bahrain's Open Data Portal describes its official annual dataset as **“Bahraini Unemployed (15 years and above) and the Unemployment Rate by Sex (Yearly)”**. The official rates for 2024 and 2025 are 6.2% and 5.6%, respectively. Those values exactly match the October 2026 IMF WEO `BHR.LUR.A` observations for those years.

| Year | IMF WEO `LUR` | Bahrain official annual rate | Difference |
|---:|---:|---:|---:|
| 2024 | 6.2% | 6.2% | 0.0 pp |
| 2025 | 5.6% | 5.6% | 0.0 pp |

The portal's dataset description explicitly identifies the population as Bahraini unemployed people aged 15 and above. The series should therefore not be labelled as an all-resident rate without further evidence.

## Evidence

### Official Bahrain annual dataset

- Dataset: [Unemployment (Yearly), Bahrain Open Data Portal](https://www.data.gov.bh/explore/dataset/03-unemployment-yearly/).
- Dataset identifier: `03-unemployment-yearly`.
- Published description: Bahraini unemployed people aged 15 and above and unemployment rate by sex, yearly.
- The 2024 and 2025 annual rates (6.2% and 5.6%) match the IMF WEO values exactly.
- The IMF WEO country metadata for `BHR.LUR.A` records:
  - `HISTORICAL_DATA_SOURCE`: Other.
  - `LABOR_SECTOR_EMPLOYMENT_TYPE`: National definition.
  - `METHODOLOGY_NOTES`: “Historical data source: LMRA, SIO and IMF staff projections”.
  - `LATEST_ACTUAL_ANNUAL_DATA`: 2025.
  - `COUNTRY_UPDATE_DATE`: 2026-09-24.
  - `UNIT` is blank. Do not claim that the IMF export itself explicitly declares the unit.
- The exact 2024–2025 match plus the country-specific metadata strongly supports alignment with Bahrain's official national-citizen unemployment series. The metadata does not prove that every earlier WEO year is a direct transcription of the portal series.

### WDI / ILO modelled estimate

- WDI `SL.UEM.TOTL.ZS` is an ILO modelled estimate, not a direct reproduction of Bahrain's national annual series.
- For 2024 and 2025, the comparison run recorded approximately 1.084% and 1.102%, respectively, versus IMF/official national rates of 6.2% and 5.6%.
- WDI `SL.UEM.TOTL.NE.ZS` (national estimate) is present in the comparison only for 2015 (0.894%). It is unavailable for 2016–2025 in that API response. Do not fill those missing years or treat the 2015 value as representative of later years.
- The 2015 WDI national estimate is close to the WDI modelled estimate (1.164%) but far below the IMF value (3.5%). This does not resolve the historical population/definition difference.

### Bahrain labour-force survey context

Bahrain's Information & eGovernment Authority (iGA) describes the Labour Force Survey as a household survey designed to measure employment, unemployment and economic participation across demographic characteristics, using ILO standards and recommendations.

- [iGA: Labour Force Survey 2026 launch (7 January 2026)](https://www.iga.gov.bh/en/article/iga-launches-the-labour-force-survey-2026) describes a survey planned across 2026 and a random sample of more than 8,000 households.
- [iGA: Labour Force Survey 2026 update (8 October 2026)](https://iga.gov.bh/en/article/iga-continues-the-labor-force-survey-2026-targeting-more-than-4-000-households-across-bahrains-governorates) reports fieldwork from October to December 2026, targeting more than 4,000 households.
- [iGA Labour Force Survey page](https://www.iga.gov.bh/en/category/labour-force-survey) describes a household survey and ILO-aligned methodology.

This survey is a potentially more suitable source for an all-resident, internationally comparable measure once published with definitions and results. It is not yet a historical replacement for the 2015–2025 national-citizen series.

## Interpretation and limitations

1. **Population coverage:** The official annual dataset is explicitly about Bahraini unemployed people. WDI's ILO modelled estimate is a different statistical product. The observed gap is consistent with a population-coverage mismatch, but the exact WDI model population and all model inputs were not independently reconstructed in this assessment.
2. **Historical series:** The exact official/IMF match has been established for 2024 and 2025. Do not extrapolate that verification to every year from 2015 through 2023 without a year-by-year comparison against the underlying Bahrain dataset.
3. **Administrative measures:** Historical ILO documentation describes registered-unemployment measures with eligibility and registration conditions. Such administrative measures are not automatically equivalent to a household-survey unemployment rate. Do not use historical registration rules as proof of the current official annual series' methodology.
4. **IMF status:** `LATEST_ACTUAL_ANNUAL_DATA=2025` is a metadata hint, not proof that every value is an observed national statistic. IMF notes explicitly mention IMF staff projections.
5. **Units:** The IMF WEO CSV's `UNIT` is blank. The matching official rates support interpreting these values as percentages for Bahrain, but the source metadata gap should remain recorded rather than silently rewritten.

## Source-selection disposition

- Keep field 21's approved `imf_weo` priority-source assignment unchanged.
- For Bahrain, describe the selected series as the national-definition unemployment rate aligned with the official Bahraini-citizen annual measure (15 years and above), with direct official-value corroboration for 2024 and 2025.
- Do not substitute WDI `SL.UEM.TOTL.ZS` for the IMF values. Retain it as an international-comparability diagnostic with distinct population/methodology.
- Do not create a Bahrain-only manual override or change the source-selection policy on the basis of this assessment.
- Revisit the decision when iGA publishes the 2026 Labour Force Survey results and methodological metadata, or when a complete official annual historical series is acquired and compared.

## Reproducibility and side-effect boundary

The underlying comparison and targeted investigation are read-only reports:

- Comparison: `reports/sources/imf-wdi-comparison/20261102T130617Z/`
- Targeted investigation with retained IMF/WDI national-estimate metadata: `reports/sources/imf-wdi-discrepancy-investigation/20261102T131406Z/`

This assessment does not change `config/source_selection.json`, source registry entries, approval records, release ledgers or canonical SQLite. No data has been imported or promoted.
