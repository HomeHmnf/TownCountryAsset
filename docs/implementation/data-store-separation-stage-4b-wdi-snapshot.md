# Data-store separation Stage 4B — WDI immutable API snapshot

**Implementation status:** implemented, owner-run capture/audit/registration/comparison completed and locally validated  
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


## 6. Owner-run capture and validation record (2026-11-07)

Snapshot acquisition completed:

- Snapshot ID: `api_snapshot_20261107T133112433299Z`
- Retrieval timestamp: `2026-11-07T13:31:36.501505+00:00`
- Manifest: `data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators/api_snapshot_20261107T133112433299Z.json`
- Manifest SHA-256: `58075c28803955ca630db99da59b62084947141fa9b110a2fb3198aa1b0619be`
- Manifest size: 33,182 bytes
- Raw responses: 14 artifacts, 4,226,626 bytes
- Country/region catalogue: 296 records
- Six indicators captured; each has one observation page and 2,926 observation rows for 2015–2025.

Manifest audit: one manifest, 14 artifacts, one valid manifest, zero errors; every declared byte count and SHA-256 matched. Audit was read-only.

Registry and provenance:
- Source catalogue: 31 sources and 92 URLs synchronized; no source changes were required.
- Dataset catalogue: 6 datasets and 4 streams synchronized.
- Project DB acquisition ID 6 registered with 14 artifacts, status `acquired`, integrity `verified`.
- Project DB `PRAGMA integrity_check`: `ok`; `PRAGMA foreign_key_check`: no violations.
- No Game DB write, source-selection change, approval or retention operation occurred.

Frozen comparison:
- Report: `reports/sources/imf-wdi-comparison/20261107T144614Z/`
- Period: 2015–2025; 13,310 rows = 242 identities × 5 fields × 11 years.
- Coverage: both sources 9,324; IMF only 450; WDI only 1,354; neither 2,182.
- Compared with the 2026-11-05 live API matrix: no key, WDI value, IMF value, coverage, IMF status-hint or IMF reporting-period-classification changes.
- WDI `obs_status` is blank in all 13,310 candidate rows. The 10,678 rows with WDI observations remain `not_classified_by_this_comparison`; 2,632 rows without a WDI observation are `missing`. Blank status does not establish actual data.

Owner-run local validation: 19 focused tests passed; `compileall` completed without errors. The snapshot capture, audit, registry sync, provenance registration, database integrity checks and comparison all completed successfully.

This confirms reproducibility of the captured values and coverage relative to the earlier live run. It does not establish provider vintage alignment, IMF–WDI semantic equivalence, or actual/estimate/projection status. The snapshot remains a timestamped rolling API capture, not a provider-declared vintage.
