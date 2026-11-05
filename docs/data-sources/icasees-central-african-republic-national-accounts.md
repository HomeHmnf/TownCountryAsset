# ICASEES Central African Republic national accounts

**Status:** Acquired and assessed for workbook structure and GDP comparability; no canonical database import or source-policy change.  
**Provider:** Institut Centrafricain des Statistiques et des Études Économiques et Sociales (ICASEES).  
**Source ID:** icasees_national_accounts

This page is the entry point for the ICASEES source record. Detailed material is separated by responsibility so acquisition facts, workbook interpretation and GDP reconciliation can be maintained independently.

## ICASEES documentation

- [ICASEES documentation index](icasees/README.md)
- [Source and acquisition](icasees/source-and-acquisition.md) — provider, official publications, licence, repository paths, hashes and immutable manifest.
- [Dataset and workbook structure](icasees/dataset-and-workbook-structure.md) — sheet inventory, historical/revised blocks, formulas and parser constraints.
- [GDP scale and IMF WEO reconciliation](icasees/gdp-scale-and-weo-reconciliation.md) — definitive publication scale, workbook unit-label discrepancy, exact WEO match and 2019 break.

## Assessment tooling

- CLI: tools/assess_icasees_national_accounts.py
- Tests: tests/test_icasees_national_accounts_assessment.py
- Reports: reports/sources/icasees-national-accounts/<run-id>/

Commands from the repository root:

```fish
uv run python -m tools.assess_icasees_national_accounts manifest
uv run --with pypdf python -m tools.assess_icasees_national_accounts assess
uv run --extra dev python -m pytest -v tests/test_icasees_national_accounts_assessment.py
```

The manifest command fingerprints the already acquired files and does not download or copy them. The assessment command is read-only: it verifies fingerprints, inventories workbook structure, checks GDP arithmetic and duplicate presentations, extracts relevant PDF evidence and writes a report bundle. pypdf is supplied ephemerally for PDF text extraction; the project dependency list is unchanged.

## Boundaries and next work

- No ICASEES observations have been imported into SQLite.
- No source-selection policy, fallback, manual override, approval or release promotion has been changed.
- The ICASEES source remains a manual publication source; the generic source manager does not acquire it.
- A future adapter/import proposal must use immutable input fingerprints, validate units and identity mappings, produce review reports, and pass the shared explicit approval lifecycle before transactional application.

See [source management](source-management.md), [source selection](source-selection.md) and the [data-source index](README.md).
