# ICASEES national accounts — GDP scale and IMF WEO reconciliation

## Definitive publication scale

The definitive 2019–2021 accounts publication reports GDP in its detailed tables as:

| Year | Definitive accounts (million FCFA) | Equivalent (billion FCFA) |
|---:|---:|---:|
| 2019 | 1,952,925 | 1,952.925 |
| 2020 | 2,056,035 | 2,056.035 |
| 2021 | 2,149,622 | 2,149.622 |

The workbook's revised GDP values are 1,952.925, 2,056.035 and 2,149.622 in Donnee, Donnée nouvelle and the revised block of Donnée_SCN2008. The three workbook presentations agree year by year. These numeric values correspond to **billion FCFA**, not million FCFA. The observation-level label millions de F CFA is inconsistent with the numeric scale and detailed PDF tables; the dataset description's billion-FCFA scale is consistent.

Do not multiply the workbook GDP values when using billion FCFA. To express them in million FCFA, multiply by 1,000. This conclusion is established for GDP only; it must not automatically be generalized to every workbook indicator.

## IMF WEO cross-check

The October 2026 WEO CSV contains Central African Republic annual national-currency series CAF.NGDP.A:

- Indicator: Gross domestic product (GDP), Current prices, Domestic currency.
- Unit: Domestic currency.
- Scale: Billions.
- Reporting year: January/December.
- Latest actual annual data: 2022.

| Year | ICASEES revised GDP (billion FCFA) | IMF CAF.NGDP.A (billion domestic currency) | Difference |
|---:|---:|---:|---:|
| 2019 | 1,952.925 | 1,952.925 | 0 |
| 2020 | 2,056.035 | 2,056.035 | 0 |
| 2021 | 2,149.622 | 2,149.622 | 0 |

The three annual values match exactly at the precision published in the WEO CSV. The WEO metadata identifies these years as preceding the series' latest-actual-year boundary (2022), rather than post-actual projections. This is a value and scale cross-check; it does not prove the two publications used independent underlying compilation inputs.

The companion WEO series CAF.NGDPD.A is current-price GDP in US dollars, billions: 3.333 (2019), 3.577 (2020) and 3.879 (2021). It is not used for the exact reconciliation because it introduces exchange-rate conversion; the domestic-currency series is the direct comparison.

## 2019 historical/revised break

The workbook's historical 2019 GDP is 1,431.9912216 billion FCFA, while revised 2019 GDP is 1,952.925 billion FCFA, a 36.378% increase. These are distinct series and must not be spliced. The WEO match corroborates the revised level; it does not explain or eliminate the methodological break.

## Rebase methodology context

The February 2023 peer-review memo describes the move from a 2005 base/SNA 1993 to a 2019 base/SNA 2008. It records new sources including ENA 2021 and EHCVM 2021, expanded classifications and ERETES use, and SNA 2008 treatments such as FISIM, central-bank non-market output, adjusted non-life insurance claims, research and development, and military equipment as gross fixed capital formation.

The memo also records measurement limitations and recommendations for completing 2019 base accounts, current accounts for 2020/2021 and retropolation under SNA 2008. It is preliminary/peer-review evidence; its recommendations do not prove that every noted limitation remained in the final 2026 accounts. It does not provide a quantitative decomposition of the 36.378% GDP revision.

## Interpretation and limits

- The exact WEO match establishes consistency at published precision, not independent methodological validation.
- It does not establish continuity between the old historical series and revised 2019–2021 series.
- No complete decomposition of the revision by methodology, coverage, classification or source has been established.
- Do not generalize GDP unit resolution to all indicators.
- Do not create a source override, fallback or policy change from this reconciliation alone.

## Disposition

This is a read-only analytical finding. It does not create normalized observations, approve or promote a source release, change source-selection policy, or write to canonical SQLite. Any future ICASEES import requires the shared acquisition, validation, approval and transactional application lifecycle.
