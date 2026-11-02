# GDP and GDP-per-capita comparability investigation

**Assessment date:** 2026-11-02  
**WP1.5 fields:** 15 — GDP; 16 — GDP per capita  
**Compared series:** IMF WEO `NGDPD` / `NGDPDPC`; WDI `NY.GDP.MKTP.CD` / `NY.GDP.PCAP.CD`  
**Investigation window:** 2015–2025  
**Disposition:** retain the current IMF WEO priority assignment. The three persistent outliers have material country-specific comparability issues; no WDI fallback or manual override is justified by this investigation.

## Executive summary

All three countries show IMF values consistently above WDI for both fields over the comparison window. The median absolute relative differences in the existing read-only comparison are:

| Country | Field 15 GDP | Field 16 GDP per capita | Direction |
|---|---:|---:|---|
| Turkmenistan | 55.20% | 71.80% | IMF higher in every year |
| Guinea | 52.53% | 45.90% | IMF higher in every year |
| Central African Republic | 51.67% | 53.02% | IMF higher in every year |

The evidence points to different issues by country:

- **Turkmenistan:** the World Bank documents multiple/dual exchange-rate activity and an alternative conversion factor for 2019–2025. This is a major warning for comparing current-US-dollar GDP. The exact contribution to the WDI GDP series is not fully demonstrated, and the divergence starts increasing before the alternative-factor period.
- **Guinea:** a documented 2018-base national-accounts rebasing raised the GDP level by 51.4%. The current UN Statistics Division national-accounts profile for 2024 is close to IMF WEO and materially above the WDI values in the comparison. This is strong evidence that the WDI series in the compared vintage does not yet reflect the revised national-accounts level consistently.
- **Central African Republic (CAR):** historical national-accounts releases, a major data-vintage gap, and continuing work to produce/revise accounts under the 2008 SNA are documented. IMF staff reports show a much higher nominal GDP level than the WDI comparison. The precise source/vintage break responsible for the full gap remains unresolved.

GDP-per-capita differences broadly follow the GDP differences. They should not be treated as independent confirmation: per-capita GDP also depends on each provider's population denominator and vintage.

## Existing comparison evidence

The figures below summarize the existing read-only comparison. The country-year CSV remains the source of exact annual values; this document deliberately reports robust group summaries rather than transcribing unverified row-level numbers.

| Country | Field 15 GDP median absolute relative difference | Field 16 GDP per capita median absolute relative difference | Direction |
|---|---:|---:|---|
| Turkmenistan | 55.20% | 71.80% | IMF higher in every year |
| Guinea | 52.53% | 45.90% | IMF higher in every year |
| Central African Republic | 51.67% | 53.02% | IMF higher in every year |

For the full annual rows, signed and absolute differences, and IMF status hints, use the retained source report:
`reports/sources/imf-wdi-discrepancy-investigation/20261102T112847Z/assessment.md`.

## Country investigations

### Turkmenistan — exchange-rate conversion risk

The World Bank's WDI country metadata explicitly states that multiple or dual exchange-rate activity exists in Turkmenistan and must be accounted for in underlying statistics. It says an alternative conversion factor (`PA.NUS.ATLS`) is calculated using an inflation-adjustment method and applies for **2019–2025**. The World Bank explains that the alternative factor is intended to better reflect economic reality where the official exchange rate does not reflect the rate effectively applied to actual foreign-exchange transactions.

This is highly relevant to `NY.GDP.MKTP.CD`, a current-US-dollar GDP series. The FRED/WDI series notes explain that local-currency GDP is converted to US dollars using single-year official exchange rates, with alternative conversion factors used for some countries where the official rate is not representative.

The observed pattern is consistent with a material conversion/vintage issue:
- 2015 IMF and WDI GDP are virtually identical.
- The gap grows to 8.6% in 2016 and 13.7% in 2017.
- It jumps to 56.6% in 2018 and remains large through 2025.
- The largest annual GDP gap is 87.9% in 2021.

