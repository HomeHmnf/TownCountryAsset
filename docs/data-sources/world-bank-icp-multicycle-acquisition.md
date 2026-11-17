# World Bank ICP multi-cycle acquisition and inspection

## Scope

This workflow treats the official ICP benchmark cycles as separate releases and does not collapse revised benchmarks into original vintages.

| Cycle/release | Coverage to acquire |
|---|---|
| ICP 2005 | Original 2005 results and associated published tables |
| ICP 2011 | Original 2011 results; revised 2011 results where included in the 2017 cycle |
| ICP 2017 | Original 2017 results and revised 2011 results |
| ICP 2021 | Revised 2017 and 2021 benchmarks, annual PPP series 2017–2021, and 2022–2023 GDP PPP extrapolations |

The World Bank's current ICP data page identifies the 2021-cycle coverage and confirms that original 2005, 2011 and 2017 results remain available. The 2017 benchmark was revised in the 2021 cycle; retain both vintages separately.

Official entry points:

- ICP data page: https://www.worldbank.org/en/programs/icp/data
- ICP 2021 DataBank: https://databank.worldbank.org/source/icp-2021
- ICP 2017 DataBank: https://databank.worldbank.org/source/icp-2017
- ICP 2005 DataBank: https://databank.worldbank.org/source/international-comparison-program-(icp)-2005
- ICP 2011 original workbook: https://pubdocs.worldbank.org/en/108821487172249299/2011-International-Comparison-Program-results.xlsx
- ICP 2021 Data Catalog ID: 0066092
- ICP 2017 Data Catalog ID: 0038406

## Automated DataBank saved-report export

The DataBank browser workflow has been live-validated end to end for the saved ICP-Annual-PPPs report. The owner-run acquisition on 2026-11-09 downloaded a 107,272-byte ZIP, validated its CRC, and extracted two CSV members (one observation export and one series-metadata export).

- Report: https://databank.worldbank.org/id/1da9d9a2?Report_Name=ICP-Annual-PPPs
- Tool: tools.acquire_world_bank_icp_databank
- Command:

```fish
uv run python -m tools.acquire_world_bank_icp_databank
```

The tool creates a cookie-backed session, reads the report's cube ID and selected dimension counts, retrieves the selected Country, Classification, Series and Time members, and registers the same hdnSelectVars payload used by the DataBank page. It requests the full-range CSV export using the case-sensitive down-radio=csv parameter, follows the returned FileDownloadHandler descriptor in the same session, validates the ZIP CRC, and extracts CSV members while preserving the original ZIP.

The timestamped manifest records the report URL and response fingerprint, cube ID, selected dimension members, export settings, DataBank descriptor, endpoint URLs, archive and extracted-member byte counts and SHA-256 fingerprints. The initial live export manifest (`databank_20261109T180637192513Z`) contains a source_id typo (`world_bank_wdi`); the acquisition tool now writes `world_bank_icp` and the explicit release key `icp_2021_saved_report` for subsequent captures. The original manifest is retained unchanged as acquisition evidence. Raw archives and extracted CSV members are retained under raw_data/sources/world_bank_icp/databank_exports/; manifests are under data_manifests/sources/world_bank_icp/databank_exports/; acquisition reports are under reports/sources/world-bank-icp/.

The automated saved report is a proven export path, **not yet a complete multi-cycle acquisition**. This report contains one classification, six series and the report's selected 2017–2023 time range. It does not replace discovery and export of every detailed table, original benchmark cycle, revised benchmark, metadata/status table or annual series required by the project. Do not treat its coverage as the entire ICP catalogue.

Run through proxychains when the local network requires the configured SOCKS proxy. The tool itself uses the standard-library cookie-aware urllib opener and does not configure a proxy. The saved-report selection structure is intentionally explicit and must not be assumed to fit other ICP reports without discovering their own dimensions and hierarchy definitions.


## Official ICP 2017 archive acquisition

The official ICP 2017 Data Catalog dataset (ID `0038406`) exposes a complete CSV archive at:

- Archive: https://databankfiles.worldbank.org/public/ddpext_download/ICP_2017_csv.zip
- Catalogue: https://datacatalog.worldbank.org/search/dataset/0038406

The archive was independently inspected on 2026-11-10. It returned HTTP 200, 2,353,815 bytes, SHA-256 `ba91db66c3975aed7a0e5dc5c3b27ea1b5c130b08762a8568fb68a857307c8e2`, and passed ZIP CRC validation. It contains exactly three CSV members:

- `ICP_2017_Data.csv` (138,042 observation rows plus header; wide annual columns 2011–2017);
- `ICP_2017_Country-Metadata.csv` (214 metadata rows plus header);
- `ICP_2017_Series-Metadata.csv` (20 metadata rows plus header).

The data export contains 224 distinct country codes, 16 populated classification codes plus one blank classification value, and 48 series codes. Zimbabwe has 619 rows spanning 16 populated classifications and 47 series. These are source-structure counts, not a claim that all countries or all series are participating or fully observed. Country metadata identifies Zimbabwe as full-participation in both ICP 2011 and ICP 2017, USD currency unit, and 2008 SNA.

Acquisition is implemented by `tools.acquire_world_bank_icp_archive`:

```fish
uv run python -m tools.acquire_world_bank_icp_archive
```

The tool downloads the provider ZIP, checks the archive signature and CRC, requires the three named members, preserves the original ZIP and extracted CSVs, and records byte counts and SHA-256 hashes in a timestamped manifest. It writes only raw acquisition artifacts, a manifest and an assessment report. It does not parse or approve observations, write either database, alter source selection, or apply retention.

**Interpretation boundary:** the 2011–2017 columns alone do not identify each observation as a benchmark, revised benchmark, interpolation or extrapolation. Keep the entire archive under the distinct `icp_2017_cycle` release identity. Do not merge its 2017 observations with the ICP 2021 cycle's revised 2017 benchmark. The series metadata member contains 20 notes, not a complete dictionary for all 48 series; use the observation file's series code/name columns as the complete observed series catalogue. The inspector recognizes this wide-year/one-series-per-row layout and retains missing values, the observed series catalogue and country metadata without inferring unreported values.


