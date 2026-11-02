# PPP GDP comparability investigation

**Assessment date:** 2026-11-02  
**WP1.5 field:** 18 — GDP at current PPP prices  
**Compared series:** IMF WEO `PPPGDP` versus WDI `NY.GDP.MKTP.PP.CD`  
**Investigation window:** 2015–2025  
**Disposition:** retain the current IMF WEO priority assignment. Do not treat the WDI series as an automatic substitute; preserve benchmark, national-accounts vintage and country-specific currency-conversion context.

## Executive summary

The read-only comparison shows three distinct patterns:

| Country | Median absolute relative difference, 2015–2025 | Direction |
|---|---:|---|
| Guinea | 57.18% | IMF higher in all 11 years |
| Central African Republic | 53.79% | IMF higher in all 11 years |
| Zimbabwe | 26.41% | Mixed; WDI has a very large 2017 spike |

For Guinea and CAR, the PPP GDP gaps are largely inherited from the underlying nominal GDP/national-accounts levels rather than being explained solely by different PPP conversion factors. In 2024:
- Guinea: IMF PPP GDP / IMF nominal GDP is about 2.784; WDI PPP GDP / WDI nominal GDP is about 2.698. The implied multipliers differ by only about 3.2%, while the nominal GDP series differ by 53.3%.
- CAR: the corresponding multipliers are about 2.599 and 2.451, a difference of about 6.0%, while nominal GDP differs by about 50.0%.

For Zimbabwe, the standout is 2017: WDI PPP GDP is approximately US$159.3 billion versus IMF WEO approximately US$63.4 billion, while the surrounding WDI years are approximately US$62.4 billion (2016) and US$60.0 billion (2018). An IMF methodological paper documents a special adjustment for Zimbabwe's 2017 ICP PPP factor: it was converted from local currency to USD using exchange-rate data supplied by IMF desks before application to nominal GDP submitted in USD to WEO. This is a direct country-specific methodological difference and makes a simple comparison of the two series unsafe.

## Existing comparison values

The figures below come from the project's fixed October 2026 IMF WEO CSV and a live WDI API run. They are not a vintage-aligned source comparison.

### Guinea

| Year | IMF WEO PPP GDP (international $) | WDI PPP GDP (international $) | IMF relative to WDI |
|---:|---:|---:|---:|
| 2015 | 42.176 bn | 22.707 bn | +85.7% |
| 2016 | 46.637 bn | 27.229 bn | +71.3% |
| 2017 | 53.251 bn | 33.281 bn | +60.0% |
| 2018 | 54.637 bn | 36.138 bn | +51.2% |
| 2019 | 61.748 bn | 40.482 bn | +52.5% |
| 2020 | 74.182 bn | 44.551 bn | +66.5% |
| 2021 | 78.952 bn | 51.261 bn | +54.0% |
| 2022 | 88.423 bn | 57.088 bn | +54.9% |
| 2023 | 97.789 bn | 62.481 bn | +56.5% |
| 2024 | 106.781 bn | 67.458 bn | +58.3% |
| 2025 | 117.115 bn | 74.512 bn | +57.2% |

The Guinea national-accounts rebasing evidence is described in the [field 15/16 GDP assessment](field-15-16-gdp-comparability-assessment.md). The 2018-base SNA 2008 rebasing raised the GDP level by 51.4%; the current UN Statistics Division profile uses INS nominal values for 2018–2024. The WEO/WDI PPP gap is similar in scale to the nominal GDP gap. The near similarity of the 2024 implied PPP multipliers shows that the bulk of the PPP GDP difference is the underlying nominal GDP level, not a 57% disagreement in the PPP factor itself.

### Central African Republic

| Year | IMF WEO PPP GDP (international $) | WDI PPP GDP (international $) | IMF relative to WDI |
|---:|---:|---:|---:|
| 2015 | 5.474 bn | 3.559 bn | +53.8% |
| 2016 | 5.789 bn | 3.894 bn | +48.7% |
| 2017 | 6.159 bn | 4.237 bn | +45.4% |
| 2018 | 6.419 bn | 4.419 bn | +45.3% |
| 2019 | 7.307 bn | 4.870 bn | +50.0% |
| 2020 | 8.229 bn | 5.360 bn | +53.5% |
| 2021 | 8.887 bn | 5.769 bn | +54.0% |
| 2022 | 9.703 bn | 6.208 bn | +56.3% |
| 2023 | 10.062 bn | 6.482 bn | +55.2% |
| 2024 | 10.725 bn | 6.743 bn | +59.1% |
| 2025 | 11.647 bn | 7.244 bn | +60.8% |

