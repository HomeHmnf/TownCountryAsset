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

## Data Catalog resource boundary

The Data Catalog API's resource records include website and DataBank navigation references as well as machine-readable resources. Only actual downloadable file resources may be fetched from a /download endpoint. A website or DataBank reference is not a file; attempting to download it as one produces HTTP 400.

The existing tools.acquire_world_bank_icp_snapshot captures the ICP 2021 Data Catalog metadata/resource listing and downloads only resources explicitly identified as file formats. DataBank exports are a separate authenticated workflow and must retain the report URL, selected dimensions, export format, retrieval timestamp and file hash. Do not silently substitute a preview page or a limited saved report for a full-country/full-indicator export.

## Inspection

Run:

```fish
uv run python -m tools.assess_world_bank_icp_exports
```

The inspector scans CSV and XLSX files under raw_data/sources/world_bank_icp/ and recognizes both:

- wide DataBank exports, with one column per indicator; and
- long exports, with one indicator/value per row.

It creates timestamped reports under reports/sources/world-bank-icp/:

- observations_long.csv: all extracted rows, including missing values;
- latest_available_by_country_indicator.csv: latest non-missing value independently by country, classification and indicator;
- coverage_by_country_indicator.csv: first/latest available year, count and observed years.

CSV input decoding detects UTF-8/UTF-8 BOM and UTF-16 BOM, then uses strict Windows-1252 and Latin-1 fallbacks for legacy DataBank exports; the detected encoding is recorded in the sheet/source label. The DataBank `Series_-_Metadata.csv` member repeats the complete observation table before appending indicator definitions; the inspector treats it as a metadata artifact and does not ingest its repeated observations. Empty/footer rows (including `Data from database` and `Last Updated`) are excluded because they lack a country and reference year. Structural DataBank fields such as Time Code are excluded from wide-format indicator detection. Source-release identity is derived from the acquisition directory (`icp_YYYY_cycle` or `icp_2021_saved_report`) and is part of every latest-value and coverage key, preventing different ICP vintages from being collapsed. CSV report fields, including numeric observations, are serialized as text; downstream numeric comparisons should parse the value field explicitly. The latest-value rule is observation-based, not a common global cutoff. Missing observations remain visible. No zeros, carry-forward values, interpolation, extrapolation or imputation are created by this inspector. Published imputed observations must be identified from the source's own status metadata and must not be confused with missing observations.

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
uv run python -m pytest -v tests/test_world_bank_icp_databank.py tests/test_world_bank_icp_exports.py tests/test_world_bank_icp_snapshot.py
uv run python -m compileall -q tools
```

Owner-run terminal output is the validation authority.