## Official ICP 2011 workbook acquisition

The official ICP data page links the original 2011 results workbook:
https://pubdocs.worldbank.org/en/108821487172249299/2011-International-Comparison-Program-results.xlsx

The workbook is a distinct original 2011 release. It is not the revised 2011 series published as part of the ICP 2017 cycle. Acquire it with:

```fish
uv run python -m tools.acquire_world_bank_icp_2011_workbook
```

The acquisition preserves the provider workbook byte-for-byte and records the official source URL, retrieval time, HTTP response metadata, byte count and SHA-256 in a release-scoped manifest. It does not transform workbook sheets, infer missing observations, write either database, approve data, alter source selection or apply retention. The existing ICP export inspector reads XLSX sheets and reports their source release independently.

The original ICP 2011 DataBank source is also available at:
https://databank.worldbank.org/source/international-comparison-program-%28ICP%29-2011

Its published description reports 199 participating economies plus estimates for 15 non-participating economies, 26 analytical classifications, and multiple PPP, expenditure-share, nominal/PPP expenditure, per-capita and price-level indicators. These catalogue counts describe the source, not the completeness of any particular exported selection. Full DataBank extraction remains a separate acquisition task; do not treat the workbook as proof that every detailed DataBank series has been captured.


### Original ICP 2011 workbook structural inspection

The inspector now recognizes the specifically acquired
`2011-International-Comparison-Program-results.xlsx` under
`icp_2011_cycle`. It inventories every worksheet and preserves the original
table structure in three additional report files:

- `icp_2011_workbook_sheets.csv`: worksheet name, R/D/S table identifier and
  category (summary, detailed or supplementary), used dimensions, non-empty
  cell count and merged-range count;
- `icp_2011_workbook_rows.csv`: one record per non-empty worksheet row, with
  the row's ordered cell values serialized as JSON (including interior blank
  cells, preserving their original column positions—for example, a blank C cell
  remains `null` when D contains a value);
- `icp_2011_workbook_cells.csv`: one record per non-empty cell, retaining
  sheet, table, coordinate, row/column, cell data type and number format.


The sheet-title classifier accepts optional whitespace and zero-padded numeric
identifiers after the R, D or S prefix (for example, `R1 Summary`,
`D03` or `S2 Supplementary`). Unrecognized sheet titles remain inventoried
under `unclassified_sheet`; they are never silently assigned a table number.

This is a structural extraction, **not yet a semantic conversion into the
common annual observations table**. The workbook's R1–R7 summary, D1–D10
detailed and S1–S2 supplementary tables contain heterogeneous measures and
units (including national-currency expenditures, PPPs, PLIs, expenditure
shares and real/nominal expenditure measures). A cell value cannot safely be
assigned a common indicator, country identity, reference year or unit from
its position alone. The inspector therefore does not infer those semantics,
convert units, map country aliases, treat region aggregates as countries, or
add workbook values to latest-year/coverage selection. Source labels, units,
blank cells and table layout remain recoverable from the row/cell outputs.
A future table-specific mapping must be validated against the published
headings and footnotes before any of these values enter harmonized observations.

The workbook is counted as a recognized source artifact and its
`icp_2011_cycle` release contributes to the release inventory even though it
does not add annual observation rows. The original workbook remains unchanged.

### ICP 2011 semantic extraction and cross-release benchmark comparison

The structural workbook inventory is now supplemented by a separate semantic
assessment command:

```fish
uv run python -m tools.assess_world_bank_icp_benchmarks
```

The assessment reads the acquired original 2011 workbook and the latest
timestamped ICP export-inspection report. It emits:

- `icp_2011_workbook_semantic_observations.csv`: table-specific row/column
  observations for R1–R7, D1–D10 and S1–S2, retaining the workbook sheet,
  source cell, row, column code, original column-heading path, raw value,
  parsed value, reference year, measure family and unit;
- `benchmark_comparisons.csv`: only explicitly aligned benchmark comparisons;
- `benchmark_comparison_coverage.csv`: country/aggregate or exact
  country/classification/indicator match statuses, including unresolved identity
  and missing-source/value gaps;
- `benchmark_coverage.csv`: source-release/year/country/classification/indicator
  coverage with reported and missing counts and benchmark-role labels;
- `assessment.json`: extraction counts, comparison counts, interpretation
  rules and side-effect declaration.

The extractor locates R/D/S table identifiers as standalone tokens anywhere in descriptive worksheet titles (for example, `Detailed results - D3 PPPs`), rather than assuming the identifier is the first title character. The structural workbook inventory uses the same rule so both reports agree on table identity.

The table dictionary follows the official ICP 2011 result-table descriptions.
R1–R7 identify GDP, actual individual consumption, household individual
consumption, individual consumption by government, collective consumption by
government, gross fixed capital formation and domestic absorption. D1–D10
remain separate measure families: national-currency expenditure, expenditure
shares, PPP conversion factors, real expenditure, real-expenditure shares,
real expenditure per capita, per-capita indices, price-level indices, nominal
expenditure and nominal expenditure per capita. S1 and S2 remain supplementary
tables for Pacific Islands and estimated nonbenchmark economies. Summary
column codes retain their published column-specific measure and unit labels;
detailed-table category headings are retained from the workbook's own merged
and multi-row headings.

The semantic assessment reports which of the 19 expected R/D/S tables were
recognized. It fails closed if no semantic data rows can be decoded; a partial
table inventory is reported rather than silently treated as complete.

