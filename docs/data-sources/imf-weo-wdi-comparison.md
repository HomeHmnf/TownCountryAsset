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

The tool writes `assessment.json`, `assessment.md`, `country_year_comparison.csv` and `candidate_matrix.csv` beneath `reports/sources/imf-wdi-comparison/<UTC timestamp>/`. The matched-pair CSV remains focused on numerical comparisons; the candidate matrix is the complete project-identity × field × year grid for the selected year range.

## Complete candidate matrix

`candidate_matrix.csv` contains one row for every unique project `game_id` in the identity registry × each of the five fields × each requested year, including identities with no observations in either provider. It records:
- project `game_id`, country label and source lookup code (ISO3 where supplied);
- identity record status, ISO assignment status and a separate mapping disposition;
- IMF and WDI observation-presence flags and canonical-unit values;
- coverage state: `both_sources_present`, `imf_only`, `wdi_only` or `neither_source_present`;
- IMF latest-actual hint and reporting-period metadata;
- differences only when both provider observations exist;
- `diagnostic_only_not_approved` semantic status.

An identity is marked `mapped_verified` only when the registry record is approved and its ISO assignment is verified. Existing proposed/unverified identities remain visible as `mapped_review_required`; the comparison does not promote or repair them. Missing source codes and ambiguous code assignments remain explicit. Therefore, a populated comparison row does not itself establish an approved country identity.

The matrix is a coverage and review instrument, not an import file. It does not classify WDI actual/estimate status, and the IMF `after_latest_actual` hint does not distinguish estimates from projections. PPPGDP remains unclassified because its WEO export has no latest-actual metadata. Field 20/21 reporting-period blanks remain unknown unless independently corroborated by the existing country investigations.

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

### Field 21 targeted three-way diagnostic

For field 21, the comparison additionally retrieves World Bank `SL.UEM.TOTL.NE.ZS` (unemployment, total, national estimate) over the same year range. It is attached to the IMF/WDI-modelled country-year rows as a separate diagnostic value and its own indicator metadata is retained. It is not treated as a replacement for either series, and absence of a national estimate remains null.

The IMF WEO `LUR` country-series metadata is also preserved per observation: unit, scale, reporting-period type, methodology, methodology notes, historical data source, labour-sector employment type, short source citation and country update date, alongside the already retained latest-actual year and reporting-year months. Blank provider fields remain unknown; the utility does not infer a percentage unit, population coverage, harmonization or actual/estimate status from labels.

For a targeted three-country inspection, review the field 21 rows for Bahrain, Moldova and the Philippines in `country_year_comparison.csv`, alongside the corresponding `wdi_national_estimate_metadata` in `assessment.json`. Interpret the three WDI/IMF series as distinct statistical products:
- IMF WEO `LUR`: country-desk series; country-specific source and methodology metadata must be reviewed.
- WDI `SL.UEM.TOTL.ZS`: ILO modelled estimate.
- WDI `SL.UEM.TOTL.NE.ZS`: national estimate, with potentially different country coverage, reference population and methodology.

This is still a live WDI API diagnostic, not a vintage-aligned comparison or proof of which series is correct. No source selection or policy change follows automatically.
- IMF `LATEST_ACTUAL_ANNUAL_DATA` is preserved. A simple calendar-year value is used only as a status hint; fiscal-year labels are not coerced, and values after the latest-actual year are not split into estimate versus projection.
- WDI status is not inferred by this utility.
- Fiscal-year reporting metadata is retained on the IMF side; a same-numbered year does not prove identical reporting periods.

A shared country-year or a small numerical difference does not establish semantic compatibility. In particular, fields 18, 20 and 21 require definition review before any policy proposal.

