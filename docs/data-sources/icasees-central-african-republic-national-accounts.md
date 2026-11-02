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
- No ICASEES acquisition manifests have yet been added under `data_manifests/sources/`.
- No provider-specific parser, workbook inventory, sheet-level validation, normalized observations, or checksum-based acquisition report has yet been produced.
- No ICASEES observations have been imported into SQLite.
- No source-selection policy, fallback, manual override, approval, or release promotion has been changed as a result of this acquisition.

The files being committed is a repository-state fact, not a general change to the source-storage policy. The existing project-wide convention in [source management](source-management.md) says raw snapshots are local/untracked and manifests are tracked. The latest asset commit also changed `.gitignore` to stop ignoring `raw_data/sources/`, and committed other raw source snapshots. This differs from the documented convention and should be treated as a separate repository-policy decision; this document does not silently redefine that policy.

## Next validation steps

1. Inventory workbook sheets, dimensions, merged cells, headers, units and year columns.
2. Extract candidate GDP series without altering the original workbook.
3. Reconcile the workbook with the definitive 2019–2021 PDF and rebasing memo.
4. Determine whether a consistent 2005–2021 nominal GDP series can be constructed and document any break/revision.
5. Compare aligned Central African Republic values against the IMF WEO and WDI observations, preserving source vintages and units.
6. Only after that assessment, decide whether a normalized ICASEES adapter and any source-policy review are warranted.

All processing must remain read-only with respect to the canonical SQLite database until the separate validation and approval lifecycle is completed.
