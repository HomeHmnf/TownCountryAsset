# World Bank WDI immutable API snapshot acquisition

**Status:** acquisition, manifest audit, Project DB provenance registration and frozen comparison completed and owner-validated  
**Scope:** WDI source ID 2, annual observations for 2015–2025  
**Purpose:** freeze the exact WDI responses used in the IMF WEO comparison so later analysis can be reproduced.

## 1. Decision boundary

This workflow acquires and fingerprints source responses. It does not establish semantic comparability, classify every observation as actual/estimate/projection, approve a release, change source-selection policy, or write to the Game DB.

The WDI series are registered as a separate diagnostic dataset and rolling API snapshot stream:

- Source: world_bank_wdi
- Dataset: wdi_selected_macro_indicators
- Stream: rolling_api_snapshot

This registration is not a fallback or primary-source assignment for fields 15, 16, 18, 20 or 21. Existing IMF WEO priorities remain unchanged.

## 2. Captured indicator scope

| Role | WP1.5 field | WDI indicator | Meaning |
|---|---:|---|---|
| Primary comparison | 15 | NY.GDP.MKTP.CD | GDP, current US$ |
| Primary comparison | 16 | NY.GDP.PCAP.CD | GDP per capita, current US$ |
| Primary comparison | 18 | NY.GDP.MKTP.PP.CD | GDP, PPP, current international $ |
| Primary comparison | 20 | FP.CPI.TOTL.ZG | Inflation, consumer prices, annual % |
| Primary comparison | 21 | SL.UEM.TOTL.ZS | Unemployment, total, ILO modelled estimate |
| Diagnostic only | 21 | SL.UEM.TOTL.NE.ZS | Unemployment, total, national estimate |

The national-estimate series is retained as diagnostic context only. It is not a substitute for the ILO-modelled series and is not used as the primary field-21 comparison.

The capture period is deliberately bounded to 2015–2025 to reproduce the existing IMF–WDI comparison. Expanding the period or adding indicators requires a new snapshot scope, not mutation of an existing snapshot.

## 3. Capture contents and integrity

Run from the repository root:

    uv run python -m tools.acquire_world_bank_wdi_snapshot --start-year 2015 --end-year 2025

If the network requires the configured proxy:

    proxychains uv run python -m tools.acquire_world_bank_wdi_snapshot --start-year 2015 --end-year 2025

The tool captures and stores each raw JSON response byte-for-byte:

- WDI source metadata (/sources/2);
- all pages of the World Bank country/region catalogue;
- metadata responses for all six indicators;
- every paginated observation response for all configured primary, diagnostic and supporting indicators, using the same annual date range and per_page=20000 request pattern.

For each response, the manifest records its request URL and parameters, final URL, HTTP status, response headers, retrieval timestamp, content type, byte count and SHA-256. It also records pagination counts, row counts, source identity, period and indicator summaries. A response is never rewritten or normalized before its raw bytes are fingerprinted.

The capture aborts on malformed response envelopes, non-200/empty responses, indicator metadata that does not identify WDI source ID 2, or changing/inconsistent pagination. Partial raw files from a failed attempt have no complete manifest and are not eligible for registration. A new timestamp is used for each attempt; existing snapshot paths are never overwritten.

Storage locations:

- Raw responses: raw_data/sources/world_bank_wdi/wdi_selected_macro_indicators/<snapshot_id>/
- Manifest: data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators/<snapshot_id>.json
- Acquisition report: reports/sources/world-bank-wdi-snapshot/<snapshot_id>/

Raw provider responses remain local-only. Track the manifest and human-readable report, but do not stage raw response files or SQLite databases.

## 4. Register the source, dataset and acquisition provenance

Synchronize the reviewed source and dataset definitions:

    uv run python -m tools.sync_project_source_catalogue
    uv run python -m tools.sync_project_dataset_catalogue

Audit the new manifest and every referenced response:

    uv run python -m tools.audit_acquisition_manifests --manifest-dir data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators --format json

Only if the audit reports status: ok, register the event in the Project DB:

    uv run python -m tools.register_project_acquisitions --manifest-dir data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators

The generic registrar uses the manifest path as the immutable event key and stores the complete manifest payload and per-response artifact metadata. Re-running registration with unchanged evidence is idempotent. The acquisition remains acquired with integrity_status=verified; it is not semantically validated, approved or retained.

The source/dataset synchronization and provenance registration write only to data/project/project_data.sqlite. They do not write to the canonical Game DB.