Country identity is deliberately conservative. The matcher uses the
inspector's delimiter-aware CSV reader and checks the source-reported country
code plus available long-name, country-name, economy-name and provider `Table Name` fields. The latter is important when the original ICP 2011 workbook uses a short display name (for example, `Zimbabwe`) while the ICP 2017 metadata long name is `Republic of Zimbabwe`; both source-published names resolve to the same ISO3 code. The source label and match status remain preserved in semantic observations. This avoids
silently treating a semicolon/tab-delimited metadata file as a single-column CSV.
A workbook economy receives an ISO3 code only on a unique normalized match.
A small explicit alias table covers known workbook spelling/footnote variants
(such as Sudan's footnote suffix and Cape Verde/Swaziland naming); an alias is
accepted only when its target name resolves to exactly one code in the captured
metadata. Alias matches are labelled separately from exact matches. No region
or total is mapped to a country. Unmatched labels remain in the semantic
extract for review.
The reference year is the workbook's 2011 benchmark year. Missing cells remain
explicit missing records whenever the source row contains reported values.

Two comparison paths are currently implemented:

1. Original 2011 workbook D3 PPP factors versus the ICP 2017-cycle 2011
   `PPPGlob` observations. A pair is emitted only for the same exact country
   code and recognized aggregate (GDP, AIC, total household consumption,
   individual government consumption, collective government consumption,
   GFCF or domestic absorption). The D3 measure “Individual consumption
   expenditure by households without housing” is retained as
   `HOUSEHOLD_CONSUMPTION_EX_HOUSING` but is not matched to the total
   household-consumption indicator. This prevents a subset measure from being
   compared with the revised benchmark's total household aggregate. Both
   compared values are local currency units per international dollar (US$=1),
   consistent with the ICP/WDI PPP conversion-factor unit.
2. Original ICP 2017 benchmark versus revised ICP 2017 benchmark in the ICP
   2021 saved-report export. A pair is emitted only for an exact country,
   classification-code and indicator-code match at 2017. The source labels
   “Households and NPISHs final consumption expenditure” (series `9100000`)
   and “General government final consumption expenditure” (series `9270000`)
   receive distinct canonical aggregate labels. The NPISHs spelling and the
   archive’s code-prefixed series label are both recognized. Government
   consumption is not conflated with the 2011 individual/collective government
   split.

The 2017 comparison coverage also distinguishes a country, classification
or indicator that is outside the captured saved-report selection from a
missing observation inside that selection. The current ICP 2021 saved report
contains only six series and one classification; its unmatched count is
therefore not a global ICP missing-data rate. Statuses such as
`indicator_not_in_revised_export_scope` and
`classification_not_in_revised_export_scope` identify selection boundaries,
while `missing_revised_2017_value` identifies an explicit missing source row.
These scope diagnostics describe the captured export only and do not imply
that the wider ICP catalogue lacks the series.

The coverage output labels the ICP 2017-cycle 2011 and 2017 benchmark years,
and the ICP 2021-cycle 2017 and 2021 benchmark years. It labels 2018–2020 as
interpolation and 2022–2023 as GDP PPP extrapolation only for GDP; other
annual-series roles are not inferred. These labels describe the published ICP
2021 cycle and do not manufacture observations or fill missing years.

The comparison command uses the most recent `inspection_*/observations_long.csv`
report. Run `tools.assess_world_bank_icp_exports` first after acquiring new
exports. The present comparison scope is limited to the releases actually
captured: original ICP 2011 workbook, ICP 2017 archive and the six-series
ICP 2021 saved report. It does not claim ICP 2005 or every ICP 2021 detailed
table has been acquired. A missing pair means no exact match was available; it
is not evidence of zero or of an unchanged value.

No Project DB or Game DB writes, approvals, source-selection changes, canonical
promotion, imputation, interpolation or extrapolation are performed by this
assessment. Its CSVs are research outputs and remain outside the production
data path.

Official table/release references:
- ICP 2011 DataBank description and classification scope:
  https://databank.worldbank.org/source/international-comparison-program-%28ICP%29-2011
- World Bank ICP data page, including the distinction between original 2017
  results and the 2017 revision in the 2021 cycle:
  https://www.worldbank.org/en/programs/icp/data
- World Bank ICP 2011 results announcement:
  https://blogs.worldbank.org/en/opendata/full-set-international-comparison-program011-results-now-available
- ICP 2011 global report, including summary result table units:
  https://pubdocs.worldbank.org/en/142181487105157824/ICP-2011-report.pdf
- World Bank WDI PPP conversion-factor metadata, defining the unit as local
  currency units per international dollar:
  https://databank.worldbank.org/metadataglossary/world-development-indicators/series/PA.NUS.PPP

## Data Catalog resource boundary

The Data Catalog API's resource records include website and DataBank navigation references as well as machine-readable resources. Only actual downloadable file resources may be fetched from a /download endpoint. A website or DataBank reference is not a file; attempting to download it as one produces HTTP 400.

The existing tools.acquire_world_bank_icp_snapshot captures the ICP 2021 Data Catalog metadata/resource listing and downloads only resources explicitly identified as file formats. DataBank exports are a separate authenticated workflow and must retain the report URL, selected dimensions, export format, retrieval timestamp and file hash. Do not silently substitute a preview page or a limited saved report for a full-country/full-indicator export.

## Inspection

Run:

```fish
uv run python -m tools.assess_world_bank_icp_exports
```

The inspector scans CSV and XLSX files under raw_data/sources/world_bank_icp/ and recognizes:

- wide DataBank exports, with one column per indicator;
- long exports, with one indicator/value per row; and
- the official ICP 2017 archive's one-row-per-country/classification/series layout, with separate annual value columns for 2011–2017; and
- the original ICP 2011 workbook's heterogeneous R/D/S tables, preserved as sheet inventory, row arrays and cell-level structure (not harmonized observations).

For the ICP 2017 archive, each annual column is expanded into a separate observation while retaining the original year-column name, source row, country, classification, series code/name and release identity. Blank and `..` cells remain explicit missing observations; they do not enter latest-nonmissing selection. The country metadata CSV is retained in a separate `country_metadata.csv` report, and the observed series code/name catalogue is included in `series_metadata.csv`. Definitions from the provider's smaller series-metadata member are joined by release and indicator code where available. This does not infer benchmark/interpolation/extrapolation status or participation status from a missing observation.

It creates timestamped reports under reports/sources/world-bank-icp/:

- observations_long.csv: all extracted rows, including missing values;
- latest_available_by_country_indicator.csv: latest non-missing value independently by country, classification and indicator;
- coverage_by_country_indicator.csv: first/latest available year, count and observed years;
- series_metadata.csv: observed indicator codes/names plus provider definitions where available;
- country_metadata.csv: source-reported country metadata rows, kept separate from observations;
- icp_2011_workbook_sheets.csv, icp_2011_workbook_rows.csv and icp_2011_workbook_cells.csv: structural extracts of the original ICP 2011 workbook, kept separate from annual observations and latest-value coverage.

CSV input decoding detects UTF-8/UTF-8 BOM and UTF-16 BOM, then uses strict Windows-1252 and Latin-1 fallbacks for legacy DataBank exports; the detected encoding is recorded in the sheet/source label. The DataBank `Series_-_Metadata.csv` member repeats the complete observation table before appending a two-column `Code` / `Indicator Name` dictionary; the inspector treats it as a metadata artifact, skips the repeated observations, and extracts the trailing indicator definitions into `series_metadata.csv`. Empty/footer rows (including `Data from database` and `Last Updated`) are excluded because they lack a country and reference year. Structural DataBank fields such as Time Code are excluded from wide-format indicator detection. Source-release identity is derived from the acquisition directory (`icp_YYYY_cycle` or `icp_2021_saved_report`) and is part of every latest-value and coverage key, preventing different ICP vintages from being collapsed. Latest-value selection uses the same release/country/classification/indicator key as the coverage calculation. CSV report fields, including numeric observations, are serialized as text; downstream numeric comparisons should parse the value field explicitly. The latest-value rule is observation-based, not a common global cutoff. Missing observations remain visible. No zeros, carry-forward values, interpolation, extrapolation or imputation are created by this inspector. Published imputed observations must be identified from the source's own status metadata and must not be confused with missing observations.

## Interpretation requirements

Keep separate:

- original benchmark versus revised benchmark;
- benchmark versus annual interpolation versus extrapolation;
- participating versus imputed economy;
- PPP conversion factors versus PPP-based expenditure values and price-level indices;
- each indicator's unit and classification;
- source-reported missingness versus a country/indicator absent from an export.

The ICP 2021 publication provides 2021 benchmark results, revised 2017, annual PPP series 2017–2021 and extrapolated GDP PPPs for 2022–2023. WDI's later annual PPP series are a separate extrapolated statistical series, not new ICP benchmark cycles. Do not label WDI years after 2023 as new ICP benchmark observations.

No source-selection change, approval, Project DB write, Game DB write or canonical data promotion is performed by acquisition or inspection.

## Validation

```fish
uv run python -m pytest -v tests/test_world_bank_icp_archive.py tests/test_world_bank_icp_databank.py tests/test_world_bank_icp_exports.py tests/test_world_bank_icp_2011_workbook.py tests/test_world_bank_icp_benchmarks.py tests/test_world_bank_icp_snapshot.py tests/test_annual_ppp_lineage.py
uv run python -m compileall -q tools
uv run python -m tools.assess_world_bank_icp_exports
uv run python -m tools.assess_world_bank_icp_benchmarks
```

Owner-run terminal output is the validation authority.


## Annual PPP lineage assessment across ICP, WDI and IMF WEO

Run the read-only country/year lineage assessment after refreshing the ICP export inspection and benchmark assessment and after acquiring the required WDI API snapshot:

```fish
uv run python -m tools.assess_world_bank_icp_exports
uv run python -m tools.assess_world_bank_icp_benchmarks
uv run python -m tools.assess_annual_ppp_lineage
```

The assessment selects the latest timestamped ICP inspection and semantic benchmark reports, verifies the WDI snapshot manifest and every referenced raw response through the existing snapshot loader, and fingerprints the fixed October 2026 IMF WEO CSV. An alternate WDI manifest can be supplied with `--wdi-manifest`; source inputs are not fetched or modified by this assessment.

Outputs are written under `reports/sources/annual-ppp-lineage/`:

The assessment is a **global country screen**, not a Zimbabwe-only report. It uses the country universe represented by the captured WDI/WEO diagnostic union; each arithmetic metric uses only the years where its required source observations overlap. Source-specific ICP rows remain separate. It emits one row per diagnostic country in `country_reconciliation_screen.csv`, with screening signals for:
- WDI reported PPP GDP versus current-LCU GDP divided by WDI `PA.NUS.PPP`;
- persistent WDI/WEO reported PPP-GDP differences;
- stable WDI/WEO implied-factor ratios that are materially different from unity across multiple observed years; and
- large year-to-year breaks in those factor ratios.

The explicit triage thresholds are 0.5% for the WDI arithmetic identity, 5% for a persistent PPP-GDP gap, 1% relative median absolute deviation plus a median factor-ratio deviation greater than 1% from unity for a stable off-unity factor-ratio flag, and 25% for a year-to-year factor-ratio break. Stable ratios close to 1.0 are treated as neutral rather than anomalous. A stable off-unity ratio is flagged only when at least three values are available and no large adjacent-year break is present. At least three consecutive years are required for a persistent-gap flag; at least three observed years are required for a stable-ratio flag. The CSV records the actual years exceeding both the WDI arithmetic-mismatch threshold and the WDI/WEO PPP-GDP gap threshold, so a low full-period median does not hide a historical consecutive run. These thresholds prioritize review; they are not claims of source error, unit equivalence or currency redenomination. The Markdown report shows up to 25 prioritized flagged countries, while the CSV retains the full country screen. Zimbabwe is included in the same global output and is not given a special calculation path.

- `annual_ppp_lineage.csv`: source/release-specific ICP GDP PPP factors, WDI annual PPP conversion factors and current-PPP GDP, WEO current-PPP GDP, and a separately identified WEO NGDP/PPPGDP derived factor. Country, year, source release, lineage role, unit, source file/row and observation status are retained.
- `country_year_diagnostics.csv`: WDI reported PPP GDP versus the LCU/PPP-factor arithmetic reconstruction, and WDI factors versus the WEO-implied factor. Ratios are explicitly arithmetic diagnostics, not assertions of semantic equivalence.
- `country_reconciliation_screen.csv`: global one-row-per-country screening of arithmetic mismatches, persistent WDI/WEO PPP-GDP gaps, stable off-unity factor-ratio patterns and abrupt factor-ratio breaks.
- `assessment.json` and `assessment.md`: input fingerprints, source coverage, interpretation limits, side-effect declaration and a Zimbabwe diagnostic table plus a global country-screen summary.

The original 2011 workbook D3 GDP factor, ICP 2017-cycle revised 2011 and original 2017 values, and ICP 2021-cycle revised 2017, 2021 benchmark, documented 2018–2020 interpolation and documented 2022–2023 GDP PPP extrapolation remain distinct rows for all captured countries. ICP 2017 archive years outside its explicit benchmark roles remain unclassified. The ICP 2021 saved-report export is still limited to its captured selection; absence from that export is not treated as global source missingness.

WDI `PA.NUS.PPP` remains a rolling annual API series. This capture does not provide observation-level benchmark/interpolation/extrapolation lineage, so the tool does not infer it. WEO `PPPGDP` is retained as reported current-PPP GDP; WEO `NGDP / PPPGDP` is separately marked as a derived arithmetic factor. The rounded WEO `PPPEX` field is not used for precise reconciliation. ICP factors are not normalized across release currency denominations. Cross-source factor ratios remain flagged for currency denomination, redenomination, national-accounts vintage and reference-unit review.

This assessment does not fetch new source data, write raw data or manifests, write either database, create approvals, change source selection, promote canonical data, impute observations, or apply retention. It does not assert that the WDI/WEO arithmetic gap is explained until the underlying currency and benchmark lineage is evidenced.

## Public-source review of the global PPP anomaly screen (2026-11-17)

The 53-country screen is a triage list, not a list of 53 data errors. Public-source checks were made against the flagged periods and the October 2026 WEO / November 2026 WDI capture. This review changes interpretation only: no source values, canonical values, source selection, approvals or databases are changed.

### Global methodology

The World Bank confirms that ICP 2021 contains a 2021 benchmark, revised 2017 benchmark, interpolated PPPs for 2018–2020, and GDP PPP extrapolations for 2022–2023. Nonparticipants can receive model-imputed PPPs. National-source GDP, population and exchange-rate inputs supplied to ICP can differ from WDI because of vintage or statistical-method differences. ICP 2021 benchmark PPPs also need not converge with PPPs extrapolated from the preceding benchmark.

Sources:
- https://www.worldbank.org/en/programs/icp/faq
- https://www.worldbank.org/en/programs/icp/data
- https://www.worldbank.org/en/programs/icp/methodology
- https://datahelpdesk.worldbank.org/knowledgebase/articles/665452-how-do-you-extrapolate-the-ppp-conversion-factors

The IMF WEO PPP factors are based on ICP 2017–2021 and extended backward/forward using relative GDP-deflator growth. Non-survey-year factors are updated at each WEO release using the latest nominal GDP and relative deflators; PPPGDP is updated using the latest WEO data. WEO historical values may also be revised, spliced or represented by IMF staff estimates where national data are incomplete.

Sources:
- https://www.imf.org/en/publications/weo/frequently-asked-questions
- https://www.imf.org/external/datamapper/datasets/WEO

Interpret the flags independently:
1. A **WDI arithmetic mismatch** means reported WDI PPPGDP does not reproduce current-LCU GDP divided by WDI GDP PPP factor within 0.5%. War, sanctions or recession cannot explain a failure of this same-source identity. It remains unresolved unless a series definition, unit or vintage difference is demonstrated.
2. A **WDI/WEO PPPGDP gap** compares independently maintained series. Different benchmark vintages, interpolation/extrapolation, national-account revisions and WEO country-desk estimates can produce legitimate differences.
3. A **factor break** may reflect redenomination, currency-unit changes, statistical rebasing or a source splice, but the explanation must be tied to the country and year.
4. A **stable off-unity factor ratio** is a persistent difference, not a break. Do not normalize it without confirming currency denomination, PPP benchmark and series definitions.

### Country-specific findings supported by public sources

| Country / screen signal | Public evidence | Disposition |
|---|---|---|
| **Sudan** — gap 2020–2025; factor break 2022 | World Bank estimates real GDP contracted 29.4% in 2023 and 14% in 2024 after the April 2023 conflict; it estimates a 3.1% recovery in 2025. Conflict damaged productive capacity and disrupted agriculture and services. A separate World Bank report documents renewed official/parallel exchange-rate divergence. https://www.worldbank.org/ext/en/country/sudan ; https://documents1.worldbank.org/curated/en/099051925180542315/pdf/P178527-6a7d4d70-52be-49b7-87e5-ead89050a99b.pdf | Accept the real macroeconomic abnormality. Keep the WDI/WEO PPP level gap as a separate vintage/reconciliation issue. |
| **South Sudan** — factor break 2016; median ratio 0.893 | IMF documents civil conflict, falling oil production/prices, severe FX and revenue shortfalls, inflation peaking at 550%, and precipitous currency depreciation in 2016. https://www.elibrary.imf.org/view/journals/002/2017/073/article-A004-en.xml | Accept 2016 as a genuine macro/currency shock. The persistent factor-level difference still requires unit/benchmark reconciliation; do not apply a 0.893 correction. |
| **Lebanon** — gap 2020–2024 | IMF reports real GDP contractions of 25.9% in 2020 and 10.0% in 2021, and GDP-deflator inflation of 61.1%, 140.8%, 165.0% and 290.0% in 2020–2023. https://www.imf.org/en/news/articles/2023/06/28/pr23245-lebanon-imf-executive-board-concludes-2023-article-iv-consultation-with-lebanon | Accept the economic/price-level abnormality. The PPPGDP difference remains a separate cross-source issue. |
| **Iran** — WDI arithmetic mismatch 2014–2015; gap 2014 | IMF country data document sanctions-related output pressure and recovery after sanctions relief. Iran's national accounts are reported on a fiscal year beginning 21 March. https://www.imf.org/en/news/articles/2017/02/27/pr1765-imf-executive-board-concludes-2016-article-iv-consultation-with-the-islamic-republic-of-iran | Sanctions are relevant macro context, but do not explain a same-source WDI identity mismatch. Fiscal/calendar-year alignment and series vintages remain to be checked. |
| **Nigeria** — WDI arithmetic mismatch 2014–2018 | Nigeria's NBS says the 2014 rebasing changed the base year from 1990 to 2010 and revised nominal/real GDP and growth for 2010–2014; historical back revisions followed in 2016. https://www.nigerianstat.gov.ng/pdfuploads/GDP_Comparability.pdf ; https://www.nigerianstat.gov.ng/pdfuploads/GDP%201981%20to%202010%20post%20rebasing%20revision.pdf | Accept national-account vintage revisions as a valid explanation for cross-source level differences. They do not by themselves explain the WDI arithmetic mismatch. |
| **Bangladesh** — WDI arithmetic mismatch 2014–2015 | IMF documents a November 2021 rebasing to 2015/16 prices with expanded survey coverage; nominal GDP was revised 10.2–19.8% for FY2016–FY2021. https://www.elibrary.imf.org/view/journals/002/2023/066/article-A001-en.xml | Accept a material national-account vintage break. Preserve fiscal-year basis and do not use it alone to excuse a same-source identity mismatch. |
| **Sierra Leone** — gap 2014–2016; median factor ratio about 0.001 | Stats SL published a July 2024 rebasing from 2006 to 2018, implemented 2008 SNA and improved informal-sector coverage. IMF reports nominal GDP in 2018–2022 rose 56–74% against the prior series. https://www.elibrary.imf.org/view/journals/002/2024/321/article-A001-en.xml ; https://www.statistics.sl/images/StatisticsSL/Documents/gdp/gdp_2023/Rebased_GDP_Report_2018_base_year_and_revised_series.pdf | Accept the historical GDP revision. The 0.001 factor ratio is not an ordinary macroeconomic effect; treat it as a likely unit/scale or series-definition problem pending direct unit inspection. |
| **Equatorial Guinea** — gap 2014–2016 | IMF documents a 2016 national-account rebasing from 1986 to 2006 that raised measured GDP about 30%; a 2018 update revised 2014–2017, with nominal GDP about 14% higher by 2017 than the earlier vintage. https://www.imf.org/external/pubs/ft/scr/2016/cr16341.pdf ; https://www.elibrary.imf.org/view/journals/002/2018/310/article-A001-en.xml | Accept historical national-account revisions as a plausible explanation. Keep vintages separate. |
| **India** — WDI arithmetic mismatch 2014–2021 | India's 2026 national-accounts series changes the base year from 2011/12 to 2022/23; the official release says the new-methodology back series is expected later in 2026. https://www.pib.gov.in/PressReleasePage.aspx?PRID=2233518 ; https://www.pib.gov.in/PressNoteDetails.aspx?ModuleId=4&NoteId=157582 | The 2026 revision does not explain the historical mismatch in this capture. Keep the identity flag unresolved. |
| **Fiji** — WDI arithmetic mismatch 2014–2018 | Fiji's statistics office publishes a GDP rebase to 2019 and a compilation guide. https://www.statsfiji.gov.fj/statistics/economic-statistics/national-accounts/ | Rebasing is relevant context, not proof of the same-source mismatch. Keep unresolved. |
| **Papua New Guinea** — stable factor ratio about 0.870 | The national statistics office publishes overlapping GDP vintages (2011–2018, 2013–2019 and 2016–2022). https://www.nso.gov.pg/statistics/economy/gross-domestic-products/ | A national-account vintage review is warranted. The stable factor ratio is not yet explained by a confirmed unit or benchmark difference; do not adjust. |
| **Somalia** — gap 2014–2017; median factor ratio about 25,900 | The World Bank's 2018 Somalia Economic Update publishes GDP estimates for 2013–2016 and documents the developing national-account data environment. https://documents1.worldbank.org/curated/en/975231536256355812/pdf/REPLACEMENT-PUBLIC-Somalia-Economic-Update-3-FINAL.pdf | The extreme factor ratio is not an acceptable economic fluctuation. Treat as a probable unit, currency denomination or series-definition problem. Do not numerically correct before establishing both source units. |
| **Bolivia** — WDI arithmetic mismatch and gap 2014–2016 | Public WDI/WITS metadata confirms historical PPP GDP uses ICP benchmark extrapolation or imputation, but the sources reviewed do not establish a Bolivia-specific event explaining the same-source mismatch. https://wits.worldbank.org/CountryProfile/en/Country/BOL/Year/2014 | Unresolved arithmetic issue; do not attribute it to a macro shock. |
| **Libya** — gap 2014–2016 | IMF reports a 24% real GDP contraction in 2014 amid deteriorating security and oil-production disruption. https://www.imf.org/_next/data/OPXKbpp2La91iW-gTVkBX/en/-/media/websites/imf/imported-full-text-pdf/external/np/pp/eng/2015/_100815a.pdf.json | Accept the real GDP shock. The multi-year PPPGDP gap still requires source-vintage reconciliation. |
| **Israel** — gap 2023–2025 | IMF's 2026 Article IV describes a sharp output contraction after October 2023 followed by recovery; annual real GDP growth was 1.0% in 2024 and 2.9% in 2025. https://www.elibrary.imf.org/view/journals/002/2026/161/article-A001-en.xml | Accept the conflict-related macroeconomic shock. It does not establish the correctness of the PPPGDP level difference. |
| **Türkiye** — gap 2022–2024 | IMF reports GDP-deflator growth of 96.0% in 2022 and 68.2% in 2023 in its 2024 Article IV vintage, alongside high inflation. https://www.imf.org/en/news/articles/2024/10/11/pr-24369-turkiye-imf-executive-board-concludes-2024-aiv-consultation | Accept the high-inflation/nominal-price abnormality. A persistent PPPGDP gap with near-unity median factor ratio is more consistent with source-vintage or nominal-GDP revision differences than a separate currency conversion correction. |
| **Myanmar** — gaps 2014–2015 and 2021–2025 | Post-2021 conflict and economic disruption are relevant to recent estimates, but do not explain the separated earlier and later periods with one event. WEO methodology allows staff estimates where national data are incomplete. https://www.imf.org/en/publications/weo/frequently-asked-questions | Recent uncertainty is plausible; the earlier gap remains unexplained. Keep both as source-comparison flags. |
| **Central African Republic** — gap 2014–2025 | The project's existing reconciliation found revised ICASEES SNA 2008, 2019-base GDP agrees with WEO, while WDI's 2019–2021 local-currency numerator is materially lower. The revised series was published in 2026. | Accept the documented national-account vintage difference. Preserve the WDI/revised-ICASEES numerator discrepancy; do not overwrite either source. |
| **Guinea** — gap 2014–2025 | The project's existing reconciliation found WDI local-currency GDP follows the older SNA 1993 series, while INS's newer 2018-base SNA 2008 series is materially higher. The newer series marks 2018–2020 definitive and 2021–2024 rapid estimates. | Accept the documented national-account vintage difference. Keep old and new series distinct. |

### Remaining flagged countries: explanation not established

The following flags remain unresolved or are only generally consistent with benchmark/vintage differences. This does not prove the values wrong; it means the public sources reviewed did not establish a country-year explanation sufficient to accept or numerically correct the flagged series.

- **Jamaica:** arithmetic mismatch in 2014. Its near-unity WDI/WEO factor ratio does not resolve the WDI same-source identity.
- **Brunei Darussalam, Iraq, Kuwait and Qatar:** factor breaks in 2015 (Iraq's and Qatar's PPPGDP gaps are 2014 and 2016; Kuwait's are 2014–2016). Their near-unity full-period factor ratios do not prove a redenomination. Check exact adjacent-year factors, units and release vintage before assigning a cause.
- **Stable off-unity Pacific factor ratios:** Micronesia (0.881), Kiribati (0.903), Marshall Islands (0.865), Nauru (0.836), Palau (0.835), Papua New Guinea (0.870), Solomon Islands (0.894), Tonga (0.887), Vanuatu (0.868) and Samoa (0.874). Island-economy controls are part of the ICP imputation methodology, and nonparticipants may receive model-imputed PPPs. The screen does not establish which country was imputed in each release, nor does this methodology alone explain the size of each ratio. Do not apply a common Pacific adjustment.
- **Other persistent PPPGDP gaps:** Burundi, Guinea-Bissau, Republic of the Congo, Latvia, Lithuania, Bhutan, Dominica, Iceland, Liberia, Albania, Portugal, Lesotho, Mauritania, Malawi, Nepal, Suriname, Timor-Leste and Uzbekistan, in addition to the countries discussed above. Their exact flagged years remain in the country_reconciliation_screen.csv report. Where the median factor ratio is near one, the gap is a WDI/WEO level/vintage difference until nominal GDP and benchmark histories are aligned; it is not evidence of a separate conversion-factor shock.
- **Additional gaps already discussed above:** Argentina, Bolivia, Fiji, Iran, Lebanon, Libya, Myanmar and Türkiye remain source-comparison cases even where a macroeconomic or statistical-revision explanation is available.

For the Pacific group, the ICP methodology uses GDP per capita at market exchange rates, trade shares, age dependency and controls for regional, island and landlocked economies in its imputation regressions: https://www.worldbank.org/en/programs/icp/methodology. This is a reason to inspect participation/imputation metadata, not permission to assume every island observation is imputed.

### Screen disposition

| Signal | Disposition |
|---|---|
| Economic shock supported by official/IMF evidence (Sudan, South Sudan, Lebanon, Libya, Israel; relevant recent Myanmar years) | Accept the real macroeconomic abnormality. Do not alter source values. Keep PPPGDP gaps as separate lineage questions. |
| National-account revision documented (Nigeria, Bangladesh, Sierra Leone, Equatorial Guinea, Guinea, Central African Republic; Fiji and PNG as relevant context) | Accept a vintage/revision explanation where the documented revision years overlap. Preserve source vintages and units. |
| WDI same-source arithmetic mismatch (Zimbabwe, Bolivia, India, Fiji, Nigeria, Iran, Bangladesh, Jamaica) | Not explained by war, sanctions or GDP rebasing alone. Keep flagged until exact series vintage, units and identity are reconciled. |
| Extreme implied-factor ratios (Somalia and Sierra Leone) | Treat as probable scale/unit/source-definition issues, not acceptable economic anomalies. No numerical correction authorized. |
| Stable Pacific off-unity ratios | Benchmark/imputation comparability is plausible but not confirmed country by country. Do not normalize or apply a regional adjustment. |
| Other WDI/WEO PPPGDP gaps | Retain as source-vintage comparison flags unless a specific country-year revision is documented. |

No values were corrected in this review. No country is cleared of a same-source WDI arithmetic mismatch merely because it experienced war, sanctions, inflation or GDP rebasing. For unresolved rows, the next defensible check is a release-by-release comparison of nominal GDP, PPP factor, PPPGDP, currency unit and observation status—not a blanket adjustment.


### Follow-up: same-source arithmetic and currency-unit reconciliation (2026-11-17)

The global diagnostic output was reviewed at country-year level. The WDI arithmetic ratio is `NY.GDP.MKTP.PP.CD / (NY.GDP.MKTP.CN / PA.NUS.PPP)`; values below are the mean ratio over flagged years, not correction factors.

| Country | Flagged years | Mean reported / reconstructed WDI PPP GDP | Additional evidence and disposition |
|---|---:|---:|---|
| Bangladesh | 2014–2015 | 1.1979 | WDI current-LCU GDP is 0.8348 times WEO NGDP on average in these two years. BBS's November 2021 rebasing to 2015/16 prices revised nominal GDP by roughly 10–20% for FY2016–FY2021; the 2016 onward WDI and WEO LCU series align closely. A vintage break is plausible for the transition, but the same-source identity mismatch remains unexplained. https://www.imf.org/-/media/files/publications/cr/2023/english/1bgdea2023001.pdf |
| Bolivia | 2014–2016 | 1.2244 | WDI current-LCU GDP is 0.8325 times WEO NGDP on average. IMF reports the 1990 national-accounts base year was outdated and INE had begun rebasing to 2017 and implementing 2008 SNA. This is a strong vintage-comparability lead, not proof that it explains the WDI identity mismatch. https://meetings.imf.org/en/-/media/files/publications/cr/2025/english/1bolea2025001-print-pdf.pdf |
| Fiji | 2014–2018 | 0.9817 | Small, stable 1.83% difference. Fiji rebased GDP first to 2014 (2019 release) and later to 2019 (2025 release). Relevant vintage context; no exact same-source reconciliation established. https://www.statsfiji.gov.fj/download/69/gross-domestic-product/3801/gdp-rebase-2014-2.pdf ; https://www.statsfiji.gov.fj/fijis-gross-domestic-product-gdp-2024-rebase-2019/ |
| India | 2014–2021 | 0.9713 | Small, stable 2.87% difference. WDI metadata identifies FY reporting (year-end 31 March) and the 2011/12 base; India's new 2022/23-base series was released in February 2026. Fiscal-year alignment and vintage remain relevant, but do not establish the cause of this historical identity gap. https://databank.worldbank.org/metadataglossary/global-findex-database/country/IND ; https://www.pib.gov.in/PressReleasePage.aspx?PRID=2233518 |
| Iran | 2014–2015 | 1.0426 | WDI current-LCU GDP is 0.8594 times WEO NGDP on average across 2014–2025. Iran's fiscal year begins 21 March, and UN national-accounts data expose parallel 1993-SNA and 2008-SNA series for 2014–2015. These are material alignment/vintage issues; sanctions are not an explanation for the WDI identity failure. https://data.un.org/Data.aspx?d=SNA&f=group_code%3A401%3Bitem_code%3A5%3Bcountry_code%3A364&q=Gross+Domestic+Product+Iran ; https://www.imf.org/en/news/articles/2017/02/27/pr1765-imf-executive-board-concludes-2016-article-iv-consultation-with-the-islamic-republic-of-iran |
| Jamaica | 2014 | 1.0546 | Single-year mismatch. Jamaica's 2025 national-accounts revision rebased constant-price GDP to 2015 and revised the series back to 2015, so it does not explain the 2014 observation. Keep unresolved. https://jis.gov.jm/system-of-national-accounts-updated/ |
| Nigeria | 2014–2018 | 1.4082 | WDI current-LCU GDP is 0.7101 times WEO NGDP on average. NBS's 2014 rebasing moved the base year from 1990 to 2010 and revised 2010–2014; back revisions followed in 2016. This confirms a major vintage change, but the mismatch continuing through 2018 needs a direct vintage/series check. https://www.nigerianstat.gov.ng/pdfuploads/GDP_Comparability.pdf ; https://www.nigerianstat.gov.ng/pdfuploads/GDP%201981%20to%202010%20post%20rebasing%20revision.pdf |
| Zimbabwe | 2014–2018 | 1.5279 | The 2014–2018 identity mismatch predates the 2019 RTGS/ZWL transition. Currency and national-accounts disruptions are relevant context, but they do not yet explain the constant 1.5279 ratio over these five years. Keep the identity flag; do not attribute it solely to the later redenominations. |

The arithmetic-ratio field in the diagnostic CSV is named `wdi_ppp_gdp_arithmetic_ratio_reported_to_implied`. A display command that requests a different alias will print an empty/None value even though the actual diagnostic field is populated; use the exact CSV header when inspecting rows.

#### Confirmed currency-unit interpretations

- **Sierra Leone:** WDI PPP arithmetic reconciles within tolerance. The WDI/WEO factor ratio is approximately 0.001 throughout 2014–2025, and WDI current-LCU GDP is approximately 0.001 times the WEO nominal-GDP value. The Bank of Sierra Leone redenominated the Leone at 1,000 old Leones to 1 new Leone, effective 1 July 2022. This exact scale relationship is consistent with the two sources expressing the historical series in different Leone denominations. Preserve both original values and units; do not treat the factor ratio as an economic anomaly or rewrite source values. https://bsl.gov.sl/Public%20Notice%20on%20Redenomination.pdf ; https://www.imf.org/-/media/files/publications/cr/2024/english/1sleea2024001-print-pdf.pdf
- **Somalia:** The October 2026 WEO CSV labels NGDP only as `Domestic currency`, which is not a sufficiently specific currency-unit declaration. Country-specific official evidence resolves the denomination: the Somali National Bureau of Statistics' 2025 national accounts report current-price GDP in millions of U.S. dollars, and its 2025 value (US$13.234 billion) matches the WEO NGDP value 13.234 (billions). Therefore the WEO NGDP value must not be treated as Somali-shilling GDP or used to derive a Somali-shilling-per-international-dollar factor. The annual-lineage assessor now applies this documented Somalia-specific unit override while preserving the raw WEO unit label. WDI current-LCU GDP remains in Somali shillings. The WDI/WEO PPPGDP level difference in 2014–2017 remains a separate comparison issue. Somalia's 2026 national accounts publication uses a 2022 base year and presents the 2019–2025 series in current U.S. dollars. https://nbs.gov.so/2026/ ; https://nbs.gov.so/wp-content/uploads/2026/11/Somalia-GDP-2025.pdf

The annual-lineage assessor now retains the raw WEO NGDP value and its unit basis, but only derives a WEO implied LCU-per-international-dollar factor when NGDP is not explicitly denominated in U.S. dollars. For USD-denominated NGDP, `weo_ngdp_current_lcu` and the derived WEO factor are left null. This prevents Somalia's USD nominal GDP from contaminating the factor-ratio screen. It does not alter WDI PPPGDP comparisons or any source observations.