CAR has the same material nominal GDP national-accounts vintage/compilation gap described in the field 15/16 assessment. The 2024 implied PPP multipliers differ by approximately 6%, far less than the approximately 50% nominal GDP gap. This supports the interpretation that most of the PPP GDP discrepancy is inherited from the underlying national-accounts GDP levels. The remaining conversion-factor difference is not zero and should not be ignored.

### Zimbabwe

| Year | IMF WEO PPP GDP (international $) | WDI PPP GDP (international $) | IMF relative to WDI |
|---:|---:|---:|---:|
| 2015 | 55.505 bn | 58.257 bn | -4.7% |
| 2016 | 56.700 bn | 62.423 bn | -9.2% |
| 2017 | 63.379 bn | 159.330 bn | -60.2% |
| 2018 | 62.043 bn | 60.031 bn | +3.4% |
| 2019 | 75.853 bn | 63.619 bn | +19.2% |
| 2020 | 81.074 bn | 64.879 bn | +25.0% |
| 2021 | 96.802 bn | 76.255 bn | +26.9% |
| 2022 | 109.614 bn | 86.693 bn | +26.4% |
| 2023 | 119.729 bn | 94.711 bn | +26.4% |
| 2024 | 124.935 bn | 98.690 bn | +26.6% |
| 2025 | 138.849 bn | 109.679 bn | +26.6% |

The 2017 WDI value is an isolated discontinuity: it is more than 2.5 times the adjacent 2016 and 2018 WDI observations. The IMF value is much smoother across those years. The anomaly must not be allowed to dominate the interpretation of the full 11-year median.

## Methodological evidence

### General ICP/WDI methodology

The World Bank's ICP 2021 cycle provides:
- a new 2021 benchmark;
- revised 2017 results;
- PPP time series for 2018–2020;
- extrapolated GDP PPPs for 2022–2023.

The ICP 2021 results use SNA 2008 and national accounts expenditure data. The World Bank explains that PPPs for nonparticipating economies are imputed using regression models. It also explicitly notes that GDP, population and market-exchange-rate inputs used in the ICP can differ from WDI because of differences in data vintage or statistical methods.

WDI PPP conversion factors are extrapolated beyond the benchmark years using changes in the GDP implicit deflator (for GDP PPPs). The IMF WEO FAQ describes its own PPP method: WEO uses ICP 2017–2021 PPPs, extends them backward and forward using relative GDP deflators, updates non-survey-year implied conversion rates with the latest nominal GDP and relative deflators, and updates PPPGDP using the latest WEO data.

Thus, even where both products reference the same ICP cycles, they need not be numerically identical: the underlying nominal GDP series, data vintages, deflator histories and update cutoffs can differ.

### Zimbabwe — explicit IMF special adjustment

The IMF's March 2021 *2020 Quota Data Update* documents a specific adjustment for Zimbabwe:
- the 2017 ICP PPP factors were converted from local currencies to USD using exchange-rate data supplied by IMF desks;
- those converted PPP factors were then applied to the respective nominal GDP series, which were submitted in USD to the WEO database.

The same paper identifies Zimbabwe as an outlier in the comparison between actual 2017 ICP PPP factors and extrapolated PPP factors. It explains that 2017 ICP factors and the WEO PPP calculation were not simply a mechanical use of the same local-currency factor.

This is direct evidence that the IMF's Zimbabwe PPP treatment includes a country-specific conversion step. It is not, by itself, proof that the WDI 2017 value is erroneous; it does establish that the two providers' benchmark-conversion pipelines differ and that a direct series substitution is unsafe. The 2017 WDI spike should be investigated against the exact ICP 2017 and 2021 country-level PPP records, local-currency nominal GDP, currency/redenomination treatment, and source vintages before any source-policy decision.

### Guinea and CAR — nominal GDP dominates the PPP gap

For Guinea, the 2024 WEO and WDI PPP GDP values differ by 58.3%, but their implied PPP multipliers differ by only about 3.2%. The official 2018-base rebasing and current INS/UNSD GDP level are close to WEO nominal GDP and far above the WDI nominal GDP in the comparison. The PPP discrepancy is therefore largely a reflection of the nominal GDP vintage gap.

