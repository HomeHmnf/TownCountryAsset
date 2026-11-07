# Data-store separation Stage 4B — WDI immutable API snapshot

**Implementation status:** code, tests, source/dataset registry definitions and documentation committed; owner-run live capture and local validation pending  
**Branch:** work/compiler-hardening  
**Scope:** freeze the World Bank WDI responses used by the IMF WEO comparison for 2015–2025.

## 1. Why this step exists

Stage 4 compared a fixed IMF October 2026 CSV with live WDI API responses. That comparison is useful diagnostic evidence, but a rolling API response can change between runs. This step creates a reproducible response bundle without treating the API capture as a provider-declared WDI release vintage.

The work does not change source selection, approve data, validate semantic equivalence, promote a release, or write to the Game DB.

## 2. Implementation

New acquisition tool:

- tools/acquire_world_bank_wdi_snapshot.py
- tests/test_world_bank_wdi_snapshot.py

The tool captures:
- WDI source ID 2 metadata;
- every page of the country/region catalogue;
- metadata for five primary comparison indicators;
- metadata and annual observation pages for the five primary indicators plus SL.UEM.TOTL.NE.ZS as a field-21 national-estimate diagnostic.

Each raw JSON response is written byte-for-byte to a new timestamped local-only directory. The manifest stores each response path, request URL/parameters, final URL, status, response headers, retrieval timestamp, content type, byte count, SHA-256 and pagination/row counts. Capture rejects invalid envelopes, unexpected WDI indicator source identity and inconsistent pagination. Existing paths are never overwritten.

The loader rechecks every artifact's byte count and SHA-256, verifies the required indicator and country metadata, and rejects incomplete page numbering. It does not infer actual/estimate/projection status. Observation status is preserved; only explicit WDI status F is labelled forecast in the comparison.

The comparison utility now accepts --wdi-snapshot-manifest. It uses the snapshot's metadata and observations instead of issuing live WDI requests, verifies the period matches the requested comparison period, and records the manifest fingerprint, snapshot ID and retrieval timestamp in its report. Live mode remains available but explicitly identifies its rolling retrieval model.

## 3. Registry changes

config/data_sources.json:
- adds WDI macroeconomic and labour domain/field coverage;
- records the official dataset terms URL and attribution guidance;
- keeps license_status as unclear_or_unverified because third-party indicator exceptions remain to be checked;
- distinguishes timestamped API snapshots from provider release discovery.

config/project_datasets.json:
- adds dataset world_bank_wdi / wdi_selected_macro_indicators;
- adds stream rolling_api_snapshot;
- declares five primary indicators and one diagnostic indicator;
- bounds the current comparison snapshot to 2015–2025;
- defines full-page, metadata and fingerprint requirements.

The registry addition records acquisition scope only. It does not assign WDI as a primary or fallback source for fields 15, 16, 18, 20 or 21. IMF WEO source priorities remain unchanged.

## 4. Owner-run commands

Capture the snapshot:

    uv run python -m tools.acquire_world_bank_wdi_snapshot --start-year 2015 --end-year 2025

Audit the manifest:

    uv run python -m tools.audit_acquisition_manifests --manifest-dir data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators --format json

Synchronize source and dataset definitions:

    uv run python -m tools.sync_project_source_catalogue
    uv run python -m tools.sync_project_dataset_catalogue

After the audit reports status ok, register provenance in the Project DB:

    uv run python -m tools.register_project_acquisitions --manifest-dir data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators

Select the manifest and rerun the frozen comparison:

    set manifest (find data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators -type f -name '*.json' | sort | tail -n 1)
    uv run python -m tools.compare_imf_weo_wdi --start-year 2015 --end-year 2025 --wdi-snapshot-manifest $manifest

Run the focused tests:

    uv run --extra dev python -m pytest -v tests/test_world_bank_wdi_snapshot.py tests/test_world_bank_wdi_assessment.py tests/test_imf_weo_wdi_comparison.py tests/test_project_dataset_catalogue.py

The owner must provide terminal output before the work can be marked locally validated. In particular, inspect Project DB integrity and foreign-key checks after registration. Do not stage raw_data response bytes or either SQLite database.

## 5. Licensing and limitations

The World Bank dataset terms default to CC BY 4.0 for World Bank-produced datasets but explicitly allow indicator-level third-party exceptions. The source registry therefore remains unclear_or_unverified pending series-by-series review. Keep raw responses local-only; do not redistribute them or claim blanket license coverage.

The capture is a rolling API snapshot with a precise retrieval timestamp, request parameters and raw response hashes. It is not a provider vintage, and it does not make the WDI data vintage-aligned with the October 2026 IMF release. The comparison remains diagnostic, and actual/estimate status remains unknown unless explicit observation metadata supports a narrower classification.

See [WDI snapshot acquisition](../data-sources/world-bank-wdi-snapshot-acquisition.md) and [Stage 4 IMF WEO semantic assessment](data-store-separation-stage-4-imf-weo-semantic-assessment.md).