The targeted field 21 review is documented in [`field-21-unemployment-comparability-assessment.md`](field-21-unemployment-comparability-assessment.md), with detailed Bahrain evidence in [`bahrain-unemployment-series-assessment.md`](bahrain-unemployment-series-assessment.md). The official Bahrain Open Data Portal API dataset `03-unemployment-yearly` has been acquired and reviewed (50 records for 2016–2025). Its total rate matches IMF WEO exactly in 2017–2025. The 2016 API value of 4.3% matches the Ministry's December 2016 rate; the Ministry states the annual average was 4.0%. GCC-STAT independently reports a 3.9% annual citizen unemployment rate for Bahrain in 2016, matching WEO, and documents that Bahrain unemployment data are citizens-only Ministry register data. The best-supported classification is a reference-period mismatch (likely December/year-end API value versus annual citizen rate), although the API does not explicitly expose its reference period. The dataset also provides male/female rates and male/female unemployed counts, but no provider total-count rows. The 2022 verification gap is closed. Retain IMF WEO as priority and do not change source-selection policy.

## Bahrain field 21 primary-source reconciliation update (2026-11-02)

The Bahrain official annual dataset was acquired through `tools.sources.bahrain_unemployment` and reviewed from the immutable snapshot `raw_data/sources/bahrain_open_data/unemployment_yearly/20261102T141738Z/`. The provider published 50 records: 10 years of male and female unemployed counts, and 10 years of male, female and total unemployment rates. The official API total-rate series matches IMF WEO `LUR` for 2017–2025. In 2016, the API value 4.3% matches the Ministry's December rate, while the Ministry states the annual average was 4.0%; GCC-STAT reports the annual citizen rate as 3.9%, matching WEO, and states Bahrain unemployment data are citizen-only Ministry register data. Classify this as a likely reference-period mismatch, noting the API does not explicitly expose its reference period. The official dataset confirms 2022 at 5.4%, matching WEO. Detailed values and sex breakdowns are in the Bahrain assessment document. No source-policy, database or release action follows.

## Targeted GDP and GDP-per-capita investigation

The persistent field 15/16 outliers (Turkmenistan, Guinea and the Central African Republic) have been reviewed against country-specific national-accounts and exchange-rate evidence. The findings and source references are documented in [`field-15-16-gdp-comparability-assessment.md`](field-15-16-gdp-comparability-assessment.md). In summary: Turkmenistan has a documented dual-exchange-rate/alternative-conversion-factor issue; Guinea's 2018-base SNA 2008 rebasing raised the GDP level by 51.4%, and current UN/INS values are much closer to IMF WEO than to the compared WDI values; CAR's earlier national-accounts gap assessment has been superseded by ICASEES's July–August 2026 publication of definitive 2019–2021 accounts and 2019-base SNA 2008 rebasing; the remaining task is to align those new accounts with WEO/WDI vintages. Retain IMF WEO as priority; no source-policy, database, approval or release action follows.

## Targeted PPP GDP investigation

Field 18 outliers (Guinea, Central African Republic and Zimbabwe) have been reviewed against ICP and country-specific national-accounts/currency evidence. Findings are documented in [`field-18-ppp-gdp-comparability-assessment.md`](field-18-ppp-gdp-comparability-assessment.md). For Guinea and CAR, PPP GDP discrepancies are similar in scale to the nominal GDP discrepancies, consistent with underlying national-accounts source-vintage differences; a full decomposition of nominal GDP and PPP-factor effects remains outstanding. Zimbabwe's WDI 2017 PPP GDP API observation differs from an older WITS display based on the 2011 ICP vintage; the ICP 2021 cycle revised the 2017 benchmark, so this is not yet evidence of a WDI anomaly. An IMF methodological paper documents a special desk-exchange-rate conversion of Zimbabwe's 2017 ICP PPP factor before applying it to WEO nominal GDP submitted in USD. Retain IMF WEO as priority; no source-policy, database, approval or release action follows.

## Targeted inflation investigation

Field 20 outliers (Tonga, Samoa and Palau) have been reviewed against IMF Article IV period-average CPI tables and national statistical office CPI publications. Findings are documented in [`field-20-inflation-comparability-assessment.md`](field-20-inflation-comparability-assessment.md). The strongest explanation for much of the discrepancy is fiscal-year versus calendar-year alignment: Samoa uses July–June, Tonga's fiscal year begins 1 July, and Palau's fiscal year ends 30 September. Tonga also changed its CPI basket/methodology in September 2021. The comparison's WEO reporting-period metadata is blank for this series, so no year shifting or policy change is made; the Samoa 2025 residual and earlier Tonga/Palau years remain under review.

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