For CAR, the 2024 PPP GDP difference is 59.1%, while the implied PPP multipliers differ by about 6.0%. The country has a documented national-accounts vintage/compilation gap, with production and retropolation under the 2008 SNA still being developed. This supports the nominal-GDP explanation for most of the PPP gap, but the residual PPP factor difference remains.

## Status and limitations

- The IMF WEO export has no `LATEST_ACTUAL_ANNUAL_DATA` value for `PPPGDP`; all compared IMF PPP observations remain **unclassified** as actual/estimate/projected by the project's assessment tooling.
- The IMF WEO export does not supply reporting-period metadata for this series; do not infer calendar-year/fiscal-year conventions from the year label alone.
- The WDI API is rolling/live, not an immutable release. The comparison is not vintage-aligned.
- ICP PPPs are statistical estimates subject to sampling, measurement and classification errors; the World Bank cautions that they are not measures of currency under- or overvaluation.
- PPP GDP is not the same concept as nominal GDP in current USD. It is a volume-comparison measure converted using PPP factors; it must retain its international-dollar unit.
- The 2017 Zimbabwe adjustment in the IMF paper is documented in the 2020 quota-data methodology. The exact implementation in the October 2026 WEO vintage and the exact WDI source records for 2017 still require direct record-level confirmation.
- No cause has been established for every year of the Guinea or CAR residual PPP factor differences.

## Source-selection disposition

1. Retain `imf_weo` as the existing priority source for field 18.
2. Do not promote WDI `NY.GDP.MKTP.PP.CD` to priority/fallback based on this comparison.
3. Preserve the country-specific national-accounts vintage and conversion evidence:
   - Guinea: 2018-base SNA 2008 rebasing and revised INS series.
   - CAR: unresolved national-accounts vintage/compilation gap and ongoing 2008-SNA retropolation.
   - Zimbabwe: IMF desk-exchange-rate adjustment for 2017 ICP PPP factors and the isolated WDI 2017 discontinuity.
4. Do not infer IMF actual/estimate/projected status for PPPGDP from nominal GDP metadata.
5. If field 18 is reconsidered, acquire immutable WDI and ICP benchmark inputs and reproduce each provider's implied PPP conversion factors and underlying nominal GDP series before proposing any policy change.

This is a read-only evidence assessment. It changes no source registry, source-selection policy, approval, release ledger, or canonical SQLite data.

## Primary references

- World Bank, [International Comparison Program — Data](https://www.worldbank.org/en/programs/icp/data), ICP 2021, revised ICP 2017, 2018–2020 PPP time series, and 2022–2023 extrapolations.
- World Bank, [International Comparison Program — FAQ](https://www.worldbank.org/en/programs/icp/faq), national-source vintage differences between ICP and WDI and PPP update methodology.
- World Bank, [ICP methodology](https://www.worldbank.org/en/programs/icp/methodology), PPP imputation and interpolation/extrapolation methodology.
- World Bank Data Help Desk, [Extrapolating PPP conversion factors](https://datahelpdesk.worldbank.org/knowledgebase/articles/665452-how-do-you-extrapolate-the-ppp-conversion-factors).
- IMF, [WEO Frequently Asked Questions](https://www.imf.org/en/publications/weo/frequently-asked-questions), WEO ICP 2017–2021 PPP benchmark and deflator extension methodology.
- IMF, [2020 Quota Data Update, March 2021](https://www.imf.org/-/media/Files/Publications/PP/2021/English/PPEA2021016.ashx), paragraph 27 and related discussion of Zimbabwe's 2017 PPP-factor conversion.
- IMF, [Zimbabwe 2020 Article IV consultation](https://www.imf.org/en/news/articles/2020/02/26/pr2072-zimbabwe-imf-executive-board-concludes-2020-article-iv-consultation), currency introduction, exchange-rate market, inflation and nominal GDP context.
- Guinea, [field 15/16 GDP comparability assessment](field-15-16-gdp-comparability-assessment.md), including the 2018 rebasing and 2024 national-accounts corroboration.
- IMF, [Central African Republic 2025 Article IV/ECF review](https://www.imf.org/en/Publications/CR/Issues/2025/06/04/Central-African-Republic-Third-and-Fourth-Reviews-Under-the-Extended-Credit-Facility-Arrangement-568185), national-accounts compilation and 2008-SNA retropolation context.
