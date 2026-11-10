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
- `benchmark_coverage.csv`: source-release/year/country/classification/indicator
  coverage with reported and missing counts and benchmark-role labels;
- `assessment.json`: extraction counts, comparison counts, interpretation
  rules and side-effect declaration.

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

Country identity is deliberately conservative: a workbook economy receives an
ISO3 code only when its normalized name uniquely matches a source-reported
ICP 2017 country-metadata long name. No alias, historical name, region or total
is silently mapped. Unmatched labels remain in the semantic extract for review.
The reference year is the workbook's 2011 benchmark year. Missing cells remain
explicit missing records whenever the source row contains reported values.

Two comparison paths are currently implemented:

1. Original 2011 workbook D3 PPP factors versus the ICP 2017-cycle 2011
   `PPPGlob` observations. A pair is emitted only for the same exact country
   code and recognized aggregate (GDP, AIC, household consumption, individual
   government consumption, collective government consumption, GFCF or
   domestic absorption). Both values are local currency units per international
dollar (US$=1), consistent with the ICP/WDI PPP conversion-factor unit.
2. Original ICP 2017 benchmark versus revised ICP 2017 benchmark in the ICP
   2021 saved-report export. A pair is emitted only for an exact country,
   classification-code and indicator-code match at 2017.

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
uv run python -m pytest -v tests/test_world_bank_icp_archive.py tests/test_world_bank_icp_databank.py tests/test_world_bank_icp_exports.py tests/test_world_bank_icp_2011_workbook.py tests/test_world_bank_icp_benchmarks.py tests/test_world_bank_icp_snapshot.py
uv run python -m compileall -q tools
uv run python -m tools.assess_world_bank_icp_exports
uv run python -m tools.assess_world_bank_icp_benchmarks
```

Owner-run terminal output is the validation authority.
