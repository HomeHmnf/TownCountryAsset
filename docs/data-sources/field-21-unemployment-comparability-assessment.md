# Field 21 unemployment comparability assessment

**Assessment date:** 2026-11-02  
**WP1.5 field:** 21 — unemployment  
**Scope:** IMF WEO `LUR` versus WDI `SL.UEM.TOTL.ZS`, with national statistical office corroboration for Bahrain, Moldova and the Philippines.  
**Disposition:** retain IMF WEO as the current priority source. Do not treat the WDI ILO-modelled series as a like-for-like replacement for country-specific national-definition series.

## Executive finding

The three targeted country investigations show that large IMF–WDI differences do not, by themselves, indicate an IMF error:

- **Bahrain:** the IMF WEO value aligns with an annual citizen unemployment rate in GCC-STAT. The apparent 2016 conflict with Bahrain's annual API dataset is best classified as a likely reference-period mismatch: the API's 4.3% matches the Ministry's December rate, while GCC-STAT's annual citizen rate is 3.9%, matching WEO. The Ministry's stated 4.0% annual average remains 0.1 percentage point above GCC-STAT.
- **Moldova:** IMF WEO closely matches the National Bureau of Statistics' national LFS rates for 2024 and 2025 (3.955% vs 4.0%; 3.802% vs 3.8%). However, Moldova changed its LFS sample, population weights and methodology in 2025; the NBS warns that 2025 is not fully comparable with 2019–2024.
- **Philippines:** IMF WEO closely matches PSA's annual LFS rates for 2023–2025 (4.358% vs 4.4%; 3.817% vs 3.8%; 4.208% vs 4.2%). PSA's post-April-2005 unemployment definition and annualized LFS methodology are documented.

WDI `SL.UEM.TOTL.ZS` is explicitly an ILO modelled estimate, with imputation for missing observations. It is not equivalent by default to a country's national survey series or administrative-register measure. The World Bank's metadata cautions that imputed observations have high uncertainty and should not be used for country comparisons/rankings where they are not grounded in national data.

## Country findings

### Bahrain

The official Bahrain Open Data Portal annual dataset `03-unemployment-yearly` was acquired through the project's API adapter. Its 2016 total-rate value is 4.3%; the Ministry of Labour's February 2017 clarification identifies 4.3% as the December 2016 rate and gives 4.0% as the 2016 annual average. GCC-STAT's *Labour Statistics Bulletin in GCC Countries 2016* reports 3.9% for Bahrain's annual citizen unemployment rate and explicitly states that Bahrain unemployment data are for citizens only and sourced from Ministry of Labour registers. IMF WEO `BHR.LUR.A` is 3.9% in 2016.

The official API total-rate values match WEO exactly for 2017–2025. The best-supported interpretation is that the API's 2016 value is a year-end/December rate, while WEO is aligned with the annual citizen rate. The API does not itself expose a reference-period field, so this remains a strongly supported interpretation rather than a formal API metadata declaration. The Ministry annual average (4.0%) and GCC-STAT value (3.9%) differ by 0.1 pp; the available evidence does not establish why.

The WEO country metadata identifies a national definition and cites LMRA, SIO and IMF staff projections. The acquired national dataset is explicitly Bahraini-focused. WDI's modelled estimate is a different statistical product and should not be substituted. See [Bahrain unemployment series assessment](bahrain-unemployment-series-assessment.md) for the complete year table, sex breakdown, snapshot provenance and detailed evidence.

### Moldova

The National Bureau of Statistics (NBS) reports an unemployment rate of **4.0% in 2024** and **3.8% in 2025** from its Labour Force Survey. The corresponding IMF WEO `MDA.LUR.A` values are **3.955%** and **3.802%**. Differences are only 0.045 and 0.002 percentage points, respectively, consistent with rounding.

The NBS 2025 statistical databank notes a material survey redesign in 2025:
- 2019–2024 used the EMDOS 2 master sample, based on the 2014 Population and Housing Census.
- 2025 introduced the EMDOS 3 master sample.
- 2025 expansion factors and relative indicators use the usually resident population recalculated from the 2024 census.
- The NBS states that the adjustments caused a break in the time series and that 2025 data are not fully comparable with corresponding previous years.

The current NBS LFS methodology is approved by Order No. 84 of 11 October 2024, with amendments in June and December 2025. The NBS describes the source as a continuous household LFS, with quarterly and annual dissemination. The 2024 and 2025 national rates provide strong direct corroboration of the WEO values, but the 2025 break must be retained as a comparability caveat. Do not interpret the near match as proof that every historical WEO year uses an unchanged survey basis.

The comparison investigation's older secondary-source indications for 2019–2023 should not be elevated to primary-source corroboration without extracting the corresponding NBS table vintage. The current evidence securely establishes the 2024 and 2025 comparisons.

### Philippines

