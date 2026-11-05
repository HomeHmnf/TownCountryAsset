# ICASEES Central African Republic national accounts

**Status:** Acquired; workbook structure assessed; revised GDP scale resolved and mechanically cross-checked against the pinned October 2026 IMF WEO CSV. No canonical database import or source-policy change.  
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
uv run --with pypdf python -m tools.assess_icasees_national_accounts assess
uv run --extra dev python -m pytest -v tests/test_icasees_national_accounts_assessment.py
```

The assessment verifies the three ICASEES manifest fingerprints, inventories workbook structure, checks GDP arithmetic and duplicate presentations, and extracts relevant PDF text when pypdf is available. It also verifies the fingerprint of the pinned October 2026 IMF WEO CSV and checks the exact Central African Republic national-currency series `CAF.NGDP.A` for 2019–2021, including its country, indicator, annual frequency, domestic-currency unit, billion scale, January/December reporting period and 2022 latest-actual-year metadata. A missing, altered or metadata-inconsistent WEO input fails the assessment. The WEO comparison is a read-only corroboration, not evidence of independent source compilation.

The CLI resolves the revised GDP scale as billion FCFA, while explicitly limiting that resolution to GDP. The workbook's observation-level unit label remains recorded as published and is not silently rewritten. The tool does not import observations into SQLite or change source-selection policy.

## Boundaries and next work

- No ICASEES observations have been imported into SQLite.
- No source-selection policy, fallback, manual override, approval or release promotion has been changed.
- The ICASEES source remains a manual publication source; the generic source manager does not acquire it.
- A future adapter/import proposal must use immutable input fingerprints, validate units and identity mappings, produce review reports, and pass the shared explicit approval lifecycle before transactional application.

See [source management](source-management.md), [source selection](source-selection.md) and the [data-source index](README.md).
