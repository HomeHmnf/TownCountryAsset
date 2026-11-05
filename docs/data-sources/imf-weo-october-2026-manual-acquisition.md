# IMF WEO October 2026 manual acquisition record

**Status:** manually acquired and registered in the Project DB (acquisition ID `5`, byte integrity verified); repository-tracked files and recorded checksums reconciled; read-only coverage/identity assessment completed; semantic validation, WDI comparison, approval, application and promotion remain pending  
**Provider:** International Monetary Fund (IMF), Research Department  
**Dataset:** World Economic Outlook (WEO), October 2026 vintage  
**Project source ID:** `imf_weo`  
**Manual download date:** 2026-11-02 (date precision only; no exact acquisition time recorded)  
**Local directory:** `raw_data/sources/imf_weo/october_2026/`

## Official source and download method

The files were obtained manually from the official IMF Data Portal WEO dataset page:

- WEO dataset landing page and download interface: https://data.imf.org/datasets/WEO
- IMF WEO publication page, October 2026: https://www.imf.org/en/Publications/WEO/Issues/2026/10/13/world-economic-outlook-october-2026
- WEO Database Appendix is listed as a vintage-specific downloadable PDF on the WEO dataset page.
- WEO Database Transition Guide: https://data.imf.org/-/media/iData/External-Storage/Documents/2C2B2F3E671A4B11ABE756E2441FD6F0/en/WEO-Database-Transition-Guide.pdf
- IMF Data API documentation: https://data.imf.org/en/Resource-Pages/IMF-API

The project operator used the WEO dataset page's download/export interface and saved the returned dataset file and the October 2026 Database Appendix. This is a **manual portal export**, not an automated bulk-download process. The precise click sequence, selected portal controls, and original download response headers were not captured; do not infer them retrospectively.

The October 2026 WEO dataset page describes the dataset as annual and covering national accounts, inflation, unemployment, balance of payments, fiscal indicators, trade and other WEO series for countries and country groups. The IMF transition guide distinguishes static tab-delimited CSV/Excel bulk downloads from dynamic SDMX/API access. The IMF API documentation states that SDMX 2.1 and SDMX 3.0 APIs are available.

## Acquired files and integrity

The following files were present in the local snapshot directory and SHA-256 checksums were calculated locally on 2026-11-02.

| Local filename | Format recorded | Bytes | SHA-256 |
|---|---|---:|---|
| `dataset_2026-11-02T07_37_00.482492506Z_DEFAULT_INTEGRATION_IMF.RES_WEO_9.0.0.csv` | CSV portal export | 26,692,032 | `a19b2bd65b050a91d593cb6bcfc77a303e6359e058f03c3c92cf5ad849cda74d` |
| `October 2026 WEO Database Appendix.pdf` | PDF documentation | 985,701 | `cd4e2829d7e621d43134728bfc128547f776e909e08ef1d38b837e2d39e5ae2a` |

The CSV filename embeds the portal export timestamp `2026-11-02T07:37:00.482492506Z` and dataset identifier/version string `IMF.RES_WEO_9.0.0`. These filename tokens are recorded as observed; the timestamp is the export-generation timestamp, not the WEO publication date or an independently verified dataset acquisition timestamp.

The delivered data file is CSV. Its extension and filename alone do **not** establish that its byte-level serialization is SDMX 3.0-CSV, nor do they establish whether it was generated from an SDMX 3.0 API response or the portal's static export path. Record its observed serialization as CSV until its header, columns, dimensions and metadata have been inspected. Do not label this file SDMX-ML or SDMX-JSON. The IMF separately documents SDMX 2.1 and SDMX 3.0 API availability.

Stage 0 repository inventory confirmed that both raw files are Git-tracked and that the committed Git blobs match the working-tree files. The recorded byte counts and SHA-256 values above were also reconciled by the read-only IMF assessor. The original files are retained unchanged. This document is the manual provenance record; it is not represented as a formal provider manifest.

## Read-only coverage and identity assessment (2026-11-05)

The owner ran:

```fish
uv run --extra dev python -m pytest -v tests/test_imf_weo_assessment.py
uv run python -m tools.assess_imf_weo
```

Owner-reported result: **4 assessment tests passed**. The generated report covered five indicators over 1980–2031:

| Field | Indicator | Concept |
|---:|---|---|
| 15 | NGDPD | GDP |
| 16 | NGDPDPC | GDP per capita |
| 18 | PPPGDP | GDP (PPP) |
| 20 | PCPIPCH | Inflation |
| 21 | LUR | Unemployment |

This assessment is coverage and candidate-identity analysis, not semantic validation. Its output explicitly recorded:

- WDI comparison: `not_assessed`;
- immutable snapshot acquisition by the assessor: `false` (the assessor is read-only);
- canonical database writes: `false`;
- release promotion: `false`.

The assessor preserves latest-actual metadata and reporting-year months, excludes non-ISO aggregate prefixes from country identity matching, and records unresolved limitations: PPPGDP has no latest-actual metadata; LUR has a blank unit; registry code matches do not approve ISO assignments; fiscal-year reporting periods are not coerced to calendar years; and missing annual values remain missing. These are review gates, not silently normalized values.

## Intended comparison scope

The existing source registry assigns IMF WEO as the priority source for WP1.5 fields 15, 16, 18, 20 and 21. The WEO candidate must be compared with the World Bank WDI candidates at indicator-definition level, not just by label. Preserve country/area versus country-group distinctions, annual reference year, unit/currency/price basis, methodology, vintage and latest-actual-year metadata.

The IMF WEO CSV full-dataset download includes a `Latest Actual Annual Data` metadata field according to the official WEO FAQ. For country observations, years after that latest actual year are IMF staff estimates; a value of zero indicates the entire series is estimated. Actual values can still be revised in later vintages. Country-group data do not have the same per-country latest-actual-year metadata, so their status must not be inferred using the country rule.

## Licensing and use restrictions

The source registry continues to mark the IMF WEO license status as `unclear_or_unverified`. This manual acquisition record does not grant reuse or redistribution rights and does not resolve whether the intended use is permitted. Review the IMF copyright and terms page and any WEO-specific notices before publishing or redistributing derived or source data:

- IMF copyright and terms: https://www.imf.org/en/about/copyright-and-terms
- WEO dataset page: https://data.imf.org/datasets/WEO

Do not implement automated bulk downloading until the applicable IMF permission and access requirements have been verified. Do not mark the source as open or unrestricted based solely on public download availability.

## Governance boundary and next actions

The manual acquisition and coverage assessment:

- do not change `config/source_selection.json`;
- do not add WDI fallback or change the five IMF priority assignments;
- do not approve semantic validity or mark a release as validated/retained;
- do not normalize or import observations;
- do not write to the canonical Game DB;
- do not promote a release to `latest_validated` or `latest_applied`.

The Project DB manual-bundle registration is implemented separately in [Stage 3C](../implementation/data-store-separation-stage-3c-imf-manual-acquisition.md). Owner-run registration completed on 2026-11-05 as acquisition ID `5`, event key `manual:october_2026:2026-11-02`, with two artifact rows (`dataset` CSV and `supporting_document` PDF). The stored date is `2026-11-02` at day precision; the command verified both artifact byte counts and SHA-256 values. The owner also confirmed SQLite integrity `ok` and no foreign-key violations. Registration does not create a formal manifest or claim semantic validation; the event remains `acquired`, not `validated` or `retained`, and no Game DB write or release promotion occurred.

Next, complete indicator-definition and unit verification, explicit country-code/alias review, and a normalized WDI country-year comparison. Then build the country × field completeness and candidate matrix. Only validated, approved observations may proceed through the existing guarded application workflow.

## Official references

- IMF Data Portal, World Economic Outlook: https://data.imf.org/datasets/WEO
- IMF WEO October 2026 publication: https://www.imf.org/en/Publications/WEO/Issues/2026/10/13/world-economic-outlook-october-2026
- IMF WEO Frequently Asked Questions: https://data.imf.org/en/Datasets/WEO/Frequently-Asked-Questions
- IMF Data API documentation (SDMX 2.1 and SDMX 3.0): https://data.imf.org/en/Resource-Pages/IMF-API
- IMF WEO Database Transition Guide: https://data.imf.org/-/media/iData/External-Storage/Documents/2C2B2F3E671A4B11ABE756E2441FD6F0/en/WEO-Database-Transition-Guide.pdf


## Comparison and semantic assessment update (2026-11-05)

The comparison and targeted discrepancy investigation are now complete as read-only diagnostics. The owner ran the comparison test group (15 tests passed) and generated the 2015–2025 candidate matrix and matched-pair output. The targeted investigation selected 15 country/field groups and 165 observations from that comparison; it did not fetch original provider records or change any database/policy state.

The consolidated findings and remaining semantic gates are recorded in [Stage 4 — IMF WEO semantic assessment](../implementation/data-store-separation-stage-4-imf-weo-semantic-assessment.md) and [the IMF WEO/WDI comparison record](imf-weo-wdi-comparison.md). The assessment is not an approval: all five existing IMF WEO priority assignments remain unchanged; the WDI comparison remains live-vintage and diagnostic; no semantic validation, approval, retention, release promotion or Game DB write has occurred.
