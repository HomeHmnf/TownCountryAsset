# World Bank ICP 2021 release acquisition

## Purpose

Acquire and retain the World Bank International Comparison Program (ICP) 2021-cycle public dataset as source evidence for the Zimbabwe field-18 PPP investigation. The May 2024 release includes the 2021 reference year, revised 2017 results, annual PPPs for 2017–2021, and extrapolated GDP PPPs for 2022–2023. The original 2017 cycle remains a separate publication and must not be confused with the revised 2017 values in the 2021 cycle.

Official entry points:

- ICP data page: https://www.worldbank.org/en/programs/icp/data
- Data Catalog record: https://datacatalog.worldbank.org/search/dataset/0066092/international-comparison-program-2021
- Public Data Catalog API: https://ddh-openapi.worldbank.org/docs/index.html
- Dataset identifier: `0066092`

## Acquisition

Run:

```fish
uv run python -m tools.acquire_world_bank_icp_snapshot
```

The tool retrieves dataset metadata and the dataset's complete resource listing through the World Bank Data Catalog API, then downloads every listed resource. It preserves response bytes, request/final URLs, HTTP status, content type, byte count and SHA-256 in a timestamped manifest. It refuses partial resource listings and existing output paths. Network retries are bounded and configurable:

```fish
uv run python -m tools.acquire_world_bank_icp_snapshot --timeout 120 --retries 5 --retry-delay 2
```

Raw files are written under `raw_data/sources/world_bank_icp/icp_2021_cycle/`, manifests under `data_manifests/sources/world_bank_icp/icp_2021_cycle/`, and acquisition reports under `reports/sources/world-bank-icp/`.

## Scope and limitations

- This is a byte-preserving acquisition of the Data Catalog's published ICP 2021-cycle dataset, not a claim that the API resource files are a particular original-vintage workbook until their metadata and contents are inspected.
- The capture includes the revised 2017 results supplied in the 2021 cycle. It does not substitute those for the original 2017 cycle.
- The public ICP embedded tables display rounded values. Use downloaded underlying resources for precision analysis; retain embedded tables only as independent presentation cross-checks.
- The acquisition does not classify Zimbabwe as participating or imputed. That status must be read from the country-level dataset records and documented separately.
- The acquisition does not parse or transform data, assess PPP-factor units, reconcile WDI/WEO, approve a source, alter source selection, apply retention, or write either SQLite database.
- The World Bank states that ICP results are statistical estimates subject to sampling, measurement and classification error, and are not national official statistics.

## Diagnostic follow-through

After acquisition, inspect the manifest and raw resource formats. The next assessment should isolate Zimbabwe's GDP PPP conversion factor, GDP in local currency, PPP GDP in international dollars, price-level index, and any participation/imputation or currency-unit metadata for:
1. original ICP 2017;
2. revised ICP 2017 as published in the ICP 2021 cycle;
3. ICP 2021;
4. annual PPP series 2017–2021.

Do not infer a currency-unit bridge from matching numeric values alone. Preserve the source's own unit labels, benchmark identifiers and status flags. Compare the original and revised 2017 records explicitly before interpreting the WDI 2015–2018 arithmetic ratio or 2017 spike.

## Validation

```fish
uv run python -m pytest -v tests/test_world_bank_icp_snapshot.py
uv run python -m compileall -q tools
```

Owner-run tests are the validation authority. The acquisition report records that no Project DB, Game DB, approval, retention or source-selection state is changed.
