# Bahrain unemployment series assessment

**Assessment date:** 2026-11-02  
**WP1.5 field:** 21 — unemployment  
**Decision:** retain IMF WEO as the priority source; describe Bahrain's WEO series as a national-definition measure aligned with the official Bahraini-citizen unemployment rate, while retaining a year-specific corroboration caveat. Do not substitute WDI's modelled ILO estimate.

## Executive finding

The large difference between IMF WEO `LUR` and World Bank WDI `SL.UEM.TOTL.ZS` for Bahrain is not evidence that the IMF observations are erroneous. Bahrain's official national statistics explicitly publish unemployment rates for Bahraini citizens aged 15 and above; the 2024 and 2025 rates (6.2% and 5.6%) exactly match IMF WEO.

Historical public evidence also corroborates much of the WEO series, but **does not establish an exact year-by-year match for every year from 2015 through 2025**. In particular, a Government of Bahrain statement reports 4.3% for 2016, while the October 2026 WEO CSV reports 3.9%. That discrepancy must remain visible rather than being silently reconciled.

## Year-by-year evidence

| Year | IMF WEO `LUR` | Official/public corroboration located | Assessment |
|---:|---:|---|---|
| 2015 | 3.5% | Bahrain Economic Quarterly reports the Ministry of Labour rate at 3.5% in December 2015; a later Government of Bahrain statement also gives 3.5% for 2015. | Corroborated, though the quarterly publication describes a December/monthly rate, not necessarily an annual average. |
| 2016 | 3.9% | Government of Bahrain statement reports 4.3% for 2016. | **Unresolved 0.4 percentage-point difference.** Possible revision, reference-period or source-vintage difference; no cause established. |
| 2017 | 4.1% | Government of Bahrain statement reports 4.1%. | Corroborated. |
| 2018 | 4.3% | Government of Bahrain statement reports 4.3%. | Corroborated. |
| 2019 | 4.7% | Government of Bahrain statement and UN treaty-body record report 4.7%. | Corroborated. |
| 2020 | 5.9% | UN treaty-body record reports 5.9% for 2021; a Government of Bahrain statement gives 5.9% for 2020 and 2021. | Corroborated by government statement. |
| 2021 | 5.9% | Government of Bahrain statement and UN treaty-body record report 5.9%. | Corroborated. |
| 2022 | 5.4% | The official Bahrain annual unemployment dataset covers the year; WEO value also appears in secondary reproductions of the WEO series. A separately extracted primary annual record was not retained for this assessment. | Consistent, but record-level primary-source verification incomplete. |
| 2023 | 6.3% | Bahrain's official government facts-and-figures page reports 6.3%. | Corroborated. |
| 2024 | 6.2% | Bahrain Open Data Portal annual series reports 6.2%; this exactly matches WEO. | Direct official match. |
| 2025 | 5.6% | Bahrain Open Data Portal annual series reports 5.6%; this exactly matches WEO. | Direct official match. |

### Sources for the year-by-year checks

- [Bahrain Open Data Portal: Unemployment (Yearly)](https://www.data.gov.bh/explore/dataset/03-unemployment-yearly/), dataset `03-unemployment-yearly`. Its title/description is “Bahraini Unemployed (15 years and above) and the Unemployment Rate by Sex (Yearly)”. The portal's current annual dataset includes 2024 and 2025; the official figures are 6.2% and 5.6%.
- [Bahrain Economic Quarterly, March 2016](https://www.bahrainedb.com/app/uploads/2020/08/BEQ-March-2016.pdf), reports the Ministry of Labour unemployment rate at 3.4% in Q4 2015 and its monthly series around 3.5% in December 2015.
- [Government of Bahrain statement reproduced in a 2021 filing](https://www.rns-pdf.londonstockexchange.com/rns/1517S_1-2021-3-12.pdf): gives unemployment rates for Bahraini nationals of 3.5% (2015), 4.3% (2016), 4.1% (2017), 4.3% (2018) and 4.7% (2019).
- [Government of Bahrain statement reproduced in a 2022 filing](https://www.rns-pdf.londonstockexchange.com/rns/9948C_2-2022-10-14.pdf): reports 4.1% (2017), 4.3% (2018), 4.7% (2019), 5.9% (2020) and 5.9% (2021) for Bahraini nationals.
- [UN Committee on Economic, Social and Cultural Rights record E/C.12/2022/SR.19](https://digitallibrary.un.org/nanna/record/3959403/files/E_C.12_2022_SR.19-EN.pdf?registerDownload=1&version=1&withMetadata=0&withWatermark=0): records 4.7% in 2019 and 5.9% in 2021.
- [Bahrain government Facts & Figures](https://www.bahrain.bh/wps/portal/en/): reports a Bahraini unemployment rate of 6.3% for 2023.
- [Bahrain Open Data Portal: Statistics Reports](https://data.gov.bh/pages/statistics-page/?flg=en-gb): lists annual Labour Force reports for 2015–2023. These reports provide an avenue for primary record-level verification of the remaining years.

The Government of Bahrain statements are strong official-source evidence, but they are reproduced in third-party-hosted filings. The source and reporting basis should be captured from the original Ministry/portal datasets before claiming that every year is a direct match.

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
2. **Historical coverage:** Public official evidence corroborates most WEO years, but 2016 conflicts (3.9% WEO versus 4.3% in a Government of Bahrain statement), and the 2022 primary annual record has not been independently extracted. Do not describe the entire 2015–2025 series as fully verified.
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
- Revisit the decision when primary Ministry annual reports/dataset records for 2015–2023 have been acquired and checked, particularly the 2016 and 2022 records, and when iGA publishes the 2026 Labour Force Survey results and methodological metadata.

## Reproducibility and side-effect boundary

The underlying comparison and targeted investigation are read-only reports:

- Comparison: `reports/sources/imf-wdi-comparison/20261102T130617Z/`
- Targeted investigation with retained IMF/WDI national-estimate metadata: `reports/sources/imf-wdi-discrepancy-investigation/20261102T131406Z/`

This assessment does not change `config/source_selection.json`, source registry entries, approval records, release ledgers or canonical SQLite. No data has been imported or promoted.
