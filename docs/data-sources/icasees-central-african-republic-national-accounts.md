# ICASEES Central African Republic national accounts

## Source identity

- **Provider:** Institut Centrafricain des Statistiques et des Études Économiques et Sociales (ICASEES).
- **Subject:** Central African Republic national accounts and GDP rebasing.
- **Official catalogue:** https://icasees.org/publications/tableau-de-bord/statistiques-structurelles/statistiques-economiques/comptes-nationaux
- **Dataset publication:** https://www.icasees.org/index.php/publications/tableau-de-bord/telecharger/jeux-de-donnees-des-comptes-nationaux-de-2005-2019-et-2019-2021-paru-en-2026
- **Definitive accounts publication:** https://www.icasees.org/index.php/publications/tableau-de-bord/telecharger/comptes-nationaux-definitifs-2019-2021-de-la-republique-centrafricaine
- **GDP rebasing memo:** https://www.icasees.org/index.php/actualites/399-icasees-publication-de-laide-memoire-sur-les-travaux-de-rebasage-du-pib-base-2019-selon-le-scn-2008
- **Licence:** CC BY 4.0 as stated in the ICASEES catalogue/publication metadata. Retain provider attribution when redistributing derived material.

## Acquired files and repository layout

The following original provider files were added to the repository in commit `ed62810037abdc2975a51b0677e3b3d7c6a57bdb`.

```text
raw_data/
└── sources/
    └── icasees/
        ├── national_accounts_dataset/
        │   └── 2026-07-16/
        │       └── 11-Comptes nationaux_16-07-2026.xlsx
        ├── national_accounts_2019_2021/
        │   └── 2026-07-30/
        │       └── COMPTES-NATIONAUX-2019_2021.pdf
        └── gdp_rebasing_2019/
            └── 2026-08-07/
                └── 2026-08_Aide-memoire_Rebasage_PIB_Base2019_SCN2008_RCA.pdf
```

### File roles

| File | Format | Role | How to use it |
|---|---|---|---|
| `11-Comptes nationaux_16-07-2026.xlsx` | Excel workbook | Published national-accounts dataset titled for 2005–2019 and 2019–2021 | Primary machine-readable source for extracting national-accounts series. Inspect workbook sheets, units, valuation basis, years and revision notes before normalization. |
| `COMPTES-NATIONAUX-2019_2021.pdf` | PDF | Definitive national accounts for 2019–2021 | Supporting publication for tables, concepts, methods and interpretation of the 2019–2021 accounts. |
| `2026-08_Aide-memoire_Rebasage_PIB_Base2019_SCN2008_RCA.pdf` | PDF | GDP rebasing memo: 2019 base, System of National Accounts 2008 (SNA 2008) | Methodological evidence for interpreting the change in GDP level/base and comparing vintages. |

The Excel workbook is a **file-based dataset**, not a live database service or API. The PDFs are supporting documents, not data stores. The workbook's actual sheet structure and series have not yet been parsed or validated.

## Intended analytical use

This source was acquired to investigate Central African Republic GDP comparability, especially the large differences previously observed between IMF WEO and World Bank WDI for nominal GDP and PPP GDP.

The 2019 base-year rebasing and SNA 2008 methodology are potentially material to the interpretation of the historical series. Before comparing values, inspect and record:

- current-price versus constant-price series;
- local-currency units and scale;
- GDP and component definitions and valuation basis;
- calendar/fiscal reference periods;
- treatment of 2019 overlap and any backcast/retropolation;
- whether 2005–2019 and 2019–2021 are continuous, revised, or differently based series;
- publication/revision dates and any explanatory footnotes.

Do not assume that the two ranges can be concatenated without a break or that a nominal local-currency series can be compared directly with USD or PPP series. The 2019 rebasing memo and definitive accounts should be used to establish the correct interpretation.

## Acquisition and validation status

- Original workbook and two PDFs are present at the paths above.
- Files were committed to Git in `ed62810037abdc2975a51b0677e3b3d7c6a57bdb`.
- A provider-specific read-only assessment CLI is implemented in `tools/assess_icasees_national_accounts.py`.
- It reuses the central source registry and shared source-report bundle writer; it does not create a second registry or copy the committed source files.
- The `manifest` command records a fingerprint manifest for the exact three committed files, pinned to the byte counts and SHA-256 values from the reviewed local inventory. It refuses to overwrite an existing manifest.
- The `assess` command verifies all three fingerprints, inventories workbook sheets and formulas, extracts the historical and revised GDP series separately, checks sector value added against total value added, checks GDP = total value added + product taxes, evaluates restricted arithmetic formulas with cell references, including SUM over a rectangular cell range without relying on Excel's cached formula results, cross-checks duplicate historical/revised tables, and extracts relevant text from both PDFs when pypdf is available.
- The workbook parser treats the two 2019 columns in `Donnée_SCN2008` as distinct historical and revised blocks. It does not join sector classifications by indicator code or splice the series.
- The workbook's unit/scale-label conflict remains unresolved until the official PDF evidence is reviewed. No normalized observations have been created.
- No ICASEES observations have been imported into SQLite.
- No source-selection policy, fallback, manual override, approval, or release promotion has been changed as a result of this acquisition.

The files being committed is a repository-state fact, not a general change to the source-storage policy. The existing project-wide convention in [source management](source-management.md) says raw snapshots are local/untracked and manifests are tracked. The latest asset commit also changed `.gitignore` to stop ignoring `raw_data/sources/`, and committed other raw source snapshots. This differs from the documented convention and should be treated as a separate repository-policy decision; this document does not silently redefine that policy.

## Assessment commands

Run from the repository root:

```fish
uv run python -m tools.assess_icasees_national_accounts manifest
uv run --with pypdf python -m tools.assess_icasees_national_accounts assess
uv run --extra dev python -m pytest -v tests/test_icasees_national_accounts_assessment.py
```

- `manifest` records hashes for the files already in Git; it does not download or copy them. The manifest is immutable.
- `assess` verifies all three fingerprints, inventories workbook sheets and formulas, extracts historical and revised GDP separately, checks sector VAB against total VAB and GDP against value added plus product taxes, and cross-checks duplicate tables.
- pypdf is supplied ephemerally by `uv run --with pypdf` for PDF text extraction; the project dependency list is unchanged.
- Reports are written under `reports/sources/icasees-national-accounts/<run-id>/` with assessment JSON, Markdown summary, provenance, workbook inventory and GDP-series CSVs.
- The generic `tools.manage_sources check` command only checks registry entries with generic `downloads`; ICASEES retains its publication-oriented paths and is verified by this dedicated validator. Its absence from the generic snapshot-check listing is expected.

## Remaining analytical decisions

1. Review the extracted evidence pages from the definitive accounts and rebasing memo to resolve the unit/scale conflict and document the 2019 base/revision methodology.
2. Determine whether the 2005–2019 and 2019–2021 tables can be reconciled into a defensible continuous series; preserve any break if they cannot.
3. Compare only verified, unit-aligned ICASEES GDP observations with IMF WEO and WDI, retaining provider vintages and year conventions.
4. Only after that assessment, decide whether a normalized ICASEES adapter and any source-policy review are warranted.

All processing must remain read-only with respect to the canonical SQLite database until the separate validation and approval lifecycle is completed.
