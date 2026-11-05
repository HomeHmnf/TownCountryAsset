# ICASEES national accounts — dataset and workbook structure

## Dataset metadata

- Dataset title: Comptes nationaux 2019–2021 (suivant le SCN 2008).
- Coverage: Central African Republic, annual, 2019–2021 for the revised accounts.
- Producer: ICASEES / DCNPE.
- Subject matter: GDP, value added by branch, goods and services, consumption, gross fixed capital formation and external trade.
- The workbook also carries an older historical series, including 2005–2019 and a 1960–2019 presentation.

## Workbook inventory

| Sheet | Dimensions | Role |
|---|---:|---|
| Metadonnées | 11 × 2 | Dataset metadata |
| Dataset | 6 × 3 | Dataset description and coverage |
| Indicateur | 36 × 4 | Indicator definitions |
| Donnee | 36 × 7 | Revised 2019–2021 observations |
| Indicateur_2005-2019 | 36 × 4 | Historical indicator definitions |
| Donnee_2005-2019 | 36 × 72 | Historical observations |
| Donnee_2013-2019 | 36 × 64 | Historical observations for 2013–2019 |
| Donnée nouvelle | 36 × 7 | Repeated revised 2019–2021 presentation |
| Donnée_SCN2008 | 40 × 71 | Historical and revised blocks presented side by side |

## Revised 2019–2021 observations

The Donnee sheet has columns Indicateur, Indicateur Name, Units, Scale, 2019, 2020 and 2021. Its GDP aggregates are:

| Indicator | Label | 2019 | 2020 | 2021 |
|---|---|---:|---:|---:|
| IND33 | TOTAL VAB | 1876.710 | 1968.854 | 2063.554 |
| IND34 | IMPÔTS ET TAXES SUR LES PRODUITS | 76.215 | 87.181 | 86.068 |
| IND35 | PRODUIT INTERIEUR BRUT | 1952.925 | 2056.035 | 2149.622 |

The sector VAB aggregates are:

| Indicator | Sector | 2019 | 2020 | 2021 |
|---|---|---:|---:|---:|
| IND1 | Primary | 422.807 | 462.537 | 475.988 |
| IND7 | Secondary | 431.047 | 431.564 | 479.105 |
| IND20 | Tertiary | 1022.856 | 1074.753 | 1108.461 |

The sector values sum to total VAB; total VAB plus product taxes equals GDP in each of the three years. Donnée nouvelle repeats the revised GDP values.

## Historical and revised blocks are distinct

The Donnee_2013-2019 historical GDP series (IND35) is:

| Year | Historical GDP value |
|---:|---:|
| 2013 | 887.5841009239971 |
| 2014 | 1012.1709741089346 |
| 2015 | 1102.8568528781984 |
| 2016 | 1182.4961782573846 |
| 2017 | 1276.813017407797 |
| 2018 | 1322.8826100491247 |
| 2019 | 1431.9912216062085 |

The combined Donnée_SCN2008 sheet places the historical block in columns A:BE and the revised block from BN onwards. The historical GDP is row 37; revised VAB, taxes and GDP are rows 38, 39 and 40. The revised 2019 value is not the historical 2019 value. Do not overwrite, align by row number or concatenate these blocks without a defensible methodological bridge.

## Formula and cached-value handling

The revised right-side labels in Donnée_SCN2008 are formulas referring to an external workbook path from the original author's environment. Formula mode exposes external references such as =[1]PIB_courant!$B$3; cached/data-only mode contains the labels and numeric cached results. The assessment reads labels from the cached workbook and evaluates supported numeric arithmetic from formula mode. It must not attempt to access the author's external workbook.

Key revised formulas include sector VAB aggregation, VAB + product taxes = GDP. The external tax formula is cached; the final GDP formula is an arithmetic sum. Formula parsing is deliberately restricted and should fail clearly on unsupported formula shapes.

## Unit metadata warning

Observation-level rows label units as millions de F CFA, while the dataset description and the definitive publication's reported GDP values show the revised GDP numeric values are in billion FCFA. This conflict is resolved for GDP only in [the GDP scale and WEO reconciliation](gdp-scale-and-weo-reconciliation.md). Do not infer the scale of every other indicator from the GDP finding.

## Parser and assessment

The read-only assessment tool is tools/assess_icasees_national_accounts.py. It verifies the immutable manifest, inventories sheets and formulas, extracts historical and revised GDP separately, checks arithmetic and duplicate presentations, and extracts relevant PDF text when pypdf is available. It does not import observations into SQLite or change source-selection policy.