The World Bank metadata's explicit 2019–2025 alternative-factor period does **not** by itself explain the 2018 jump, nor does it prove that the alternative factor is applied directly in every observation of the GDP indicator. Treat the exchange-rate issue as a strong comparability warning and plausible contributor, not a complete numerical reconciliation.

The State Committee of Statistics also reports ongoing modernization of national accounts and statistical methods with World Bank technical assistance, including implementation work for the 2025 SNA and the International Comparison Program. This is additional reason to preserve the exact source vintage and methodology.

**Assessment:** exchange-rate conversion and source-vintage incompatibility are strongly implicated; exact series conversion is not fully reconciled. Do not choose either USD series as universally correct from this comparison alone.

### Guinea — 2018 national-accounts rebasing

The Guinean Ministry of Planning, Cooperation and International Development reports that the National Institute of Statistics rebased GDP to **2018** under the **2008 System of National Accounts**. It states that the revision raised the GDP level from **GNF 106,845.3 billion to GNF 161,766.5 billion**, an increase of **51.4%**, through better coverage of the national economy.

The latest UN Statistics Division Annual National Accounts country profile (January 2026 upload) reports Guinea's 2024 GDP at current prices as **GNF 311,076.517 billion**, or **US$36.465 billion**, and GDP per capita of **US$2,473**. The UN metadata records the 2018–2024 GDP series as sourced from the Institut national de la statistique, République de Guinée. This current official national-accounts level is consistent with the IMF/WDI comparison's finding that the IMF series is materially closer to the revised national-accounts level than the WDI series.

The 51.4% rebasing uplift is strikingly close to the approximately 50–53% IMF/WDI GDP gaps over 2015–2025. The match is especially persuasive for the later years where the official rebased series is explicitly used by UNSD. The 2015–2017 portion predates the 2018-based series, so the same numerical explanation should not automatically be projected backwards.

**Assessment:** the WDI series used in the comparison appears not to reflect the rebased national-accounts level consistently, while IMF WEO is much closer to the latest INS/UNSD series. This is strong evidence of a national-accounts vintage/rebasing issue, not proof that every IMF year is a direct national observation. Preserve the 2025 WEO status hint (after latest actual year) and do not relabel projections as actuals.

### Central African Republic — unresolved national-accounts vintage and compilation gap

The IMF reported in 2019 that CAR authorities had released actual national accounts for **2005–2017**, the first release by the national statistical institute since the 2013 crisis. The data followed the **1993 SNA**, used **2005 as the base year**, and revised 2017 nominal GDP upward by **7%** relative to the prior estimates. The IMF report also recorded the authorities' intention at that time to move to the 2008 SNA and a 2017 base year.

In the May 2025 IMF country report, the authorities state that, with IMF technical assistance and World Bank support, they are committed to producing national accounts for 2020 and 2021 and initiating retropolation in line with the **2008 SNA**. The same report's macroeconomic tables show nominal GDP in CFA francs rising from CFAF 1,564 billion in 2015 to CFAF 2,684 billion in 2024 and CFAF 2,922 billion in 2025 (the latter is a projection in that report). The report identifies the sources as CAR authorities and IMF staff estimates/projections.

By contrast, WDI current-USD GDP in the comparison is US$2.751 billion for 2024 and US$3.066 billion for 2025, versus IMF WEO's US$4.126 billion and US$4.636 billion. The gap is persistent and similar in percentage terms across the period. The WDI series therefore does not align with the nominal GDP level in the later IMF staff-report table.

The 2019 7% upward revision alone is far too small to explain a persistent approximately 50% difference. The evidence of ongoing 2008-SNA retropolation and missing/being-produced national accounts for 2020–2021 is consistent with a substantial vintage/compilation gap, but the reviewed sources do not establish the precise point at which the WDI and WEO series diverged or which underlying national-accounts release each provider used for every year.

**Assessment:** material source-vintage/compilation incompatibility is confirmed; the exact cause and correct canonical series remain unresolved. Do not attribute the whole difference to the 2017 revision or assume WEO is correct solely because it is higher.

## GDP-per-capita interpretation

