# ILOSTAT labour-force acquisition research — WP1.5 field 22

**Status:** provider discovery and candidate-series assessment; no source selection, acquisition or import has been performed  
**Reviewed:** 2026-11-23  
**WP1.5 field:** 22 — `labour_force`  
**Registered source key:** `ilostat`  
**Primary-source policy:** ILOSTAT; configured WDI fallback only when the series definition, age/sex scope and reference period are compatible

## 1. Scope and contract gap

The current field contract specifies a scalar count in people and says to preserve age/sex scope and reference year. It does not yet define:
- the target ICLS statistical standard (13th ICLS or 19th ICLS);
- the lower/upper age boundary for the total labour force;
- whether a national-source series or ILO modelled estimate is preferred;
- the selection rule where ILOSTAT publishes several source observations for one country/year;
- the treatment of breaks in series, preliminary observations and source-specific notes.

These are not parser details. They determine what the field means. Do not silently choose a series or collapse multiple source records until the field contract is explicit.

## 2. Official acquisition channels

The official ILOSTAT data page exposes indicator and country catalogues, bulk downloads, an API/web service, and SDMX tools:

- Data catalogue: https://ilostat.ilo.org/data/
- Bulk download facility: https://ilostat.ilo.org/data/bulk/
- Labour Force Statistics database description: https://ilostat.ilo.org/databases/lfs/description/
- SDMX API user guide: https://www.ilo.org/resource/other/ilostat-sdmx-user-guide
- SDMX dissemination API reference guide: https://www.ilo.org/sites/default/files/2024-12/ILOSTAT-SDMX_Dissem%20API%20Ref%20Guide_V4.1-%28ILO%20Style%29.pdf

The bulk service publishes gzip-compressed CSV data and separate code dictionaries. The indicator directory includes a table of contents with dataset coverage and periods. Each CSV row can carry reference area, source, indicator, classification dimensions, period, observation value, status and note metadata. Preserve these dimensions and notes; the indicator label alone is not sufficient provenance.

The bulk directory reported a last update of **2026-11-22** when reviewed. This is a provider-directory update date, not a release timestamp for every observation.

## 3. Candidate annual series

Two annual candidates are visible in the current official bulk catalogue:

| Candidate | Standard | Catalogue coverage | Disposition |
|---|---|---:|---|
| `EAP_TEAP_SEX_AGE_NB_A` | Labour force statistics using previous ILO definition (ICLS13) | 410,624 records; 315 reference areas; updated 2026-11-22 | Preferred candidate for further assessment, not yet selected |
| `EAP_5EAP_SEX_AGE_NB_A` | Work Statistics using current ILO definition (ICLS19) | 10,241 records; 134 reference areas; updated 2026-11-22 | Retain as a comparison candidate; do not merge with ICLS13 |

The ILO's LFS database description explicitly warns that most countries currently follow ICLS13 and that most WORK/ICLS19 data are not comparable with ICLS13-based databases. This is a material reason to assess the broader ICLS13 candidate first for a global country field. It is not permission to mix the two standards or to claim that every country's national series uses an identical age boundary.

Official evidence:
- ILO describes the distinction between ICLS13-based LFS indicators and ICLS19-based WORK indicators, and says most countries currently follow ICLS13: https://ilostat.ilo.org/databases/lfs/description/
- The official bulk catalogue lists both annual candidate files and their current record/reference-area counts: https://rplumber.ilo.org/files/website/bulk/indicator.html

## 4. Capture targets and immutable evidence

For a first capture candidate, inspect and then capture the complete ICLS13 annual indicator bundle:

- Data: `EAP_TEAP_SEX_AGE_NB_A`
- Bulk endpoint observed from the official directory: `https://rplumber.ilo.org/data/indicator?format=.csv.gz&id=EAP_TEAP_SEX_AGE_NB_A`
- Required dictionaries include at least the English reference-area, source, indicator, sex, age, observation-status, unit-measure, unit-multiplier, and note dictionaries from the official DIC directory: `https://rplumber.ilo.org/files/website/bulk/dic.html`

The data and dictionary files must be acquired as one documented release bundle if they are needed to decode the captured records. Record each artifact separately with role, final URL, retrieval timestamp, media type, byte count and SHA-256. Do not treat a successful HTTP response as a validated release.

The generic WP1.5 snapshot helper currently accepts a direct HTTPS download URL and writes an immutable raw snapshot plus manifest. Its current one-file CLI is not by itself a multi-artifact bundle adapter. Before using it, decide whether the data and dictionaries are represented as one acquisition with multiple artifact rows or whether the acquisition helper needs a narrowly scoped bundle extension. Do not create unrelated acquisition streams for dictionaries that only decode the same dataset.

No raw ILOSTAT bytes have been captured by this research step. Keep raw source files local-only under the repository's established policy; track manifests and documentation, not source payloads.

## 5. Series-selection and normalization gates

Before choosing the ICLS13 series, inspect the actual CSV and dictionaries and report:

1. Available `sex` values and the exact code/label for total persons.
2. Available age classifications and whether a defensible total-age category exists. Do not sum age bands unless the categories are mutually exclusive, exhaustive, and have compatible coverage.
3. Whether the table contains multiple source records for the same reference-area/year/classification, and what ILOSTAT's best-source or source-selection metadata means. Do not select one source row by file order or overwrite duplicates.
4. Unit and multiplier codes. Convert to people only through explicit unit metadata; do not assume that a filename suffix or a label is enough.
5. Observation status and note fields, including breaks in series, provisional/unreliable values and source/method notes.
6. Country and territory reference-area coverage, regional aggregates, non-country areas, and provider code changes.
7. First/latest populated year by area and missingness; a row count is not a coverage guarantee.
8. The applicable licence, attribution and redistribution terms for the bulk dataset and metadata. The central source registry currently records ILOSTAT as `unclear_or_unverified`; do not change that status until evidence supports it.

The field 22 fallback to World Bank WDI is conditional. Compare its indicator definition, age/sex scope, reference period, unit and status before filling any ILOSTAT gap. Never combine a modelled estimate and a national-source observation without preserving the distinct source and method.

## 6. Required output before acquisition is considered complete

The first ILOSTAT work package should produce:
- a provider-series decision record (ICLS13 vs ICLS19, with evidence and reasons);
- a field-22 sub-definition (age boundary, sex scope, national/modelled source treatment);
- an immutable multi-artifact capture and manifest;
- a read-only source audit reporting coverage, dimensions, duplicates, status, missingness and units;
- a reviewed explicit source-country-code to `game_id` crosswalk;
- a normalized candidate artifact with original dimensions and provenance retained.

Only after those gates pass should the existing fingerprinted approval/application workflow be used. Acquisition, semantic validation, approval, canonical application and release promotion remain distinct. Do not change the WDI fallback policy or any other source-selection rule as part of this acquisition.

## 7. Current conclusion

ILOSTAT provides an appropriate official global acquisition channel. The ICLS13 annual labour-force table is the strongest initial candidate because it has materially broader catalogue coverage and aligns with the standard most countries currently follow. However, the total-sex/age selection, multiple-source handling, unit conversion, identity crosswalk and licensing still require verification. **No series has yet been formally selected, and no data have been acquired or imported.**
