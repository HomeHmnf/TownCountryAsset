# IMF WEO October 2026 manual acquisition record

**Status:** manually downloaded local source snapshot; not yet parsed, semantically validated, release-approved, applied, or promoted  
**Provider:** International Monetary Fund (IMF), Research Department  
**Dataset:** World Economic Outlook (WEO), October 2026 vintage  
**Project source ID:** `imf_weo`  
**Manual download date:** 2026-11-02  
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

The CSV filename embeds the portal export timestamp `2026-11-02T07:37:00.482492506Z` and dataset identifier/version string `IMF.RES_WEO_9.0.0`. These filename tokens are recorded as observed; the timestamp is the export-generation timestamp, not the WEO publication date or an independently verified dataset release timestamp.

The delivered data file is CSV. Its extension and filename alone do **not** establish that its byte-level serialization is SDMX 3.0-CSV, nor do they establish whether it was generated from an SDMX 3.0 API response or the portal's static export path. Record its observed serialization as CSV until its header, columns, dimensions and metadata have been inspected. Do not label this file SDMX-ML or SDMX-JSON. The IMF separately documents SDMX 2.1 and SDMX 3.0 API availability.

Raw files remain local and untracked under `raw_data/`. This document records their provenance and checksums; it does not replace a formal immutable acquisition manifest.

## Intended comparison scope

The existing source registry assigns IMF WEO as the priority source for WP1.5 fields:

| Field | Concept |
|---:|---|
| 15 | GDP |
| 16 | GDP per capita |
| 18 | GDP (PPP) |
| 20 | Inflation |
| 21 | Unemployment |

The WEO candidate must be compared with the World Bank WDI candidates at indicator-definition level, not just by label. Preserve country/area versus country-group distinctions, annual reference year, unit/currency/price basis, methodology, vintage and latest-actual-year metadata.

The IMF WEO CSV full-dataset download includes a `Latest Actual Annual Data` metadata field according to the official WEO FAQ. For country observations, years after that latest actual year are IMF staff estimates; a value of zero indicates the entire series is estimated. Actual values can still be revised in later vintages. Country-group data do not have the same per-country latest-actual-year metadata, so their status must not be inferred using the country rule.

## Licensing and use restrictions

The source registry continues to mark the IMF WEO license status as `unclear_or_unverified`. This manual acquisition record does not grant reuse or redistribution rights and does not resolve whether the intended use is permitted. Review the IMF copyright and terms page and any WEO-specific notices before publishing or redistributing derived or source data:

- IMF copyright and terms: https://www.imf.org/en/about/copyright-and-terms
- WEO dataset page: https://data.imf.org/datasets/WEO

Do not implement automated bulk downloading until the applicable IMF permission and access requirements have been verified. Do not mark the source as open or unrestricted based solely on public download availability.

## Governance boundary and next actions

This manual download:

- does not change `config/source_selection.json`;
- does not add WDI fallback or change the five IMF priority assignments;
- does not create or approve a source release;
- does not normalize or import observations;
- does not write to the canonical SQLite database;
- does not promote a release to `latest_validated` or `latest_applied`.

Next, inspect the CSV structure and PDF appendix, identify the exact WEO series codes and definitions for the five fields, validate country and aggregate dimensions, and build a read-only comparison against WDI. Preserve the WEO vintage and actual/estimate/projection status. Formal manifest creation, source validation, approval, database application and release promotion remain separate steps.

## Official references

- IMF Data Portal, World Economic Outlook: https://data.imf.org/datasets/WEO
- IMF WEO October 2026 publication: https://www.imf.org/en/Publications/WEO/Issues/2026/10/13/world-economic-outlook-october-2026
- IMF WEO Frequently Asked Questions: https://data.imf.org/en/Datasets/WEO/Frequently-Asked-Questions
- IMF Data API documentation (SDMX 2.1 and SDMX 3.0): https://data.imf.org/en/Resource-Pages/IMF-API
- IMF WEO Database Transition Guide: https://data.imf.org/-/media/iData/External-Storage/Documents/2C2B2F3E671A4B11ABE756E2441FD6F0/en/WEO-Database-Transition-Guide.pdf
