# Inflation comparability investigation

**Assessment date:** 2026-11-02  
**WP1.5 field:** 20 — inflation  
**Compared series:** IMF WEO `PCPIPCH` versus WDI `FP.CPI.TOTL.ZG`  
**Investigation window:** 2015–2025  
**Disposition:** retain the current IMF WEO priority assignment pending explicit reporting-period normalization. Much of the Tonga, Samoa and Palau discrepancy is consistent with IMF fiscal-year observations being compared to WDI calendar-year observations. Do not silently shift years or average values across periods.

## Executive summary

The comparison's large relative differences are misleading for low and near-zero inflation rates. Absolute percentage-point differences and reporting periods are more informative.

Country-specific IMF sources document fiscal-year reporting:
- **Samoa:** fiscal years run July–June. IMF staff's period-average CPI observations for FY2020/21 through FY2023/24 closely match the WEO values stored under the fiscal-year ending year. WDI's annual values track calendar-year averages and closely match Samoa Bureau of Statistics' annual average CPI series for 2021–2023.
- **Tonga:** the fiscal year begins 1 July. IMF staff's period-average CPI values for FY2022–FY2025 closely match WEO observations for 2022–2025. WDI annual values are calendar-year observations. Tonga also changed its CPI basket and methodology in September 2021.
- **Palau:** the fiscal year ends 30 September. IMF staff's period-average CPI values for FY2022/23, FY2023/24 and FY2024/25 closely match WEO observations stored as 2023, 2024 and 2025. WDI values are calendar-year observations.

The comparison utility has blank IMF reporting-period metadata for `PCPIPCH` in all three countries. The country-specific IMF staff reports nevertheless establish that the relevant series are fiscal-year-based. This is a material metadata gap; a year label alone must not be interpreted as calendar-year coverage.

## Country findings

### Samoa — fiscal year July–June

The IMF's 2024 Article IV report explicitly states that Samoa's fiscal years are July–June. It publishes period-average CPI inflation for:
- FY2020/21: -3.0%;
- FY2021/22: 8.7%;
- FY2022/23: 12.0%;
- FY2023/24: 3.6%;
- FY2024/25: 3.1%.

These values closely match the October 2026 WEO series under ending-year labels:
- 2021: -3.010%;
- 2022: 8.747%;
- 2023: 11.981%;
- 2024: 3.586%.

The 2025 WEO value is 1.840%, however, not the 3.1% in the IMF report's FY2024/25 table. This is a residual vintage/revision or compilation discrepancy that is not explained by the reporting-period alignment alone.

The WDI calendar-year values for 2021–2025 are 3.133%, 10.962%, 7.922%, 2.172% and 2.212%. Samoa Bureau of Statistics' published average-annual inflation table independently confirms 2021 at 3.1%, 2022 at 11.0%, and 2023 at 7.9%, matching WDI to rounding. The national statistical office's CPI page provides monthly CPI tables, and its annual inflation-rate summary documents average annual inflation as a separate measure.

**Assessment:** the 2021–2024 IMF/WDI differences are strongly explained by fiscal-year versus calendar-year reference periods. The WEO 2025 value does not match the cited IMF FY2024/25 table and remains a source-vintage question. Do not treat the full 2015–2025 gap as a statistical disagreement about the same calendar-year inflation measure.

### Tonga — fiscal year begins 1 July

The IMF's 2025 Article IV report states that its fiscal year begins July 1. Its period-average CPI inflation figures are:
- FY2022: 6.5%;
- FY2023: 12.6%;
- FY2024: 8.0%;
- FY2025: 2.9%.

These closely match the October 2026 WEO observations for 2022–2025:
- 2022: 6.550%;
- 2023: 12.554%;
- 2024: 8.001%;
- 2025: 3.100%.

The WDI calendar-year CPI series reports 10.971% in 2022, 6.351% in 2023, 3.182% in 2024 and 5.593% in 2025. These are not directly comparable to the fiscal-year values. A fiscal year beginning July 1 spans two calendar years; calendar-year averages include a different set of months, especially around a rapid change in inflation.

There is a further structural break/caveat: the Tonga Statistics Department says the CPI basket and methodology changed in September 2021. The 2025 rebasing used 2021 HIES expenditure weights, expanded the basket from 137 to 161 items, and revised recent CPI results following technical assistance in October 2025. These changes can affect the historical series and the latest vintage.

**Assessment:** the 2022–2025 WEO values are directly corroborated by IMF staff fiscal-year period-average CPI figures. The large WEO/WDI differences are substantially a reporting-period mismatch, compounded by CPI basket/methodology changes and revisions. The 2015–2021 history still requires an exact vintage and fiscal-year alignment review; do not shift those years mechanically without the full source metadata.

### Palau — fiscal year ends 30 September

The IMF's 2025 Article IV report explicitly states that Palau's fiscal year ends September 30. It publishes period-average CPI inflation for:
- FY2022/23: 12.4%;
- FY2023/24: 3.6%;
- FY2024/25: 0.2%.

