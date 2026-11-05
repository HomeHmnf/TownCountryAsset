# ICASEES national accounts — documentation index

This folder separates the ICASEES source record into acquisition/provenance, workbook structure and GDP comparability. The parent page [ICASEES Central African Republic national accounts](../icasees-central-african-republic-national-accounts.md) remains the entry point from the data-source catalogue.

## Documents

- [Source and acquisition](source-and-acquisition.md) — official publication URLs, licence, local files, fingerprints and manifest.
- [Dataset and workbook structure](dataset-and-workbook-structure.md) — workbook sheets, series layout, indicator rows, formulas and parsing constraints.
- [GDP scale and IMF WEO reconciliation](gdp-scale-and-weo-reconciliation.md) — definitive publication evidence, scale interpretation, exact WEO comparison and 2019 break.

## Shared tooling

- [Shared PDF text extraction](../../implementation/pdf-text-extraction.md) — common handling of PDF source snapshots; ICASEES uses this service rather than a local extractor.

## Separation of concerns

- Acquisition establishes which bytes were obtained and their provenance.
- Dataset structure describes how the provider workbook stores observations.
- Reconciliation interprets units and comparability using external corroboration.
- The assessment tool and its validation history belong in the [implementation record](../../implementation/README.md) and the source overview.