## 5. Re-run the comparison against the frozen snapshot

Select the manifest created by the capture command:

    set manifest (find data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators -type f -name '*.json' | sort | tail -n 1)

Run the comparison with the same year range:

    uv run python -m tools.compare_imf_weo_wdi --start-year 2015 --end-year 2025 --wdi-snapshot-manifest $manifest

The comparison loader verifies every response SHA-256 and byte count, checks that all required indicator and country metadata are present, and verifies complete page numbering before using the captured observations. The report records the WDI manifest path, manifest SHA-256, snapshot ID and retrieval timestamp. It retains the rectangular country × field × year candidate matrix.

A snapshot with a different year range is rejected rather than silently clipped or expanded. The existing live-API mode remains available for exploration, but must be labelled live_rolling_api_not_immutable_snapshot and must not be used as the frozen comparison evidence.

The API's obs_status is preserved in the comparison output. Only an explicit F status is labelled as forecast; other or blank statuses remain unclassified. Do not infer that a blank status means actual.

## 6. Licensing and attribution

World Bank dataset terms state that CC BY 4.0 is the default for datasets produced by the World Bank. The same terms explicitly warn that some indicators contain third-party data with different restrictions. Accordingly:

- retain indicator-level source organization and source-note metadata;
- preserve the terms URL in the manifest;
- keep the source-level license status unclear_or_unverified until the individual indicator exceptions have been checked;
- do not redistribute raw responses or assert blanket CC BY coverage solely from the WDI dataset's default license.

References:

