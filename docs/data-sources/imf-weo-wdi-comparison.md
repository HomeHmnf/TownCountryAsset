# IMF WEO and World Bank WDI country-year comparison

**Status:** read-only comparative assessment utility; no source-policy decision  
**Scope:** WP1.5 fields 15, 16, 18, 20 and 21  
**IMF input:** fixed October 2026 WEO CSV snapshot recorded in `docs/data-sources/imf-weo-october-2026-manual-acquisition.md`  
**WDI input:** live World Bank Indicators API v2 responses; not an immutable release

## Purpose and execution

The comparison aligns the existing IMF WEO series with candidate WDI indicators:

| Field | IMF WEO | WDI | Canonical comparison unit |
|---:|---|---|---|
| 15 GDP | `NGDPD` | `NY.GDP.MKTP.CD` | current US dollars |
| 16 GDP per capita | `NGDPDPC` | `NY.GDP.PCAP.CD` | current US dollars per person |
| 18 GDP PPP | `PPPGDP` | `NY.GDP.MKTP.PP.CD` | current international dollars |
| 20 Inflation | `PCPIPCH` | `FP.CPI.TOTL.ZG` | annual percent |
| 21 Unemployment | `LUR` | `SL.UEM.TOTL.ZS` | percent of labour force (IMF unit still requires confirmation) |

Run from the repository root:

```fish
uv run python -m tools.compare_imf_weo_wdi
```

The default comparison period is 2015–2025. It can be changed explicitly:

```fish
uv run python -m tools.compare_imf_weo_wdi --start-year 2015 --end-year 2025
```

The tool writes `assessment.json`, `assessment.md` and `country_year_comparison.csv` beneath `reports/sources/imf-wdi-comparison/<UTC timestamp>/`.

## Matching and normalization

- IMF source identifiers and WDI ISO3 codes are independently resolved through the existing country identity registry to `game_id`. No new identity assignment or ISO approval is made.
- WDI aggregate regions are excluded using the World Bank country catalogue's region classification.
- IMF GDP and PPP GDP are published in billions in this WEO export; the comparison multiplies those values by 1,000,000,000. GDP per capita and percentage values are not rescaled.
- Only country-year pairs present and non-null in both sources are numerically compared.
- The report separately counts IMF-only and WDI-only country-years and lists source codes that cannot be resolved through the existing registry.
- The CSV distinguishes `signed_difference` (IMF minus WDI), `absolute_difference`, signed `relative_difference_percent`, and `absolute_relative_difference_percent`. A zero WDI denominator produces a null relative difference rather than an infinite value.
- Summary percentiles and threshold counts use absolute relative differences. The 5% and 20% markers are descriptive, not acceptance thresholds.
- Each row classifies IMF reporting metadata as `calendar_year` only for the exact `January/December` value, `non_calendar_fiscal_year` when another reporting period is supplied, or `unknown` when blank.
- The report includes a calendar-year-only sensitivity summary using only January/December IMF rows. Fiscal-year and unknown-period rows are excluded; year labels are never shifted or interpreted as fiscal-year end dates.

## Interpretation constraints

This is not a like-for-like release-vintage comparison. The IMF input is a fixed October 2026 WEO export; WDI is retrieved from a rolling API and can change between runs. The WDI indicator metadata's API `lastupdated` value is retained where supplied, but that does not create an immutable snapshot.

- **GDP and GDP per capita:** both are current-price US-dollar measures, but country reporting practices, revisions and release vintages can differ.
- **GDP PPP:** the IMF WEO series refers to ICP benchmarks 2017–2021 and has no `LATEST_ACTUAL_ANNUAL_DATA` values in this export. Its actual/estimate/projected status is therefore unclassified. Confirm the PPP benchmark and time-series construction against WDI's indicator note before interpreting discrepancies.
- **Inflation:** IMF `PCPIPCH` is CPI period-average percent change. Verify that the WDI annual CPI series uses a sufficiently compatible annual-average convention.
- **Unemployment:** WDI `SL.UEM.TOTL.ZS` is a modelled ILO estimate. The IMF `LUR` export has a blank `UNIT` field and must not be assumed to have a confirmed percent unit or equivalent methodology. Numerical comparison is diagnostic only.
- IMF `LATEST_ACTUAL_ANNUAL_DATA` is preserved. A simple calendar-year value is used only as a status hint; fiscal-year labels are not coerced, and values after the latest-actual year are not split into estimate versus projection.
- WDI status is not inferred by this utility.
- Fiscal-year reporting metadata is retained on the IMF side; a same-numbered year does not prove identical reporting periods.

A shared country-year or a small numerical difference does not establish semantic compatibility. In particular, fields 18, 20 and 21 require definition review before any policy proposal.

## Side-effect boundary

The utility is read-only. It does not:

- acquire or write immutable source snapshots;
- alter `config/data_sources.json` or `config/source_selection.json`;
- create an approval record or release-validation record;
- change `latest_validated` or `latest_applied`;
- write to canonical SQLite or import observations.

Do not use this exploratory comparison report as an application artifact or as evidence of an approved fallback. Any future source-policy change remains a separate review and approval decision.


## Targeted country discrepancy investigation

After generating a comparison, run a read-only investigation against its CSV:

```fish
uv run python -m tools.investigate_imf_weo_wdi_discrepancies \
  --input reports/sources/imf-wdi-comparison/<timestamp>/country_year_comparison.csv
```

The utility currently prioritizes a small, explicit shortlist: fields 15/16 (Turkmenistan, Guinea, Central African Republic), field 18 (Guinea, Central African Republic, Zimbabwe), field 20 (Tonga, Samoa, Palau), and field 21 (Bahrain, Moldova, Philippines). It emits JSON, Markdown and country-year CSV outputs with source values, signed/absolute differences, direction consistency, IMF status hints and reporting-period metadata.

This is a prioritization and descriptive audit only. It does not fetch original provider records, revision histories, methodological notes beyond those already captured in the comparison, or independent corroboration. It must not infer which provider is correct or explain the cause of a discrepancy. Large relative differences with near-zero WDI denominators require particular caution; inspect absolute values and percentage-point differences for fields 20/21. No database, source registry, policy, approval or release action is performed.
