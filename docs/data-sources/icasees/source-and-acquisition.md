# ICASEES national accounts — source and acquisition

## Provider and scope

- **Provider:** Institut Centrafricain des Statistiques et des Études Économiques et Sociales (ICASEES).
- **Subject:** Central African Republic national accounts and GDP rebasing.
- **Official catalogue:** https://icasees.org/publications/tableau-de-bord/statistiques-structurelles/statistiques-economiques/comptes-nationaux
- **Licence:** CC BY 4.0 as stated in the ICASEES catalogue/publication metadata. Retain provider attribution when redistributing derived material.
- **Acquisition mode:** manual publication download; no queryable ICASEES database/API was verified. The Excel workbook is a file-based dataset, not a database server.

## Publications

| Publication | Published | Official URL | Role |
|---|---|---|---|
| Jeux de données des Comptes Nationaux de 2005-2019 et 2019-2021 | 16 July 2026 | https://www.icasees.org/index.php/publications/tableau-de-bord/telecharger/jeux-de-donnees-des-comptes-nationaux-de-2005-2019-et-2019-2021-paru-en-2026 | Machine-readable workbook |
| Comptes Nationaux définitifs 2019-2021 de la République centrafricaine | 30 July 2026 | https://www.icasees.org/index.php/publications/tableau-de-bord/telecharger/comptes-nationaux-definitifs-2019-2021-de-la-republique-centrafricaine | Definitive accounts and detailed tables |
| Rebasage du PIB de la République centrafricaine (Base 2019 – SCN 2008) | 7 August 2026 | https://www.icasees.org/index.php/actualites/399-icasees-publication-de-laide-memoire-sur-les-travaux-de-rebasage-du-pib-base-2019-selon-le-scn-2008 | Rebase methodology and peer-review evidence |

Supporting ERETES materials:
- Nomenclatures: https://www.icasees.org/index.php/publications/tableau-de-bord/telecharger/nomenclatures-de-travail-utilisees-avec-le-module-eretes-pour-lelaboration-des-comptes-nationaux-definitifs-de-la-republique-centrafricaine-2019-2021
- ERETES nomenclature note: https://icasees.org/publications/tableau-de-bord/publications/note-explicative-sur-la-nomenclature-des-comptes-nationaux-selon-le-module-eretes-en-republique-centrafricaine

## Acquired repository files

Original French filenames are preserved:

| Role | Repository path | SHA-256 |
|---|---|---|
| Workbook | raw_data/sources/icasees/national_accounts_dataset/2026-07-16/11-Comptes nationaux_16-07-2026.xlsx | 7d6f764f1eba87c5df53ffedbbf0a90a48061098509cd67f9070501737b63dce |
| Definitive accounts PDF | raw_data/sources/icasees/national_accounts_2019_2021/2026-07-30/COMPTES-NATIONAUX-2019_2021.pdf | e419508a82e9d09421405880c7a8212376d60776cc809ed942241bd231e6d173 |
| Rebase memo PDF | raw_data/sources/icasees/gdp_rebasing_2019/2026-08-07/2026-08_Aide-memoire_Rebasage_PIB_Base2019_SCN2008_RCA.pdf | 403bae60e88c7d8701bc0d1498228a6a49e96bc90cf2cdc4de6be8d451f29bc5 |

The files were committed in commit ed62810037abdc2975a51b0677e3b3d7c6a57bdb. Their immutable manifest is data_manifests/sources/icasees_national_accounts/manual_publication_bundle/2026-07-16.json (three files; recorded 2026-11-02T17:42:44.791034+00:00; raw files copied false).

The source is registered as icasees_national_accounts in config/data_sources.json, with manual release discovery and no generic download adapter. See [project source management](../source-management.md).

## Repository storage-policy caveat

The project-wide source-management convention says raw snapshots are local/untracked and manifests are tracked. The asset commit changed .gitignore so raw_data/sources/ stopped being ignored and committed raw source snapshots. This differs from the documented convention and remains a separate repository-policy decision; this source record does not silently redefine it.

## Intended analytical use

The files were acquired to investigate Central African Republic GDP comparability, especially the previously observed differences between IMF WEO and World Bank WDI. The definitive accounts and rebasing memo provide methodological context; the workbook provides machine-readable series. See [dataset structure](dataset-and-workbook-structure.md) and [GDP reconciliation](gdp-scale-and-weo-reconciliation.md).
