# Turkmenistan GDP conversion-basis reconciliation

**Assessment date:** 8 November 2026  
**Status:** diagnostic finding; no source-policy or canonical-data approval  
**Scope:** Turkmenistan, WDI and October 2026 IMF WEO, nominal GDP (field 15), with implications for GDP per capita and PPP GDP.

## Executive finding

The 2015–2025 WDI/IMF WEO nominal-GDP difference is substantially a currency-conversion issue, not evidence by itself of different local-currency GDP levels.

For every year in the captured WDI snapshot, WDI current-USD GDP is reproduced by:

`WDI GDP current USD = WDI GDP current LCU / WDI DEC alternative conversion factor`.

For nine of the eleven years (2015–2021 and 2024–2025), the captured WDI current-LCU GDP divided by 3.5 TMT per US dollar reproduces October 2026 WEO current-USD GDP to the displayed precision. The implied WEO conversion factor is approximately 3.5 in those years. The 2022 and 2023 rows do not reconcile to 3.5 and remain explicit residual cases.

This is a strong arithmetic reconciliation, not proof that the WEO compilers used the WDI local-currency series or explicitly applied 3.5 in their production process. The exact WEO local-currency numerator and compilation lineage have not yet been independently retrieved.

## 1. Captured series and arithmetic

The frozen WDI snapshot is `api_snapshot_20261107T161129160851Z`, retrieved 7 November 2026. It includes `NY.GDP.MKTP.CN`, `NY.GDP.MKTP.CD`, `PA.NUS.FCRF`, and `PA.NUS.ATLS`. The October 2026 IMF WEO export supplies `NGDPD` for the comparison.

| Year | WDI GDP current LCU (bn TMT) | WDI DEC factor (TMT/USD) | WDI GDP current USD (bn) | IMF WEO GDP current USD (bn) | WDI vs WEO |
|---:|---:|---:|---:|---:|---:|
| 2015 | 125.299 | 3.5000 | 35.800 | 35.800 | 0.00% |
| 2016 | 126.593 | 3.8000 | 33.314 | 36.180 | -7.92% |
| 2017 | 132.742 | 3.9800 | 33.352 | 37.926 | -12.06% |
| 2018 | 142.679 | 5.4800 | 26.036 | 40.762 | -36.13% |
| 2019 | 157.410 | 5.3000 | 29.700 | 44.974 | -33.96% |
| 2020 | 159.092 | 5.8168 | 27.351 | 45.455 | -39.83% |
| 2021 | 173.170 | 6.5759 | 26.334 | 49.477 | -46.77% |
| 2022 | 203.947 | 5.4264 | 37.584 | 56.677 | -33.69% |
| 2023 | 211.704 | 5.4255 | 39.020 | 62.814 | -37.88% |
| 2024 | 240.363 | 5.4320 | 44.249 | 68.675 | -35.57% |
| 2025 | 270.893 | 5.4365 | 49.829 | 77.398 | -35.62% |

The implied conversion factor calculated as WDI current-LCU GDP divided by WEO current-USD GDP is approximately:

| Year | Implied WEO conversion factor (TMT/USD) | Assessment |
|---:|---:|---|
| 2015 | 3.5000 | Consistent with 3.5 |
| 2016 | 3.4990 | Consistent with 3.5 |
| 2017 | 3.5000 | Consistent with 3.5 |
| 2018 | 3.5003 | Consistent with 3.5 |
| 2019 | 3.5000 | Consistent with 3.5 |
| 2020 | 3.5000 | Consistent with 3.5 |
| 2021 | 3.5000 | Consistent with 3.5 |
| 2022 | 3.5984 | Residual; not 3.5 |
| 2023 | 3.3703 | Residual; not 3.5 |
| 2024 | 3.5000 | Consistent with 3.5 |
| 2025 | 3.5000 | Consistent with 3.5 |

The factors above are calculated from the rounded values displayed in the table. The assessment tool now emits `imf_ngdpd_implied_conversion_factor_lcu_per_usd` from the underlying loaded values so that the exact residuals can be checked in the generated CSV. The 2022 and 2023 differences are far larger than display rounding: using the displayed WDI LCU values, division by 3.5 implies US$58.271bn in 2022 versus WEO US$56.677bn (+2.81%), and US$60.487bn in 2023 versus WEO US$62.814bn (-3.70%).

### What this establishes

1. WDI current-USD GDP is arithmetically consistent with the captured DEC alternative factor across all eleven years.
2. In nine years, WEO current-USD GDP is arithmetically consistent with the same WDI local-currency GDP divided by 3.5.
3. The conversion basis explains most of the persistent WDI/WEO nominal-USD level difference. It is not a complete explanation in 2022–2023.
4. The official exchange-rate WDI indicator `PA.NUS.FCRF` is missing in the snapshot for every year. The 3.5 comparison is therefore an external reference documented in the IMF working paper, not an observed WDI official-rate series in this capture.

