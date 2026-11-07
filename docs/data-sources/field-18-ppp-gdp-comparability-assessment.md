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

For Guinea and CAR, the PPP GDP gaps are similar in scale to the nominal GDP gaps documented in the field 15/16 investigation. This is consistent with underlying national-accounts source-vintage differences contributing materially to the PPP GDP divergence. A full decomposition of nominal GDP and PPP conversion-factor effects has not yet been completed.

For Zimbabwe, the standout is an isolated WDI PPP GDP spike in 2017 relative to the adjacent WDI observations in the comparison. An IMF methodological paper documents a special adjustment for Zimbabwe's 2017 ICP PPP factor: it was converted from local currency to USD using exchange-rate data supplied by IMF desks before application to nominal GDP submitted in USD to WEO. This is a direct country-specific methodological difference and makes a simple comparison of the two series unsafe.

## Existing comparison evidence

The figures below summarize the existing read-only comparison. The country-year CSV remains the source of exact annual values; this document reports group summaries and only country-specific values independently corroborated by cited sources.

| Country | Median absolute relative difference, 2015–2025 | Direction |
|---|---:|---|
| Guinea | 57.18% | IMF higher in all 11 years |
| Central African Republic | 53.79% | IMF higher in all 11 years |
| Zimbabwe | 26.41% | Mixed direction |

For the full annual rows, signed and absolute differences, and IMF status hints, use the retained source report:
`reports/sources/imf-wdi-discrepancy-investigation/20261102T112847Z/assessment.md`.

The WDI API value for Zimbabwe 2017 in the project's comparison is an isolated discontinuity relative to adjacent years. However, the World Bank's WITS profile shows a different value (approximately US$104.36 billion) and identifies its PPP GDP data as based on the 2011 ICP round, while the current WDI series is based on the revised 2017/2021 ICP vintage. This is not a like-for-like validation of the current API value. The World Bank revised 2017 ICP results in its 2021 cycle using updated expenditure, regional PPP, population and market-exchange-rate data. The IMF separately documents a special conversion of Zimbabwe's 2017 ICP PPP factor using desk-supplied exchange rates before applying it to WEO nominal GDP in USD. The two providers' benchmark/currency handling is therefore materially different, but the current WDI 2017 observation cannot be labelled erroneous or anomalous until the exact current WDI and ICP benchmark records are acquired and reconciled.

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

For Guinea and CAR, the field 18 median PPP GDP gaps are similar in scale to the field 15 nominal GDP gaps documented in the companion assessment. That is consistent with PPP GDP inheriting much of the underlying nominal GDP source-vintage difference. However, this document does not quantify the separate contribution of nominal GDP and PPP conversion factors because a complete country-year reconstruction of both providers' implied PPP factors has not yet been completed.

## Status and limitations

- The IMF WEO export has no `LATEST_ACTUAL_ANNUAL_DATA` value for `PPPGDP`; all compared IMF PPP observations remain **unclassified** as actual/estimate/projected by the project's assessment tooling.
- The IMF WEO export does not supply reporting-period metadata for this series; do not infer calendar-year/fiscal-year conventions from the year label alone.
- The WDI API is rolling/live, not an immutable release. The comparison is not vintage-aligned.
- ICP PPPs are statistical estimates subject to sampling, measurement and classification errors; the World Bank cautions that they are not measures of currency under- or overvaluation.
- PPP GDP is not the same concept as nominal GDP in current USD. It is a volume-comparison measure converted using PPP factors; it must retain its international-dollar unit.
- The 2017 Zimbabwe adjustment in the IMF paper is documented in the 2020 quota-data methodology. The exact implementation in the October 2026 WEO vintage, the current WDI source record, and the revised ICP 2017 country record still require direct record-level confirmation.
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
- ICASEES, [Comptes Nationaux définitifs 2019–2021](https://www.icasees.org/index.php/publications/tableau-de-bord/telecharger/comptes-nationaux-definitifs-2019-2021-de-la-republique-centrafricaine), published 30 July 2026, CC BY 4.0.
- ICASEES, [GDP rebasing to 2019 base under SNA 2008](https://www.icasees.org/index.php/publications/tableau-de-bord/statistiques-structurelles/statistiques-economiques/comptes-nationaux/rebasage-du-pib-de-la-republique-centrafricaine-base-2019-scn-2008-aide-memoire-de-la-mission-conjointe-dexamen-des-resultats), published 7 August 2026.
- IMF, [Central African Republic 2025 Article IV/ECF review](https://www.imf.org/en/Publications/CR/Issues/2025/06/04/Central-African-Republic-Third-and-Fourth-Reviews-Under-the-Extended-Credit-Facility-Arrangement-568185), historical status before the July 2026 ICASEES release.


## Updated nominal-GDP decomposition context (2026-11-07)

The expanded WDI snapshot now shows that the large Guinea and CAR PPP gaps coexist with material local-currency GDP level differences against revised national accounts:

- **Guinea:** WDI current-LCU GDP for 2018–2022 reproduces the legacy INS/SCN 1993 series at published rounding precision. The new INS 2018-base SNA 2008 series is substantially higher. For 2024, the UNSD profile (sourced from INS for 2018–2024) reports GNF 311.077 trillion and US$36.465 billion, while WDI reports GNF 214.597 trillion and US$25.009 billion. This is a nominal national-accounts vintage issue before PPP conversion.
- **CAR:** WDI current-LCU GDP is 33–35% below definitive ICASEES 2019–2021 GDP. The WDI official and DEC alternative conversion factors are effectively identical in those years, so the nominal level difference is already present before USD conversion.

The WDI PPP series is arithmetically reproduced by current-LCU GDP divided by the WDI GDP PPP conversion factor. This confirms the WDI series' internal arithmetic only. It does not validate the PPP factor's benchmark, vintage, imputation or extrapolation method, nor does it show that the IMF uses the same nominal GDP input. For CAR and Guinea, the local-currency GDP vintage mismatch is a material component of the PPP discrepancy; a separate reconciliation of the PPP factor and benchmark remains necessary. The field 18 disposition therefore remains **not yet demonstrated comparable**, and IMF priority is unchanged.
