# WP1.5 source licence and reuse report

**Checked:** 2026-10-31  
**Status:** Initial public-terms review. This is an informational register, not legal advice and not a production redistribution clearance. A downloadable file is not automatically openly licensed.

## Classification summary

| Source | Fields | Classification | Restrictions / notes |
|---|---|---|---|
| Beck et al. Köppen-Geiger V3 | 41 | **Attribution required — CC BY 4.0** | Commercial and non-commercial reuse/adaptation allowed with attribution and citation. |
| USGS Mineral Commodity Summaries 2026 data release | 45 | **Free/open — CC0 1.0 for the data release** | The 2026 data release is marked CC0. Verify each future edition and any third-party content separately. |
| World Bank WDI | 3, 33, 34 | **Open licence — verify dataset-specific terms** | World Bank materials commonly carry dataset-specific terms; confirm the actual indicator dataset terms and attribution before publication. |
| World Bank PIP | 55, 56 | **Unclear / dataset-specific terms** | Confirm PIP data terms and underlying survey-source restrictions for the exact downloadable dataset. |
| World Bank WGI | 62 | **Redistribution restricted for some underlying values** | Standardized/rescaled values derived from five named proprietary providers may be used for own analysis/research/education, but not redistributed or republished without authorization from the relevant provider. |
| SIPRI Military Expenditure Database | 69 | **Commercial authorization / licence required** | Fair use is limited to non-commercial purposes and less than 10% of a dataset; commercial use requires authorization and normally a royalty. Reproduction generally requires authorization outside fair use. |
| Protected Planet WDPA / GD-PAME | 79 | **Commercial use and redistribution restricted** | Commercial use requires prior written permission. No sublicensing or redistribution of the database materials without prior written permission. |
| IISS The Military Balance | 67, 70, 71 | **Proprietary / subscription** | Candidate source; subscription access and redistribution rights require separate review. |
| Energy Institute Statistical Review | 75–78 | **Unclear / terms not verified** | CSV/XLSX downloads and archives are available, but availability alone does not establish an open licence or redistribution permission. |
| Pew Global Religious Composition | 48 | **Unclear / dataset-specific terms** | Dataset download is available; confirm the dataset's licence and redistribution conditions before publishing derived or copied values. Respect rounded-count reporting guidance. |
| UN WPP 2024 | 1, 2, 6, 12, 13, 14 | **Unclear / terms not verified** | Public download/API access is available; exact data licence and redistribution terms must be checked against the downloaded release. |
| IMF WEO | 15, 16, 18, 20, 21 | **Unclear / terms not verified** | Public database access does not by itself establish an open licence. Verify IMF terms for the dataset and intended reuse. |
| ILOSTAT | 22 | **Unclear / terms not verified** | Confirm the licence and any source-country restrictions for the selected indicator/table. |
| FAO FRA 2025 | 42 | **Unclear / terms not verified** | Verify dataset-specific licence and attribution requirements for the downloaded tables. |
| UNDP HDR statistical data | 51 | **Unclear / terms not verified** | Verify the download/API terms for the exact statistical table and edition. |
| ITU DataHub | 52 | **Unclear / possible access/reuse restrictions** | Verify dataset-specific reuse and redistribution permissions; do not infer an open licence from public access. |
| WHO GHED | 54 | **Unclear / terms not verified** | Verify WHO data terms and attribution requirements for the selected download. |
| Official government sources | 57, 58, 65 | **Country/source-specific** | Government information may be public but copyright and reuse terms vary by jurisdiction and source. Record each authority's terms. |
| Official organization registers | 66 | **Organization-specific** | Terms vary by organization. Prefer factual membership status with a source citation; record source terms for each register. |
| Global Carbon Project | 73 | **Unclear / dataset-specific terms** | Confirm the exact data product's licence, attribution and redistribution conditions before acquisition for publication. |
| FAO AQUASTAT | 80, 81 | **Unclear / terms not verified** | Confirm the terms for the exact indicator export/API and its underlying source data. |

## Important terms verified from primary pages

### Beck et al. Köppen-Geiger V3

The dataset page states that maps and code are available under CC BY 4.0, allowing commercial and non-commercial use, adaptation and sharing with attribution. Cite Beck et al. (2023), *Scientific Data* 10, 724, DOI: 10.1038/s41597-023-02549-6.

Terms: https://www.gloh2o.org/koppen/

### USGS Mineral Commodity Summaries 2026

The USGS 2026 data release metadata marks the release CC0 1.0 Universal. The release covers world production statistics for more than 90 nonfuel mineral commodities. This does not imply that every resource or country/metric pair is covered.

Data release: https://www.usgs.gov/data/mineral-commodity-summaries-2026-data-release

### World Bank WGI

The WGI usage advisory identifies five third-party proprietary data providers (Economist Intelligence Unit, Gallup World Poll, The PRS Group, S&P Global and the World Economic Forum). The published standardized/rescaled values derived from those providers may be used only for users' own analysis, research or educational activities; redistribution/republication requires prior authorization from the relevant provider.

Terms: https://www.worldbank.org/en/publication/worldwide-governance-indicators/usage-advisory

### SIPRI

SIPRI's fair-use policy requires both non-commercial purpose and reproduction of less than 10% of a published dataset. Commercial use requires authorization and normally a royalty. Reproduction outside the fair-use policy requires authorization.

Terms: https://www.sipri.org/about/terms-and-conditions  
Database: https://www.sipri.org/databases/milex

### Protected Planet

UNEP-WCMC's terms prohibit commercial use of WDPA/GD-PAME materials and derivative works without prior written permission. They also prohibit sublicensing and redistribution without prior written permission.

Terms: https://www.protectedplanet.net/en/legal

### Energy Institute

The Statistical Review page provides downloadable XLSX and consolidated CSV datasets and archives. It warns that historical values can change between editions as data and methodologies are revised. The public download page reviewed here does not establish a general open licence; treat reuse rights as unclear until the relevant terms are confirmed.

Downloads: https://www.energyinst.org/statistical-review/resources-and-data-downloads

## Project handling policy

- Licence restrictions do **not** block source acquisition or local research imports, per the approved WP1.5 decision.
- The register must never describe an unclear, proprietary, non-commercial or redistribution-restricted source as open.
- Keep source terms URL, checked date, attribution text, commercial-use restriction, redistribution/modification restriction, permission/subscription requirement and source edition in the source manifest.
- Raw source downloads remain local. Git stores source manifests, URLs, retrieval dates, release identifiers and SHA-256 checksums, not raw datasets.
- A future decision to redistribute data in a public game build, public API, downloadable asset or commercial product requires a separate rights review. Local acquisition approval is not redistribution permission.
- Where permissions are unclear, keep the source classified as unclear/unverified until the exact dataset terms are checked; do not silently upgrade its classification.

## Primary references

- https://www.gloh2o.org/koppen/
- https://www.usgs.gov/data/mineral-commodity-summaries-2026-data-release
- https://www.worldbank.org/en/publication/worldwide-governance-indicators/usage-advisory
- https://www.sipri.org/about/terms-and-conditions
- https://www.sipri.org/databases/milex
- https://www.protectedplanet.net/en/legal
- https://www.energyinst.org/statistical-review/resources-and-data-downloads
