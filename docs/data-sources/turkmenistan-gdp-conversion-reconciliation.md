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

## 6. Direct WEO domestic-currency reconciliation (2026-11-08)

The October 2026 WEO CSV contains both `TKM.NGDP.A` (GDP at current prices, domestic currency, billions of TMT) and `TKM.NGDPD.A` (GDP at current prices, US dollars, billions). This directly tests the previously unresolved WEO local-currency numerator.

| Year | WDI current LCU (bn TMT) | WEO current LCU (bn TMT) | WDI minus WEO (%) | WEO current USD (bn) | WEO implied TMT/USD |
|---:|---:|---:|---:|---:|---:|
| 2015 | 125.299 | 125.299 | +0.000% | 35.800 | 3.499972 |
| 2016 | 126.593 | 126.630 | -0.029% | 36.180 | 3.500000 |
| 2017 | 132.742 | 132.742 | +0.000% | 37.926 | 3.500026 |
| 2018 | 142.679 | 142.667 | +0.008% | 40.762 | 3.500000 |
| 2019 | 157.410 | 157.410 | +0.000% | 44.974 | 3.500022 |
| 2020 | 159.092 | 159.092 | +0.000% | 45.455 | 3.499989 |
| 2021 | 173.170 | 173.170 | +0.000% | 49.477 | 3.500010 |
| 2022 | 203.947 | 198.371 | +2.811% | 56.677 | 3.500026 |
| 2023 | 211.704 | 219.848 | -3.704% | 62.814 | 3.499984 |
| 2024 | 240.363 | 240.363 | +0.000% | 68.675 | 3.500007 |
| 2025 | 270.893 | 270.893 | +0.000% | 77.398 | 3.500000 |

The WEO domestic-currency and USD series imply approximately 3.5 TMT/USD in every year. The small 2016 and 2018 local-currency differences are below 0.03% and are consistent with displayed precision/rounding. The two material local-currency discrepancies are 2022 (+2.811% WDI relative to WEO) and 2023 (-3.704%).

**Revised conclusion:** the 2022–2023 residuals are not explained by a different WEO exchange-rate conversion. They are already present in the two providers' domestic-currency GDP numerators. In the other nine years the local-currency series agree to displayed precision or within 0.03%. The earlier statement that the WEO local-currency numerator had not been retrieved is superseded by this direct comparison.

The reason for the 2022–2023 numerator differences remains unknown. The available evidence does not distinguish among source-vintage/revision differences, national-accounts compilation changes, timing/reference-period differences or other provider-specific inputs. No particular explanation should be asserted without a dated national source bridge or provider methodology evidence.

This finding strengthens the separation of two mechanisms: (a) the broad WDI/WEO current-USD level difference in years where local-currency GDP agrees is associated arithmetically with the different conversion factors; and (b) 2022–2023 contain additional, oppositely signed domestic-currency numerator differences. WDI's current-USD arithmetic remains reproduced by its DEC factor, but this does not prove the full provider compilation process or establish DEC as the parallel-market rate.

The October 2026 WEO export is the captured fixed release; WDI remains a timestamped rolling-API snapshot rather than a provider-declared vintage. The comparison therefore establishes differences between these captured series, not a fully vintage-aligned statistical reconciliation. Field 16 population denominators and field 18 PPP construction remain separate gates. No identity, semantic, source-selection or canonical-data approval follows from this diagnostic.


## 7. Field 16 population-denominator reconciliation (2026-11-08)

The October 2026 WEO CSV contains TKM.LP.A (annual population, millions). Its values agree, within the precision of the published series, with population implied independently by WEO current-USD GDP divided by WEO GDP per capita. This is an internal consistency check, not independent population validation.

| Year | WDI population | WEO population (m) | WEO implied persons | WDI above WEO |
|---:|---:|---:|---:|---:|
| 2015 | 6,215,770 | 5.766 | 5,766,491 | 7.791% |
| 2016 | 6,360,041 | 5.869 | 5,868,561 | 8.375% |
| 2017 | 6,507,061 | 5.968 | 5,968,343 | 9.026% |
| 2018 | 6,655,524 | 6.065 | 6,065,062 | 9.735% |
| 2019 | 6,803,944 | 6.158 | 6,158,380 | 10.483% |
| 2020 | 6,949,912 | 6.250 | 6,250,457 | 11.190% |
| 2021 | 7,092,043 | 6.342 | 6,341,837 | 11.829% |
| 2022 | 7,230,193 | 6.431 | 6,430,721 | 12.432% |
| 2023 | 7,364,438 | 6.516 | 6,516,130 | 13.019% |
| 2024 | 7,494,498 | 6.598 | 6,598,069 | 13.586% |
| 2025 | 7,618,847 | 6.680 | 6,679,994 | 14.055% |

The WEO metadata identifies TKM.LP.A as annual population in millions, with latest actual annual data 2024, country update date 25 September 2026, and historical data source “Turkmenistan authorities”. Its methodology note says pre-2009 data cannot currently be confirmed by national sources. The 2025 value must therefore remain projection-status, not actual. The metadata does not identify the precise national publication, population concept or revision vintage behind the series.

WDI SP.POP.TOTL describes total population using a de facto concept: all residents regardless of legal status or citizenship, with midyear estimates. Its general source-organization metadata lists several providers and does not establish the specific lineage of the Turkmenistan observations. WDI observation-status strings are blank in the captured snapshot; do not infer actual status from that blank.

The official 2022 Turkmenistan census reports 7,057,841 people as of 17 December 2022. The UN Population Division portal independently records 7,057,844 and classifies the census as de facto. WDI's 2022 midyear estimate of 7,230,193 is 2.44% above the census count; WEO's 6.431 million is 8.88% below it. The reference dates are not aligned, so this is corroborative context rather than a direct same-date error test.