GDP per capita is not an independent observation of output. It is nominal GDP divided by a population series. In the three countries, field 16 discrepancies have the same direction and broadly similar scale as field 15. The variation in the ratios (particularly Turkmenistan and Guinea) means population denominator/vintage differences may also contribute. A separate population-denominator reconstruction would be needed to isolate the GDP numerator from population effects.

For all three countries, the IMF/WDI comparison uses the same year labels and calendar-year IMF reporting metadata. That does not eliminate differences in national-accounting vintages, exchange-rate conversion, population reference date, or revisions.

## Source-selection disposition

1. Retain `imf_weo` as the existing priority source for fields 15 and 16.
2. Do not promote WDI GDP or GDP per capita to priority/fallback on the basis of this comparison.
3. Do not create country-specific manual overrides from these investigations.
4. For Guinea, preserve the 2018-base SNA 2008 rebasing evidence and the INS/UNSD corroboration; investigate the exact WDI vintage before any future substitution.
5. For Turkmenistan, preserve the 2019–2025 dual-exchange-rate warning and the unresolved 2018 onset.
6. For CAR, preserve the unresolved national-accounts vintage/compilation gap; do not treat the 2017 7% revision as a sufficient explanation.
7. Keep GDP and GDP-per-capita source status and population provenance distinct. Do not infer actual status from a country-level GDP series alone.

Any future source-policy change requires immutable, vintage-aligned source snapshots, a country-specific normalization/compatibility review, and a separate approval artifact. This assessment is read-only: it changes no source registry, selection policy, approval, release ledger, or canonical SQLite data.

## Primary references

- State Committee of Statistics of Turkmenistan, [National accounts in statistics are improved](https://editor.stat.gov.tm/en/news/204), 17 January 2025.
- State Committee of Statistics of Turkmenistan, [The national statistical system of Turkmenistan is being improved](https://editor.stat.gov.tm/en/news/359), 23 June 2026.
- World Bank, [Turkmenistan WDI country metadata](https://databank.worldbank.org/metadataglossary/world-development-indicators/country/TKM), especially Special Notes on dual exchange rates and alternative conversion factors.
- World Bank/FRED, [GDP (current US$), Turkmenistan](https://fred.stlouisfed.org/series/MKTGDPTMA646NWDB), source note for USD conversion.
- Guinea Ministry of Planning, Cooperation and International Development, [2024 macroeconomic framework and GDP rebasing](https://mpci.gov.gn/index.php/cadrage-macroeconomique-2024-le-ministre-ismael-nabe-met-laccent-sur-la-transformation-structurelle-et-la-credibilite-internationale-de-la-guinee/).
- UN Statistics Division, [Guinea national accounts country profile](https://unstats.un.org/unsd/snaama/CountryProfile?ccode=324), January 2026 upload.
- UN Statistics Division, [Guinea GDP metadata](https://unstats.un.org/unsd/snaama/Metadata/?countrycode=324&groupid=101), GDP 2018–2024 from INS.
- IMF, [Central African Republic: Sixth Review under the ECF Arrangement, Country Report 19/216](https://www.elibrary.imf.org/view/journals/002/2019/216/article-A001-en.xml), national-accounts release for 2005–2017 and 7% revision to 2017 nominal GDP.
- IMF, [Central African Republic: Third and Fourth Reviews, Country Report 25/140](https://www.imf.org/en/Publications/CR/Issues/2025/06/04/Central-African-Republic-Third-and-Fourth-Reviews-Under-the-Extended-Credit-Facility-Arrangement-568185), nominal GDP table and 2008-SNA retropolation commitment.
- World Bank, [GDP (current US$), Central African Republic](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD?locations=CF).
- World Bank, [Why do countries revise their national accounts?](https://datahelpdesk.worldbank.org/knowledgebase/articles/680284-why-do-countries-revise-their-national-accounts).
- IMF, [WEO Frequently Asked Questions](https://www.imf.org/en/publications/weo/frequently-asked-questions), country-specific historical revisions and staff-estimate methodology.
