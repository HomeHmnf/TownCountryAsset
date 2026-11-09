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

## Acquisition boundary

The Data Catalog API's resource records include website and DataBank navigation references as well as machine-readable resources. Only actual downloadable file resources may be fetched from a `/download` endpoint. A website or DataBank reference is not a file; attempting to download it as one produces HTTP 400.

DataBank supports Excel, CSV, tab-delimited text and metadata exports. DataBank exports must retain the report URL, selected dimensions, export format, retrieval timestamp and file hash. Do not silently substitute a preview page or a limited saved report for a full-country/full-indicator export.

The existing `tools.acquire_world_bank_icp_snapshot` captures the ICP 2021 Data Catalog metadata/resource listing. Its prior all-resources-as-files behaviour is not a valid acquisition contract. Until the DataBank export request is reproducibly automated and tested, manually exported full DataBank tables may be placed under:

`raw_data/sources/world_bank_icp/<cycle>/`

Preserve each export as an immutable file and record its report URL, selected dimensions, release/vintage, retrieval timestamp, byte count and SHA-256 in its manifest. Do not overwrite previous captures.

## Inspection

Run:

```fish
uv run python -m tools.assess_world_bank_icp_exports
```

The inspector scans CSV and XLSX files under `raw_data/sources/world_bank_icp/` and recognizes both:

- wide DataBank exports, with one column per indicator; and
- long exports, with one indicator/value per row.

It creates timestamped reports under `reports/sources/world-bank-icp/`:

- `observations_long.csv`: all extracted rows, including missing values;
- `latest_available_by_country_indicator.csv`: latest non-missing value independently by country, classification and indicator;
- `coverage_by_country_indicator.csv`: first/latest available year, count and observed years.

CSV report fields, including numeric observations, are serialized as text; downstream numeric comparisons should parse the value field explicitly. Structural DataBank fields such as `Time Code` are excluded from wide-format indicator detection. The latest-value rule is observation-based, not a common global cutoff. Missing observations remain visible. No zeros, carry-forward values, interpolation, extrapolation or imputation are created by this inspector. Published imputed observations must be identified from the source's own status metadata and must not be confused with missing observations.

## Interpretation requirements

Keep separate:

- original benchmark versus revised benchmark;
- benchmark versus annual interpolation versus extrapolation;
- participating versus imputed economy;
- PPP conversion factors versus PPP-based expenditure values and price-level indices;
- each indicator's unit and classification;
- source-reported missingness versus a country/indicator absent from an export.

The ICP 2021 publication provides 2021 benchmark results, revised 2017, annual PPP series 2017–2021 and extrapolated GDP PPPs for 2022–2023. WDI's later annual PPP series are a separate extrapolated statistical series, not new ICP benchmark cycles. Do not label WDI years after 2023 as new ICP benchmark observations.

No source-selection change, approval, Project DB write, Game DB write or canonical data promotion is performed by inspection.

## Validation

```fish
uv run python -m pytest -v tests/test_world_bank_icp_exports.py
uv run python -m compileall -q tools
```

Owner-run terminal output is the validation authority.