The UN World Population Prospects 2024 revision identifies Turkmenistan as a major revision case: its 2023 population estimate was revised upward by 848,000 (13%) relative to WPP 2022, incorporating 2022 census evidence and indicating substantially more net in-migration over the 1995–2022/23 period than previously estimated. Historical estimates back to 1950 were revised. The captured WDI series is consistent with the higher revised population level and the census evidence; the WEO series is materially lower. However, the exact WEO population lineage is not verified, so it must not be labelled as WPP 2022 or any other specific revision without direct evidence.

**Field 16 conclusion:** population is a material, independent component of the Turkmenistan GDP-per-capita discrepancy. WDI is more consistent with the 2022 census and WPP 2024 upward revision than the captured WEO series, but exact WEO source lineage and date/concept alignment remain unresolved. Combined with the field-15 numerator reconciliation, this establishes that field 16 cannot be explained by GDP conversion alone.

## 8. Field 18 PPP/ICP reconciliation (2026-11-08)

The captured WDI PPP GDP is arithmetically reproduced by current-LCU GDP divided by PA.NUS.PPP for every year 2015–2025. The October 2026 WEO export contains TKM.PPPEX.A (domestic currency per international dollar) and TKM.PPPGDP.A (current PPP GDP). The WEO PPP GDP is broadly consistent with its own domestic-currency GDP and PPP factor, subject to small differences caused by displayed source precision.

| Year | WDI PPP factor | WDI PPP GDP (bn intl$) | WEO PPP factor | WEO PPP GDP (bn intl$) | WDI vs WEO PPP GDP |
|---:|---:|---:|---:|---:|---:|
| 2015 | 1.585414 | 79.032 | 1.612 | 77.736 | +1.668% |
| 2016 | 1.540666 | 82.168 | 1.556 | 81.393 | +0.952% |
| 2017 | 1.536306 | 86.403 | 1.536 | 86.403 | 0.000% |
| 2018 | 1.491996 | 95.630 | 1.492 | 95.622 | +0.008% |
| 2019 | 1.503330 | 104.708 | 1.503 | 104.708 | approximately 0.000% |
| 2020 | 1.529004 | 104.049 | 1.529 | 104.049 | 0.000% |
| 2021 | 1.501704 | 115.316 | 1.502 | 115.316 | approximately 0.000% |
| 2022 | 1.554252 | 131.219 | 1.554 | 127.686 | +2.767% |
| 2023 | 1.463334 | 144.672 | 1.592 | 138.113 | +4.749% |
| 2024 | 1.525358 | 157.578 | 1.641 | 146.491 | +7.568% |
| 2025 | 1.573152 | 172.198 | 1.740 | 155.724 | +10.579% |

The direct arithmetic decomposition identifies distinct periods:

- **2015–2016:** small PPP GDP differences (1.668% and 0.952%).
- **2017–2021:** PPP GDP agrees at displayed precision or within 0.008%; conversion factors also agree at displayed precision. Do not interpret tiny differences in rounded factors as meaningful methodological divergence.
- **2022:** WDI current-LCU GDP is 203.947bn TMT versus WEO 198.371bn, while both displayed PPP factors are 1.554. The PPP GDP gap is principally the domestic-currency GDP numerator difference already identified in field 15.
- **2023:** WDI current-LCU GDP is lower (211.704bn versus 219.848bn), but its PPP factor is also lower (1.463334 versus 1.592); the lower factor more than offsets the lower numerator, leaving WDI PPP GDP higher.
- **2024–2025:** current-LCU GDP agrees at displayed precision, while PPP factors diverge (1.525358 vs 1.641; 1.573152 vs 1.740). The PPP GDP gap is therefore attributable to the conversion-factor difference in these years.
- **2023** contains both numerator and factor effects.

The WEO PPP factor is displayed to three decimal places in the captured CSV. Reconstructing PPP GDP from displayed domestic-currency GDP divided by that rounded factor yields small differences (roughly 0.01–0.04bn) from the reported PPP GDP. Do not treat these rounding residuals as separate economic discrepancies.

The IMF WEO FAQ describes its PPP rates as based on ICP 2017–2021 benchmarks, extended backwards and forwards using growth in relative GDP deflators. The World Bank describes its WDI PPP series as using ICP benchmark years, interpolation between benchmarks and extrapolation outside them using relative inflation/deflator movements. World Bank ICP guidance also warns that ICP and WDI GDP, population and exchange-rate inputs can differ because ICP receives national inputs directly and they can differ by vintage or methodology. These are general provider methodologies; the exact Turkmenistan national-account and deflator inputs used for each captured year have not been established.

**Field 18 conclusion:** the WDI/WEO PPP comparison is effectively aligned through 2021, with small early differences. Divergence after 2021 separates into a 2022–2023 nominal GDP numerator component and an increasingly material 2023–2025 PPP-factor component. This does not establish which provider's PPP factor is preferable or identify the exact benchmark, deflator or vintage causing the post-2021 difference. The TurkmenStat June 2026 notice describes planned ICP and 2025 SNA technical assistance, not a completed new benchmark. Keep field 18 open and retain IMF WEO priority pending the separate approval process.

### Field 15–18 governance disposition

The field 15 domestic-currency comparison, field 16 population reconstruction and field 18 PPP decomposition are diagnostic country-case evidence only. They do not verify the country identity, establish complete vintage alignment, approve semantic equivalence, change source-selection policy, promote a release, or authorize canonical application. The WDI capture is a timestamped rolling-API snapshot, not a provider-declared vintage; the IMF input is the fixed October 2026 WEO release.