### What this does not establish

- It does not prove that WEO used the WDI local-currency series as its numerator.
- It does not prove that WEO's published compilation method explicitly specifies 3.5 for every year.
- It does not explain the 2022–2023 residuals.
- It does not establish the source or construction of the WDI DEC factor.
- It does not establish that the DEC factor is the parallel-market exchange rate.
- It does not resolve GDP-per-capita denominator differences or PPP benchmark/factor differences.

## 2. IMF Working Paper 2023/207: what it contributes

Bayar and Gogoberishvili's IMF Working Paper 2023/207, *Reassessing GDP Growth in Countries with Statistical Shortcomings – A Case Study on Turkmenistan*, is research in progress. Its disclaimer states that the views are those of the authors and do not necessarily represent the IMF, its Executive Board or management. It is not an official replacement national-accounts series.

The paper proposes a bottom-up expenditure-side GDP estimation framework for settings where official data are unavailable or where official statistics use an official exchange rate that differs materially from rates relevant to actual foreign-exchange transactions. It combines official raw data with external evidence, including bilateral/multilateral trade data, imports of intermediate and consumption goods, sectoral production inputs, fiscal information, services trade and other indicators. It emphasizes counterparty trade statistics as a cross-check and cautions that both internal and external source quality must be examined.

For Turkmenistan, the paper states that the official rate remained 3.5 manat per US dollar from 2015, while the parallel-market rate diverged, reaching about 38 manat per US dollar in April 2021. It describes the parallel-market rate as an indicative measure of external-account pressure, not an official exchange-rate observation. The paper's combined-deflator approach attempts to capture price developments in formal and informal activity. It estimates the share of parallel-market activity using official household-consumption-survey data and an assumed consumption structure similar to regional oil-exporting economies. It differentiates the treatment of activities likely to have an informal component from government activity.

**Critical distinction:** the paper's documented parallel-market rate is not the same thing as the WDI DEC factor. The captured DEC factor peaks at 6.5759 in 2021, whereas the paper reports an indicative parallel-market rate around 38. The DEC series is neither the official 3.5 rate nor the paper's cited parallel-market rate. No captured provider documentation identifies the DEC factor as a measured parallel-market rate. Do not label it as such.

The paper is relevant to the interpretation of the IMF's alternative real-GDP analysis and the limitations of official price/deflator data. Its combined-deflator method does not, by itself, prove the exchange-rate conversion used in the WEO nominal-USD series. Nominal GDP conversion and real GDP deflation must remain separate analytical questions.

## 3. TurkmenStat notices: what changed, and what remains unknown

### 17 January 2025 — national accounts methodology

TurkmenStat reports that:
- a proposal to conduct statistical reporting using an improved version of the System of National Accounts had been approved;
- GDP output-calculation methods and other macroeconomic indicators had been improved in phases over several years, with international financial-organisation experts;
- reporting methodologies were modernized and several methodological documents based on the improved SNA version were developed and implemented;
- E-Statistics and business-registry software was prepared and installed.

The notice does not identify the SNA edition or provide a bridge table, benchmark revision, rebased GDP history, implementation date by series, or quantitative impact on 2015–2025 GDP. It therefore establishes a modernization programme, not a numerical explanation of the WDI/WEO discrepancy.

### 23 June 2026 — World Bank advisory agreement for 2026–2027

TurkmenStat reports a reimbursable advisory-services agreement with the World Bank Group/IBRD for 2026–2027. Planned areas include:
- methodology and participation in the International Comparison Program;
- strengthening national accounts and GDP compilation under the 2025 SNA;
- operational guidelines and sample lists for price collection;
- specialist training in PPP calculation and national-accounts compilation;
- digital household and labour-force survey collection using Survey Solutions/CAPI, including training and a pilot.

This is evidence that important national-accounts, PPP and survey-methodology work was still planned for 2026–2027. It is not evidence that 2025 SNA implementation, a new ICP benchmark, a household/labour survey redesign or a historical GDP revision had already been completed by June 2026.

The two notices are not contradictory: the January 2025 notice describes phased modernization already undertaken under an improved SNA version, while the June 2026 notice describes a further programme aligned to the 2025 SNA and ICP work.

## 4. Revised country-case interpretation

### Field 15 — GDP current USD