The Philippine Statistics Authority (PSA) reports annual unemployment rates of **4.4% in 2023**, **3.8% in 2024** and **4.2% in 2025**. IMF WEO `PHL.LUR.A` reports **4.358%**, **3.817%** and **4.208%**, respectively. The differences are 0.042, 0.017 and 0.008 percentage points, consistent with the PSA's one-decimal published values.

PSA defines the unemployment rate as unemployed persons divided by persons in the labour force, multiplied by 100. Its metadata says the current unemployment definition was adopted from April 2005: persons aged 15 and over without work, currently available for work, and seeking work, or not seeking for specified valid reasons. The PSA notes that annual estimates are computed using the annualized-estimates method adopted by PSA Board Resolution No. 14, Series of 2021. Since 2021 the LFS has been conducted monthly; the annual estimate aggregates the January–December survey rounds.

For January 2019–December 2025, PSA metadata identifies the 2015-based population projections. The 2025 annual release was issued on 19 March 2026 and describes its annual result as preliminary. The IMF WEO export labels 2025 as the latest actual annual year for the Philippines, but the exact country-year source vintage and IMF compilation process are not independently reproduced here. The numerical match across 2023–2025 is nevertheless strong primary-source corroboration.

PSA metadata also documents that the 2005 definition change preceded this comparison period. Therefore, the earlier IMF note about pre-2005 national-definition observations does not explain the 2015–2025 differences.

## Interpretation of WDI's modelled series

WDI `SL.UEM.TOTL.ZS` is “Unemployment, total (% of total labour force) (modelled ILO estimate)”. Its metadata describes an ILOEST series that uses country-reported observations and imputes missing data to support consistent regional and global coverage. The World Bank cautions that imputed observations are not based on national data, carry high uncertainty, and should not be used for country comparisons/rankings. It separately publishes `SL.UEM.TOTL.NE.ZS`, a national-estimate series; that indicator also requires country-specific interpretation and does not automatically share the same reference population, source or methodology as the IMF series.

Consequently:
- Do not assume the modelled ILO estimate is the preferred value merely because it is internationally harmonized.
- Do not assume national estimates are automatically comparable across countries.
- Keep the modelled and national-estimate series distinct in diagnostics and provenance.
- For Bahrain, explicitly preserve the citizen administrative-register population coverage.
- For Moldova, preserve the 2025 survey redesign and break in series.
- For the Philippines, preserve the annualized LFS convention and the 2025 preliminary status.

## Source-selection disposition

1. Keep field 21's existing `imf_weo` priority-source assignment unchanged.
2. Do not promote WDI `SL.UEM.TOTL.ZS` to priority or fallback solely on the basis of its modelled status.
3. Do not create country-specific manual overrides from this investigation.
4. Keep country-level source/methodology metadata and observation status in the evidence trail.
5. If a future source-policy change is proposed, first acquire immutable WDI snapshots and the relevant national source vintages, compare exact reference periods/population universes, and prepare a separate compatibility review and approval artifact.

This assessment is evidence and interpretation only. It does not change source registry entries, source-selection policy, approvals, release ledgers, or canonical SQLite. No WP1.5 observations are imported or promoted by this document.

## Primary references

- Moldova NBS, [Labour Force: Employment and Unemployment in 2025](https://statistica.gov.md/index.php/en/labour-force-employment-and-unemployment-in-2025-9430_62388.html), 1 April 2026.
- Moldova NBS, [Labour Force in the Republic of Moldova: Employment and unemployment in 2024](https://statistica.gov.md/index.php/en/labour-force-in-the-republic-of-moldova-employment-and-unemployment-in-2024-9430_61728.html), 1 April 2025.
- Moldova NBS, [Statistical databank: Labour force participation, employment and unemployment rates, 2019–2025](https://statbank.statistica.md/PxWeb/pxweb/en/30%20Statistica%20sociala/30%20Statistica%20sociala__03%20FM__03%20MUN__MUN010/MUN111000reg.px/), including the 2025 comparability note.
- Moldova NBS, [Labour Force Survey Methodology (2025)](https://statistica.gov.md/files/files/Metadate/alte/Methodology_LFS_2026_en.pdf), approved 11 October 2024 and amended in 2025.
- Philippines PSA, [2025 Annual Provincial Labor Market Statistics (Preliminary Results)](https://psa.gov.ph/statistics/labor-force-survey/press-release/node/1684083111), 19 March 2026.
- Philippines PSA, [OpenSTAT LFS metadata and definitions](https://openstat.psa.gov.ph/PXWeb/pxweb/en/DB/DB__1B__LFS/0121B3FEMP4.px/).
- Philippines PSA, [Unemployment rate definition and annual-estimate notes](https://openstat.psa.gov.ph/PXWeb/pxweb/en/DB/DB__1B__LFS/0021B3FKEI2.px/).
- World Bank, WDI metadata for [SL.UEM.TOTL.ZS](https://api.worldbank.org/v2/indicator/SL.UEM.TOTL.ZS?format=json).
- Bahrain evidence and citations are recorded in [Bahrain unemployment series assessment](bahrain-unemployment-series-assessment.md).
