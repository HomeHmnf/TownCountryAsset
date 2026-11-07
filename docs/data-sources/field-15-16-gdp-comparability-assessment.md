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

The 2019 7% upward revision alone is far too small to explain a persistent approximately 50% difference. The newly published 2019–2021 accounts and 2019-base rebasing provide a current official benchmark against which WEO and WDI must now be tested. The earlier 2025 status description is no longer current. The exact contribution of the revised national accounts to the observed WEO/WDI gap remains unquantified until the ICASEES tables are extracted and compared year-by-year with both providers' source vintages.

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
- ICASEES, [Comptes Nationaux définitifs 2019–2021](https://www.icasees.org/index.php/publications/tableau-de-bord/telecharger/comptes-nationaux-definitifs-2019-2021-de-la-republique-centrafricaine), published 30 July 2026, CC BY 4.0; definitive accounts prepared under SNA 2008.
- ICASEES, [GDP rebasing to 2019 base under SNA 2008](https://www.icasees.org/index.php/publications/tableau-de-bord/statistiques-structurelles/statistiques-economiques/comptes-nationaux/rebasage-du-pib-de-la-republique-centrafricaine-base-2019-scn-2008-aide-memoire-de-la-mission-conjointe-dexamen-des-resultats), published 7 August 2026; documentation of improved coverage and methods.
- IMF, [Central African Republic: Third and Fourth Reviews, Country Report 25/140](https://www.imf.org/en/Publications/CR/Issues/2025/06/04/Central-African-Republic-Third-and-Fourth-Reviews-Under-the-Extended-Credit-Facility-Arrangement-568185), historical statement of the authorities' commitment before the 2026 ICASEES release.
- World Bank, [GDP (current US$), Central African Republic](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD?locations=CF).
- World Bank, [Why do countries revise their national accounts?](https://datahelpdesk.worldbank.org/knowledgebase/articles/680284-why-do-countries-revise-their-national-accounts).
- IMF, [WEO Frequently Asked Questions](https://www.imf.org/en/publications/weo/frequently-asked-questions), country-specific historical revisions and staff-estimate methodology.


## Updated local-currency vintage reconciliation (2026-11-07)

The expanded WDI snapshot adds the supporting series `NY.GDP.MKTP.CN`, `PA.NUS.FCRF`, `PA.NUS.ATLS` and `SP.POP.TOTL`. This moves the CAR and Guinea cases beyond a comparison of USD-converted values: the national-currency GDP numerator can now be compared directly with the latest official national-accounts publications.

### Guinea — legacy WDI local-currency series identified

The WDI current-LCU GDP observations in the 2026-11-07 snapshot reproduce the older INS/SCN 1993 series published in the INS annual yearbook `La Guinée en chiffres 2023` at the reported billion-GNF precision:

| Year | WDI current LCU (billion GNF) | Older INS/SCN 1993 value (billion GNF) | INS 2018-base SNA 2008 value (billion GNF) | New INS value status |
|---:|---:|---:|---:|---|
| 2018 | 106,845.292 | 106,845 | 161,539 | definitive |
| 2019 | 123,457.571 | 123,458 | 188,309 | definitive |
| 2020 | 134,759.514 | 134,760 | 223,341 | definitive |
| 2021 | 159,336.611 | 159,337 | 249,164 | estimate |
| 2022 | 170,314.011 | 170,314 | 266,366 | estimate |
| 2023 | 190,703.769 | — | 294,158 | estimate |
| 2024 | 214,597.272 | — | 309,937 | estimate |

The June 2025 INS note states that the 2018-base accounts migrate to SNA 2008 and raise 2018 GDP from 106,845.3 to 161,539 billion GNF (51.2%), principally through wider activity coverage and improved methods. The 2018–2020 accounts are definitive; 2021–2024 are rapid estimates. The October 2025 MPCI macroeconomic framework separately reports a revised 2018 base-year GDP of 161,766.5 billion GNF (+51.4%). Preserve this as a later official value/vintage rather than silently merging it with the June 2025 table.

The WDI current-LCU observations exactly follow the older 2018–2022 INS series to the published rounding precision. For 2023–2024 they also remain materially below the new INS rapid estimates. This is direct evidence that the compared WDI current-LCU series has not incorporated the 2018-base SNA 2008 level consistently.

The UNSD National Accounts country profile (January 2026 upload) independently identifies INS as the source for Guinea GDP nominal values in 2018–2024. Its 2024 profile reports GNF 311.077 trillion / US$36.465 billion and GDP per capita US$2,473. The WDI snapshot reports GNF 214.597 trillion / US$25.009 billion and US$1,694.95 per capita; October 2026 WEO reports US$38.348 billion and US$2,487.36 per capita. The WDI population observation (14,754,785) matches the UNSD profile population for 2024. Thus the 2024 GDP-per-capita gap is not explained by the population denominator in this comparison; the GDP numerator vintage is the principal identified issue. UNSD and WEO are close but not identical, and their different publication vintages must remain visible.

The WDI USD values are reproduced by current-LCU GDP divided by the DEC alternative conversion factor. For 2018–2020, the official and alternative factors are effectively identical in the capture. This confirms arithmetic, not a causal FX explanation: the old level is already present in local-currency GDP before dollar conversion.

### Central African Republic — revised local-currency accounts isolate the level break

The 2026-11-07 WDI snapshot reports current-LCU GDP of 1,301.485, 1,339.228 and 1,395.476 billion FCFA in 2019–2021. The definitive ICASEES 2019-base SNA 2008 accounts report 1,952.925, 2,056.035 and 2,149.622 billion FCFA respectively. WDI is therefore 33.36%, 34.86% and 35.08% below the definitive accounts in local currency. The ICASEES revised values match the October 2026 IMF WEO `CAF.NGDP.A` series exactly at published precision.

The WDI official exchange-rate and DEC alternative-factor observations are effectively identical for these three years. Therefore, the persistent WDI/IMF USD gap is not explained by choosing between those two captured conversion factors: it is already present in the local-currency GDP numerator. This is stronger evidence of a national-accounts source/vintage mismatch than the earlier USD-only comparison. It does not establish which WDI source vintage or compilation inputs generated the lower numerator. The workbook's separate historical 2019 value (1,431.991 billion FCFA) is not identical to WDI's 1,301.485 billion; do not claim WDI exactly reproduces the ICASEES historical series.

The population comparison remains a separate issue. ICASEES's definitive accounts publication reports population of 5,360,271, 5,464,907 and 6,091,097 for 2019–2021, while the WDI snapshot has 4,944,703, 5,026,628 and 5,112,100. GDP-per-capita differences therefore combine a numerator vintage break and a population denominator difference. The WEO per-capita values must not be treated as a simple validation of ICASEES population.

### Updated disposition

- **Guinea field 15:** the compared WDI current-LCU series is demonstrably the legacy INS/SCN 1993 level for 2018–2022 and remains materially below the 2018-base SNA 2008 INS series through 2024. This strongly supports a WDI national-accounts vintage mismatch as the main explanation for the nominal GDP gap. The exact WDI provider vintage/ingestion history is still not established.
- **Guinea field 16:** for 2024, WDI and UNSD population match exactly, while WDI GDP and per-capita GDP are materially lower. The numerator vintage explains the principal discrepancy in that year. Earlier-year population and status should still be checked before generalizing.
- **CAR field 15:** the revised ICASEES local-currency accounts and WEO match exactly for 2019–2021; WDI local-currency GDP remains 33–35% lower. The difference exists before FX conversion and is a national-accounts vintage/compilation issue, not an official-versus-DEC conversion-factor choice.
- **CAR field 16:** both numerator and population denominator differ between WDI and ICASEES; the per-capita gap cannot be attributed to GDP alone.
- Keep IMF WEO priority unchanged. These are source-vintage findings, not source approvals, and do not establish that WEO is universally correct for all years.

### Primary source references added

- INS Guinea, [Note d’analyse des comptes nationaux définitifs 2018–2020 et rapides 2021–2024](https://www.stat-guinee.org/images/Documents/Publications/INS/annuelles/CN/Note_danalyse_des_comptes_nationaux_definitifs_2018_2020_et_rapides_2021_2024.pdf), June 2025.
- INS Guinea, [La Guinée en chiffres 2023](https://www.stat-guinee.org/images/Documents/Publications/INS/annuelles/annuaire/La_Guinee_en_chiffre_2023.pdf), legacy national-accounts series.
- Guinea MPCI, [Cadrage macroéconomique 2024](https://mpci.gov.gn/index.php/cadrage-macroeconomique-2024-le-ministre-ismael-nabe-met-laccent-sur-la-transformation-structurelle-et-la-credibilite-internationale-de-la-guinee/), 9 October 2025.
- UNSD, [Guinea National Accounts country profile](https://unstats.un.org/unsd/snaama/CountryProfile?ccode=324) and [GDP source metadata](https://unstats.un.org/unsd/snaama/Metadata/?countrycode=324&groupid=101), January 2026 upload.
- ICASEES, [Comptes Nationaux définitifs 2019–2021](https://icasees.org/index.php/actualites/394-les-comptes-nationaux-2019-2021-de-la-republique-centrafricaine-officiellement-publies), 30 July 2026.


### Turkmenistan — 7 November 2026 WDI snapshot decomposition

The expanded WDI snapshot retrieved on 7 November 2026 provides a complete 2015–2025 arithmetic decomposition for Turkmenistan. Reported current-USD GDP is reproduced by dividing WDI current-LCU GDP by the DEC alternative conversion factor in all 11 years. The WDI official exchange-rate indicator is missing for every year in this capture. This verifies the arithmetic construction in the captured observations; it does not establish the factor's original source or imply that it is a parallel-market exchange rate.

| Year | WDI current LCU GDP (bn TMT) | DEC factor (TMT/USD) | WDI current USD GDP (bn) | IMF WEO current USD GDP (bn) | WDI relative to WEO |
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

The 2017–2018 DEC factor jump (3.98 to 5.48) coincides with the sharp WDI/WEO divergence. It is not explained by the WDI country metadata's stated 2019–2025 alternative-factor period alone. The IMF 2023 working paper documents that the official rate remained 3.5 TMT/USD from 2015 while parallel-market rates diverged sharply, but it treats those observations as directional indicators rather than official statistics. Do not equate the DEC factor with the parallel-market rate without direct source documentation.

TurkmenStat's January 2025 notice reports phased national-accounts methodology modernization. Its June 2026 notice describes World Bank technical assistance for national accounts under the 2025 SNA and ICP methodology. The IMF June 2025 and June 2026 mission statements identify exchange-rate unification and statistical quality as material issues; the June 2026 statement says the official GDP-growth narrative is difficult to reconcile with other available data and that IMF staff use their own GDP estimates. These statements strengthen the case for a source-vintage and methodology investigation but do not numerically reconcile WDI and WEO.

**Disposition:** preserve the WDI arithmetic, missing official FX observations, 2018 factor break, and WEO gap as separate evidence. No source-selection change, identity approval, semantic approval, or canonical application follows. See [Turkmenistan macroeconomic evidence acquisition](turkmenistan-macroeconomic-evidence-acquisition.md) for the five-publication capture plan.