For 2015–2021 and 2024–2025, the captured WDI local-currency GDP and IMF WEO current-USD GDP imply a conversion factor of approximately 3.5 TMT/USD. The WDI published current-USD series instead follows the DEC alternative conversion factor. This strongly indicates that the main WDI/WEO difference in those years is conversion basis, not a different local-currency GDP numerator.

The 2022 and 2023 implied factors differ from 3.5. These years require separate reconciliation against the WEO local-currency GDP numerator, WEO exchange-rate assumptions, national-accounts revisions and any period/vintage changes. Do not force them into the nine-year pattern.

**Disposition:** the previous generic description of Turkmenistan's field-15 gap as an unresolved national-accounts level difference is too broad. Replace it with a conversion-basis explanation for nine years plus explicit 2022–2023 residuals. The DEC factor's provenance and appropriateness remain unresolved. This does not approve either conversion basis for canonical use.

### Field 16 — GDP per capita current USD

The nominal GDP conversion difference is a likely major contributor to the per-capita gap, but the population denominator must be assessed independently. Compare WDI `SP.POP.TOTL` with the population series embedded in or used by WEO for each year. The current assessment must not assume identical population reference dates, universe or revisions. Do not infer that field 16 is fully explained by field 15.

### Field 18 — PPP GDP

The nominal-USD conversion reconciliation does not close PPP comparability. WDI PPP GDP is arithmetically reproduced from current-LCU GDP and the captured WDI PPP conversion factor, but ICP benchmark, PPP factor vintage, extrapolation and national-accounts input remain separate gates. TurkmenStat's June 2026 notice makes the planned ICP and 2025 SNA capacity work especially relevant, but does not document a completed new benchmark.

## 5. Required follow-up before any policy decision

1. Extract the WEO local-currency nominal GDP series (or an authoritative WEO country-data bridge) and compare it year-by-year with WDI `NY.GDP.MKTP.CN`, prioritizing 2022–2023.
2. Retrieve provider-specific documentation for Turkmenistan's WDI `PA.NUS.ATLS` observations: source, method, reference date, and why the factor differs from both the official rate and the paper's indicative parallel-market observations.
3. Check whether the 2022–2023 residual reflects a different WEO local-currency numerator, exchange-rate convention, timing, or a national-accounts revision. Keep alternatives open until direct evidence is found.
4. Compare WDI and WEO population inputs for field 16.
5. Keep field 18 open pending ICP benchmark/factor evidence and the outcome of the 2026–2027 technical-assistance programme.

No identity approval, semantic approval, source-selection change, release promotion, retention action or Game DB write is authorized by this assessment. Keep the existing IMF WEO priority unchanged pending the separate approval workflow.

## Sources

### Captured Project DB evidence

- IMF Working Paper 2023/207, dataset `gdp_statistical_shortcomings_wp_2023_207`, acquisition ID 12; full-text XML capture, SHA-256 `34622422ded28dedf5ad71b361e7da345255a5c3a4a915cf7511a18ae8d62288`.
- TurkmenStat, 17 January 2025 notice, dataset `national_accounts_methodology_2025`, acquisition ID 10; HTML capture, SHA-256 `59e824dcaac8220cc2807e7c3979e2bd7753ca5e1899f0469893aa5d338b5999`.
- TurkmenStat, 23 June 2026 notice, dataset `statistical_system_reform_2026`, acquisition ID 11; HTML capture, SHA-256 `fcdfe60cc5a4eada462987c1f1bde069ff4d909c863a576e98d8f08f51a30abb`.
- WDI snapshot `api_snapshot_20261107T161129160851Z`, 12 indicator bundles, 2014–2025.
- IMF WEO October 2026 CSV and frozen WDI comparison/decomposition reports recorded in the Stage 4 assessment.

### Public source records and definitions

- Bayar, Ömer E. and Levan Gogoberishvili, [IMF Working Paper 2023/207](https://www.imf.org/en/publications/wp/issues/2023/09/29/reassessing-gdp-growth-in-countries-with-statistical-shortcomings-a-case-study-on-539482), September 2023; [official full-text XML](https://www.elibrary.imf.org/view/journals/001/2023/207/article-A001-en.xml).
- TurkmenStat, [National accounts in statistics are improved](https://www.stat.gov.tm/en/news/204), 17 January 2025.
- TurkmenStat, [The national statistical system of Turkmenistan is being improved](https://www.stat.gov.tm/en/news/359), 23 June 2026.
- World Bank, [GDP (current US$), Turkmenistan](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD?locations=TM), including its general source/coverage metadata.
- UN Statistics Division, [System of National Accounts 2025](https://unstats.un.org/unsd/econstats/national-accounts/sna2025), adopted by the UN Statistical Commission in 2025.