These values closely match the October 2026 WEO observations stored under the fiscal-year ending years:
- 2023: 12.412%;
- 2024: 3.663%;
- 2025: 0.226%.

The WDI calendar-year values for 2023–2025 are 12.820%, 2.232% and -0.418%, respectively. They differ from the IMF fiscal-year values, particularly in 2024 and 2025. The 2025 IMF country report is strong corroboration that WEO's year labels correspond to the fiscal-year ending year for these observations.

For earlier years, WEO/WDI differences are smaller in some years and larger in others. The reviewed IMF report gives direct period-average corroboration only for FY2022/23–FY2024/25; the earlier Palau observations need the corresponding historical fiscal-year source table before a complete reconciliation can be claimed.

**Assessment:** the 2023–2025 differences are strongly explained by fiscal-year versus calendar-year reference periods. Earlier observations remain less fully corroborated.

## Comparison caveats

1. **Annual average versus end-of-period:** IMF `PCPIPCH` is period-average CPI inflation. It must not be compared to end-of-period inflation. Tonga's IMF staff report publishes both, and they differ materially during the 2021–2023 inflation surge.
2. **Fiscal year versus calendar year:** Samoa, Tonga and Palau use fiscal-year periods in the cited IMF reports. WDI's annual CPI series is a calendar-year observation. A same-numbered year does not establish the same twelve-month period.
3. **CPI basket and revisions:** Tonga changed CPI basket/methodology in September 2021 and revised recent CPI results in 2025. Samoa's official monthly tables and annual average summary may also be revised; preserve the retrieval vintage.
4. **Low denominators:** relative percentage differences become unstable when inflation is close to zero or negative. Use percentage-point differences and the actual source values, not relative percent differences alone.
5. **Source vintage:** WEO uses country-desk inputs and staff estimates; WDI's CPI indicator is sourced from IMF International Financial Statistics and may have a different reporting vintage. The IMF says WEO and IFS differ because WEO reflects information collected for the WEO exercise while IFS reflects ongoing member-country reporting. Historical values can be revised.
6. **Metadata gap:** the October 2026 WEO CSV's reporting-period metadata is blank for `PCPIPCH` in these countries. Country-specific IMF Article IV reports provide evidence of fiscal-year coverage, but this has not yet been incorporated into the comparison CSV.

## Source-selection disposition

1. Retain `imf_weo` as the existing priority source for field 20.
2. Do not promote WDI `FP.CPI.TOTL.ZG` to priority/fallback based on the unadjusted comparison.
3. Do not create country-specific manual overrides.
4. Do not shift year labels or change observation periods in the current canonical dataset without an explicit, documented normalization policy.
5. For a future policy proposal, acquire immutable WDI/IFS snapshots and the exact IMF country-year fiscal-year tables; document reference-period start/end months and whether each measure is annual average or end-of-period.
6. Resolve the Samoa 2025 residual and review earlier Tonga/Palau years before describing the full 2015–2025 period as reconciled.

This is a read-only evidence assessment. It changes no source registry, source-selection policy, approval, release ledger or canonical SQLite data.

## Primary references

- IMF, [Samoa: 2024 Article IV Consultation, Country Report 25/032](https://www.elibrary.imf.org/view/journals/002/2025/032/article-A001-en.xml), fiscal years July–June and period-average CPI table.
- Samoa Bureau of Statistics, [Consumer Price Index publications](https://www.sbs.gov.ws/cpi/), monthly CPI tables and annual average inflation series.
- Samoa Bureau of Statistics, [May 2024 CPI report](https://www.sbs.gov.ws/documents/economics/CPI/2024/05-CPI_May-Eng-Sam.pdf), Table 8 average annual inflation, including 2021–2023.
- IMF, [Tonga: 2025 Article IV Consultation, Country Report 25/293](https://www.elibrary.imf.org/view/journals/002/2025/293/article-A001-en.xml), fiscal year beginning July 1, period-average and end-of-period CPI, and September 2021 CPI methodology change.
- Tonga Statistics Department, [Consumer Price Index](https://tongastats.gov.to/statistics/economics/consumer-price-index/), 2021 rebasing and September 2025 CPI revisions.
- World Bank, [WDI inflation, consumer prices for Tonga](https://fred.stlouisfed.org/series/FPCPITOTLZGTON), calendar-year series and IFS source note.
- IMF, [Republic of Palau: 2025 Article IV Consultation, Country Report 26/022](https://www.elibrary.imf.org/view/journals/002/2026/022/article-A001-en.xml), fiscal year ending September 30 and period-average CPI.
- Palau Ministry of Finance, [Consumer Price Index](https://www.palaugov.pw/executive-branch/ministries/finance/budgetandplanning/consumer-price-index-cpi/), quarterly national CPI publications.
- World Bank, [WDI inflation, consumer prices for Palau](https://fred.stlouisfed.org/series/FPCPITOTLZGPLW), calendar-year series and IFS source note.
- IMF, [WEO Frequently Asked Questions](https://www.imf.org/en/publications/weo/frequently-asked-questions), WEO/IFS data differences, country-desk compilation and historical revisions.
