# Guinea national accounts — vintage reconciliation

**Assessment date:** 2026-11-07  
**Provider:** Institut National de la Statistique (INS), République de Guinée  
**Scope:** WP1.5 fields 15 GDP, 16 GDP per capita and 18 GDP PPP  
**Disposition:** strong evidence that the compared WDI GDP series retains the legacy 1993 SNA national-accounts level; retain IMF WEO priority. No source approval, override, release promotion or canonical database write.

## 1. Evidence status

This is a read-only reconciliation using the 2026-11-07 WDI API snapshot, the October 2026 IMF WEO export, official INS publications, Guinea's Ministry of Planning publication and the January 2026 UN Statistics Division (UNSD) National Accounts profile and metadata.

The INS PDFs and yearbook are identified below as primary-source acquisition targets but have **not yet been captured into this repository or registered as Project DB acquisitions**. The numerical evidence below is transcribed from the official published tables and the UNSD profile; it must not be represented as an immutable local source snapshot until acquisition is completed.

## 2. National-accounts methodology and rebasing

INS's June 2025 *Note d'analyse des comptes nationaux définitifs 2018–2020 et rapides 2021–2024* explains that Guinea moved its national accounts to a 2018 base and the 2008 System of National Accounts (SNA 2008), with AFRISTAT technical assistance. The report states that the 2018 GDP level rose from GNF 106,845.3 billion under the previous SNA 1993 / 2006-base series to GNF 161,539 billion under the new SNA 2008 / 2018-base series, a 51.2% revaluation. The report attributes the increase primarily to wider coverage of economic activity and improved methods, including additional agricultural, household-living-conditions, employment/informal-sector and specific-sector survey sources.

The June 2025 INS note classifies 2018–2020 accounts as definitive and 2021–2024 as rapid estimates. Its current-price GDP table is:

| Year | INS 2018-base SNA 2008 GDP (billion GNF) | Status |
|---:|---:|---|
| 2018 | 161,539 | definitive |
| 2019 | 188,309 | definitive |
| 2020 | 223,341 | definitive |
| 2021 | 249,164 | rapid estimate |
| 2022 | 266,366 | rapid estimate |
| 2023 | 294,158 | rapid estimate |
| 2024 | 309,937 | rapid estimate |

The October 2025 MPCI final 2024 macroeconomic framework separately reports a 2018 base-year GDP of GNF 161,766.5 billion, compared with GNF 106,845.3 billion under the previous base, a 51.4% increase. This is a later official published value and differs slightly from the June 2025 INS note's GNF 161,539 billion. Preserve both as distinct publication vintages; do not silently replace one with the other.

The earlier INS *La Guinée en chiffres 2023* yearbook publishes the legacy 1993 SNA series (billion GNF): 2018 106,845; 2019 123,458; 2020 134,760; 2021 159,337; 2022 170,314.

## 3. Direct comparison with the frozen WDI local-currency series

The 2026-11-07 WDI snapshot's `NY.GDP.MKTP.CN` values reproduce the old INS/1993 SNA series to the published rounding precision for 2018–2022:

| Year | WDI current LCU (billion GNF) | Legacy INS 1993 SNA (billion GNF) | New INS 2018-base SNA 2008 (billion GNF) | WDI vs new series |
|---:|---:|---:|---:|---:|
| 2018 | 106,845.292 | 106,845 | 161,539 | -33.86% |
| 2019 | 123,457.571 | 123,458 | 188,309 | -34.44% |
| 2020 | 134,759.514 | 134,760 | 223,341 | -39.66% |
| 2021 | 159,336.611 | 159,337 | 249,164 | -36.05% |
| 2022 | 170,314.011 | 170,314 | 266,366 | -36.06% |
| 2023 | 190,703.769 | — | 294,158 | -35.17% |
| 2024 | 214,597.272 | — | 309,937 | -30.76% |

This is direct evidence that the compared WDI local-currency GDP series still carries the legacy national-accounts level for 2018–2022. For 2023–2024, WDI remains materially below the new INS rapid estimates. The WDI 2025 value has no corresponding value in the cited June 2025 INS note and is not reconciled here.

The 2018–2022 near-exact match to the legacy series is much more specific than a generic 51% rebasing observation: it identifies the national-accounts vintage represented by the WDI current-LCU series. It does not establish when WDI acquired or last revised the series, nor the exact provider pipeline that supplied the observations.

## 4. USD conversion and IMF/UN corroboration

The WDI current-USD GDP values are arithmetically reproduced by dividing the captured local-currency GDP by the DEC alternative conversion factor. In 2018–2020, the captured official exchange rate and DEC alternative factor are effectively identical. This means the large difference from the new INS level is already present in local-currency GDP; it is not created by the USD conversion factor.

For 2020–2024, the comparison is:

| Year | WDI GDP (US$ bn) | IMF WEO GDP (US$ bn) | UNSD GDP (US$ bn) | UNSD source/vintage |
|---:|---:|---:|---:|---|
| 2020 | 14.089 | 23.459 | 23.459 | INS nominal values |
| 2021 | 17.069 | 25.137 | 25.558 | INS nominal values |
| 2022 | 19.910 | 30.060 | 30.609 | INS nominal values |
| 2023 | 22.408 | 35.333 | 34.671 | INS nominal values |
| 2024 | 25.009 | 38.348 | 36.465 | INS nominal values |

The UNSD January 2026 country profile's GDP metadata explicitly identifies INS as the source for nominal GDP values for 2018–2024. The profile's 2024 GDP is GNF 311.077 trillion / US$36.465 billion, compared with WDI GNF 214.597 trillion / US$25.009 billion and October 2026 WEO US$38.348 billion. WEO is closer to the current UNSD/INS level than WDI, but is not identical to it.

The 2024 population is 14,754,785 in both the WDI snapshot and UNSD profile. The UNSD profile reports GDP per capita US$2,473, while WDI reports US$1,694.95 and WEO reports US$2,487.36. For 2024, the GDP-per-capita difference is therefore not explained by a different population denominator in these sources; the GDP numerator vintage is the principal identified issue. Do not generalize this result to every earlier year without checking the population values and reference dates.

## 5. PPP implications

WDI PPP GDP is reproduced arithmetically by dividing WDI current-LCU GDP by the captured GDP PPP conversion factor. This proves internal arithmetic consistency only. The nominal local-currency GDP vintage is already materially lower than the new INS series, so the PPP GDP gap inherits a substantial national-accounts numerator difference. The remaining PPP-specific questions are the ICP benchmark, PPP-factor vintage, extrapolation/linking method and the IMF WEO PPP construction. Field 18 remains not yet demonstrated comparable.

## 6. GDP-per-capita implications

For 2024, WDI and UNSD use the same population value, while their GDP and GDP-per-capita values differ materially. This points to the numerator vintage as the main explanation for that year. The 2015–2025 field 16 comparison still requires year-specific population and reference-date reconciliation; do not automatically attribute every per-capita discrepancy to GDP alone.

## 7. Source files to acquire and retain

The following official publications are the primary acquisition targets for a reproducible local evidence bundle:

| Publication | Date | Role | Official URL |
|---|---|---|---|
| *La Guinée en chiffres 2023* | 2023 | Legacy 1993 SNA series, 2018–2022 | https://www.stat-guinee.org/images/Documents/Publications/INS/annuelles/annuaire/La_Guinee_en_chiffre_2023.pdf |
| *Note d'analyse des comptes nationaux définitifs 2018–2020 et rapides 2021–2024* | June 2025 | New 2018-base SNA 2008 series, definitive/estimate status and methodology | https://www.stat-guinee.org/images/Documents/Publications/INS/annuelles/CN/Note_danalyse_des_comptes_nationaux_definitifs_2018_2020_et_rapides_2021_2024.pdf |
| MPCI, *Cadrage macroéconomique 2024* | 9 October 2025 | Later official 2018 base-year value and revaluation statement | https://mpci.gov.gn/index.php/cadrage-macroeconomique-2024-le-ministre-ismael-nabe-met-laccent-sur-la-transformation-structurelle-et-la-credibilite-internationale-de-la-guinee/ |
| UNSD Guinea National Accounts profile | January 2026 upload | Independent published profile and population/nominal GDP values | https://unstats.un.org/unsd/snaama/CountryProfile?ccode=324 |
| UNSD Guinea GDP metadata | January 2026 upload | Confirms INS nominal-value source for 2018–2024 | https://unstats.un.org/unsd/snaama/Metadata/?countrycode=324&groupid=101 |

No license conclusion is made here. Check the publication's own licensing/terms before redistributing source bytes. Do not infer a CC BY license from availability.

## 8. Disposition and remaining gates

1. Classify the compared WDI Guinea current-LCU GDP series as **legacy national-accounts vintage for 2018–2022**, with strong evidence of continued under-level relative to the 2018-base SNA 2008 series through 2024.
2. Treat the June 2025 INS series' 2021–2024 values as rapid estimates, not definitive accounts.
3. Preserve the separate October 2025 MPCI 2018-base figure and January 2026 UNSD profile as later/alternate published vintages.
4. Do not treat the 2024 WEO/UNSD closeness as proof of independent compilation or use it to approve all WEO observations.
5. Keep IMF WEO priority unchanged for fields 15, 16 and 18. Do not create a fallback or manual override.
6. Capture the official INS source files, metadata and hashes into an immutable Project acquisition before using this evidence as a reproducible project artifact.
7. No identity promotion, semantic approval, source-selection change, release promotion or Game DB write is authorized by this diagnostic.