- [World Bank Indicators API documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392)
- [WDI API pagination and observation metadata](https://datahelpdesk.worldbank.org/knowledgebase/articles/1886674-new-features-and-enhancements-in-the-v2-api)
- [World Bank dataset terms](https://www.worldbank.org/ext/en/legal/terms-conditions/datasets)
- [World Bank data access and licensing](https://datacatalog.worldbank.org/public-licenses)

## 7. Tests and validation boundary

Automated tests:

    uv run --extra dev python -m pytest -v tests/test_world_bank_wdi_snapshot.py tests/test_world_bank_wdi_assessment.py tests/test_imf_weo_wdi_comparison.py tests/test_project_dataset_catalogue.py

The snapshot tests use mocked API responses to verify complete bundle capture, metadata retention, raw-byte integrity, refusal to overwrite and rejection of a non-WDI indicator. They do not replace an owner-run live acquisition or provider response validation.

After the owner-run capture, retain the terminal output for:

1. snapshot report and manifest path;
2. manifest audit status and artifact count;
3. source/dataset synchronization counts;
4. Project DB registration result;
5. Project DB integrity and foreign-key checks;
6. comparison report directory and matrix summary.

No source-selection decision should be made until the immutable comparison and the remaining field-definition, identity, period and licensing gates have been reviewed.


## 8. Completed owner-run acquisition record (2026-11-07)

The 2015–2025 snapshot was captured successfully:

| Property | Result |
|---|---|
| Snapshot ID | `api_snapshot_20261107T133112433299Z` |
| Retrieved at | `2026-11-07T13:31:36.501505+00:00` |
| Manifest | `data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators/api_snapshot_20261107T133112433299Z.json` |
| Manifest SHA-256 | `58075c28803955ca630db99da59b62084947141fa9b110a2fb3198aa1b0619be` |
| Manifest bytes | 33,182 |
| Raw response artifacts | 14 |
| Raw response bytes | 4,226,626 |
| Country/region catalogue records | 296 |
| Indicator observations | 2,926 rows per indicator, one page each |

All six requested indicators were captured: the five primary comparisons and the field-21 national-estimate diagnostic. Each indicator metadata response reported WDI API `lastupdated=2026-10-08`; this is indicator metadata, not the snapshot retrieval timestamp or a provider vintage. The source-level `lastupdated` field was null.

The read-only manifest audit examined one manifest and all 14 artifacts. Result: `status=ok`, one valid manifest, zero errors, and all byte counts/SHA-256 hashes matched.

The source catalogue sync reported 31 sources and 92 URLs, with no source changes. Dataset sync reported six datasets and four acquisition streams. Project DB acquisition ID 6 was registered with 14 artifacts, status `acquired`, and integrity `verified`. Project DB integrity check returned `ok`; foreign-key check returned no violations. No Game DB write, approval, retention operation or source-selection change occurred.

The frozen comparison report is `reports/sources/imf-wdi-comparison/20261107T144614Z/`. It contains 13,310 candidate rows (242 identities × five fields × 11 years), with coverage counts: both sources 9,324; IMF only 450; WDI only 1,354; neither 2,182.

Comparison with the 2026-11-05 live API run found identical row keys and zero changes to WDI values, IMF values, coverage states, IMF status hints or IMF reporting-period classifications. This confirms value/coverage stability between those two runs; it does not prove semantic comparability or vintage alignment.

The snapshot-backed matrix contains a blank WDI `obs_status` for all 13,310 rows. Of these, 10,678 rows contain WDI observations and remain `not_classified_by_this_comparison`; 2,632 rows have no WDI observation and are `missing`. No WDI observation is thereby established as actual, estimate or projection.

Owner-run focused validation passed 19 tests; `compileall` completed without errors. The live capture, audit, synchronization, registration, database integrity checks and frozen comparison all completed successfully.


## HTTP reliability and retry policy

The capture command uses a 120-second per-request timeout and retries transient URL/transport failures and HTTP 408, 425, 429 and 5xx responses up to five times, with exponential backoff starting at two seconds. Non-transient client errors fail immediately. Override with `--timeout`, `--retries` and `--retry-delay` when diagnosing network conditions. A failed attempt can leave an incomplete, unmanifested timestamped raw directory; do not register it. A subsequent attempt receives a new snapshot ID and never overwrites that directory.

For a constrained network, run the command as the normal repository owner. Root privileges are not required. A proxy can be used if it is already configured in the environment, but the tool does not configure or bypass TLS verification for proxies.

## 9. Stage 4D supporting macro-decomposition indicators

The snapshot capture profile now includes six supporting WDI indicators in addition to the original five primary comparison indicators and the field-21 national-estimate diagnostic:

| Supporting indicator | Diagnostic purpose |
|---|---|
| `NY.GDP.MKTP.CN` | GDP at current prices in local currency |
| `PA.NUS.FCRF` | Official exchange rate, LCU per US$ |
| `PA.NUS.ATLS` | DEC alternative conversion factor, LCU per US$ |
| `PA.NUS.PPP` | GDP PPP conversion factor, LCU per international dollar |
| `SP.POP.TOTL` | Total population, for a GDP-per-capita arithmetic check |
| `FP.CPI.TOTL` | Consumer price index, for an annual index-growth diagnostic |

The World Bank metadata defines `PA.NUS.ATLS` as the DEC alternative conversion factor used in the Atlas method and notes that it may differ from the official rate where multiple/dual exchange rates or non-calendar national-account periods apply. Its presence does **not** prove that the current-USD GDP indicator uses that factor. The assessment reports both official-rate and alternative-factor arithmetic without assuming either is the provider's GDP conversion method. See the [WDI metadata for PA.NUS.ATLS](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/PA.NUS.ATLS).

The read-only assessment `tools/assess_wdi_macro_decomposition.py` calculates, where all inputs exist:

- local-currency GDP divided by the official exchange rate;
- local-currency GDP divided by the DEC alternative conversion factor (diagnostic only);
- local-currency GDP divided by the GDP PPP conversion factor;
- current-USD GDP divided by total population;
- year-on-year growth in the annual CPI index.

It records the source inputs, indicator metadata, country special notes, raw observation-status values and IMF WEO observations alongside the calculations. Missing or zero denominators produce null derived values. It does not infer actual/estimate/projection status, identity validity, source methodology or canonical correctness.

For the CPI calculation, the capture must include one lead-in year. Acquire 2014–2025 and assess 2015–2025:

    uv run python -m tools.acquire_world_bank_wdi_snapshot --start-year 2014 --end-year 2025
    set manifest (find data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators -type f -name '*.json' | sort | tail -n 1)
    uv run python -m tools.assess_wdi_macro_decomposition --snapshot-manifest $manifest --start-year 2015 --end-year 2025

Audit the manifest before registering its acquisition. Synchronize the updated dataset metadata, then register the manifest in the Project DB using the existing commands in section 4. The new capture is a distinct rolling-API acquisition; it does not overwrite or replace the already validated 2026-11-07 six-indicator snapshot or the frozen IMF–WDI comparison.

The six supporting series are captured with their raw bytes and indicator metadata. They are not part of the five-field candidate comparison and do not change source-selection policy. The decomposition is diagnostic only: it cannot resolve provider-vintage alignment, identity governance, IMF actual/estimate/projection status, or country-specific national-accounts methodology by itself.
