# WP1.5 data-source contracts

**Status:** Candidate source matrix; the owner confirmed the complete selection is 41 distinct field IDs. Religion (48) and Gini index (56) are included. Source-specific acquisition adapters still require validation.

## Scope and source policy

WP1.5 covers the 41 selected data fields in `config/wp1_5_data_sources.json`. Natural Earth remains a geographic/cartographic source only. It is not used for statistics, economic classifications, demographics, or other WP1.5 values.

The canonical join key is the existing persistent `game_id`. Provider identifiers (ISO codes, UN M49 codes, World Bank codes, IMF codes, and source-specific IDs) are crosswalk attributes, not replacement identities. Every source import must carry an explicit, reviewed country crosswalk. Do not join by display name alone.

The project stores one current observation per country/statistic, not a full historic time series. Each observation must retain its source reference period and source edition/vintage. A publication or retrieval date is not a substitute for the period measured. Actual, estimated and projected values must remain distinguishable. A null value may be stored only with an explicit `unavailable` or `not_applicable` status; absent rows remain missing and are included in the single final completeness audit. Importers must not infer or fill missing values.

Raw source downloads remain local and are not committed. Git tracks source contracts, acquisition manifests, URLs, retrieval timestamps, release identifiers and SHA-256 checksums. A raw snapshot is immutable once captured; a new release creates a new snapshot rather than overwriting the old one.

## Field/source matrix

| Field | Canonical key | Candidate source | Storage | Important contract |
|---:|---|---|---|---|
| 1 | population | UN WPP 2024 | scalar | Reference date and estimate status |
| 2 | population_growth | UN WPP 2024 | scalar | Annual rate and exact period |
| 3 | population_density | World Bank WDI | scalar | Prefer published indicator; derivation requires aligned population and land-area periods |
| 6 | median_age | UN WPP 2024 | scalar | Reference year |
| 12 | age_distribution | UN WPP 2024 | structured | Preserve age-band boundaries, sex scope and units |
| 13 | sex_distribution | UN WPP 2024 | structured | Preserve source categories and reference year |
| 14 | net_migration | UN WPP 2024 | scalar | Select either net migrant count or rate; never mix |
| 15 | gdp | IMF WEO | scalar | Current-price GDP; retain currency/scale and actual/estimate/projected status |
| 16 | gdp_per_capita | IMF WEO | scalar | Current-price per-capita measure |
| 18 | gdp_ppp | IMF WEO | scalar | PPP basis and WEO vintage |
| 20 | inflation | IMF WEO | scalar | Distinguish annual-average from end-period CPI |
| 21 | unemployment | IMF WEO | scalar | Preserve source definition and status |
| 22 | labour_force | ILOSTAT | scalar | Age/sex scope and reference year |
| 33 | total_area | World Bank WDI | scalar | Surface area includes inland water |
| 34 | land_area | World Bank WDI | scalar | Excludes inland water |
| 41 | climate_classification | Beck et al. Köppen-Geiger V3 | structured | Spatial overlay; retain multiple classes and area shares |
| 42 | forest_area | FAO FRA 2025 | scalar | Forest definition and reference year |
| 45 | natural_resources | USGS MCS 2026 plus specialist sources | structured | Fixed candidate catalogue; distinguish occurrence, reserves, resources and production |
| 48 | religions | Pew Research Center | structured | Seven broad categories; retain estimate year and rounded-count guidance |
| 51 | human_development_index | UNDP HDR | scalar | HDI score and reference year |
| 52 | internet_usage | ITU | scalar | Individuals using the Internet; indicator definition and year |
| 54 | healthcare_expenditure | WHO GHED | scalar | Expenditure measure and denominator must be explicit |
| 55 | poverty_rate | World Bank PIP | scalar | Poverty line, welfare aggregate and survey year |
| 56 | gini_index | World Bank PIP | scalar | Preserve original scale and survey year |
| 57 | government_system | Official national sources | structured | Country-specific authoritative evidence and effective date |
| 58 | government_structure | Official national sources | structured | Explicit executive/legislative/judicial and territorial definitions |
| 62 | political_stability | World Bank WGI | scalar | Keep estimate and 0–100 score as separate keys/scales |
| 65 | capital_city | Official national sources | structured | Official designation and effective date; not necessarily largest city |
| 66 | international_memberships | Official organization registers | structured | Organization, status, as-of date and source |
| 67 | active_military_personnel | IISS Military Balance candidate | scalar | Active-personnel definition and source edition |
| 69 | military_expenditure_gdp | SIPRI | scalar | Military burden, year and edition |
| 70 | military_reserve_personnel | IISS Military Balance candidate | scalar | Reserve definition and mobilization category |
| 71 | defence_structure | IISS Military Balance candidate | structured | Branch/service structure; no operationally sensitive detail |
| 73 | co2_emissions_per_capita | Global Carbon Project candidate | scalar | Define territorial fossil CO2 versus broader greenhouse gases |
| 75 | energy_consumption | Energy Institute | scalar | Primary versus final energy and unit |
| 76 | electricity_production | Energy Institute | scalar | Gross/net generation and unit |
| 77 | oil_production | Energy Institute | scalar | Crude oil/liquids scope and unit |
| 78 | natural_gas_production | Energy Institute | scalar | Gross/marketed gas definition and unit |
| 79 | protected_areas | Protected Planet candidate | structured | Decide aggregate-only versus site-level data after rights review |
| 80 | water_resources | FAO AQUASTAT | scalar | Select internal versus total renewable freshwater |
| 81 | water_stress | FAO AQUASTAT | scalar | Preserve denominator, method and reporting year |

The machine-readable field contract is `config/wp1_5_data_sources.json`. The candidate natural-resource vocabulary is in `config/wp1_5_resource_catalog.json`; it is not a claim of complete country coverage.

## Coverage and methodology constraints

- **UN WPP 2024:** its country/area universe does not match the 242 persistent game identities. Build an explicit crosswalk and preserve uncovered identities as missing; do not synthesize data.
- **Pew religion estimates:** the dataset covers 201 countries/territories with populations of at least 100,000 in 2010 or 2020. It reports seven broad categories and recommends rounded counts for reporting small groups. Do not convert small rounded categories into false precision.
- **Climate:** Köppen-Geiger is spatially distributed. A country may contain multiple classes. Any country-level representation must be a reproducible area-weighted distribution using the chosen project geometry and raster vintage.
- **Natural resources:** USGS MCS covers more than 90 nonfuel mineral commodities, but country/commodity metrics are not uniformly available and it is not a complete inventory of all natural resources. A missing source row is not evidence of absence.
- **Macroeconomics:** IMF WEO contains historical observations, estimates and projections. Preserve the WEO release vintage and observation status; do not label every value in the newest release as an observed actual.
- **Area:** World Bank surface area includes inland waters; land area excludes inland waters. They are distinct fields.
- **Population density:** prefer a source-published indicator. If derived, use population and land area for aligned reference periods and retain the formula and input references.
- **Governance:** WGI scores are perception-based estimates. Its usage advisory restricts redistribution/republication of certain standardized values derived from third-party proprietary sources without authorization.
- **Military:** IISS is a subscription publication candidate. SIPRI military expenditure data is downloadable, but commercial use requires authorization/licensing.
- **Protected areas:** Protected Planet prohibits commercial use without prior written permission and restricts redistribution of its database materials. The project must not assume that derived or aggregated outputs are exempt.
- **Energy:** Energy Institute publishes CSV/XLSX datasets and historical editions. Values may be revised between editions; preserve the edition and file checksum.
- **Government and memberships:** no single global source is assumed. Record the exact official authority, URL, access date, status and effective date for each record.

## Acquisition readiness

Every candidate source must pass a source-specific adapter review before production import:

1. Confirm downloadable endpoint, format and update/release identifier.
2. Confirm dataset-level country coverage and country-code scheme.
3. Document each indicator's definition, unit, observation period and status semantics.
4. Capture the exact raw bytes locally and calculate SHA-256.
5. Record retrieval timestamp, source URL, release/vintage, attribution and terms URL in the manifest.
6. Map source entities to `game_id` through an explicit crosswalk; report uncovered/ambiguous mappings without guessing.
7. Import transactionally and idempotently. Never mutate the source download or existing JSON pipeline.

## Primary source references

- UN WPP: https://population.un.org/wpp/
- IMF WEO: https://www.imf.org/en/Publications/WEO/weo-database
- World Bank WDI: https://databank.worldbank.org/source/world-development-indicators
- ILOSTAT: https://ilostat.ilo.org/data/
- Beck et al. Köppen-Geiger: https://www.gloh2o.org/koppen/
- FAO FRA: https://www.fao.org/forest-resources-assessment/
- USGS MCS: https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries
- Pew religious composition: https://www.pewresearch.org/dataset/dataset-of-global-religious-composition-estimates-for-2010-and-2020/
- UNDP HDR: https://hdr.undp.org/data-center/documentation-and-downloads
- ITU: https://datahub.itu.int/
- WHO GHED: https://apps.who.int/nha/database
- World Bank PIP: https://pip.worldbank.org/
- World Bank WGI: https://www.worldbank.org/en/publication/worldwide-governance-indicators
- IISS: https://www.iiss.org/publications/the-military-balance/
- SIPRI: https://www.sipri.org/databases/milex
- Global Carbon Project: https://globalcarbonproject.org/carbonbudget/
- Energy Institute: https://www.energyinst.org/statistical-review/resources-and-data-downloads
- Protected Planet: https://www.protectedplanet.net/en/legal
- FAO AQUASTAT: https://www.fao.org/aquastat/en/


## Immutable source acquisition tooling

The initial acquisition utility is available as `tools/acquire_wp1_5_sources.py`. It accepts a **direct HTTPS file URL**, not a provider landing page, and refuses to overwrite an existing release snapshot. Raw bytes are written under `raw_data/wp1_5/<source>/<release>/`; the JSON provenance manifest is written under `data_manifests/wp1_5/<source>/<release>.json`. The manifest records the original/final URL, retrieval timestamp, release, content type, byte count, SHA-256, terms URL, attribution and the declared rights classification.

Example (replace the URL, release and filename with the exact provider download you have verified):

```fish
uv run python -m tools.acquire_wp1_5_sources \
  --source un_wpp_2024 \
  --release 2024 \
  --url "https://provider.example/path/to/direct-download.zip" \
  --filename "wpp2024.zip" \
  --terms-url "https://provider.example/terms" \
  --license-status "source-terms-to-be-recorded"
```

The example URL is deliberately a placeholder and is not a valid provider endpoint. Do not run it as-is. Confirm the exact file, edition, format, country-code scheme and dataset terms before acquisition. The utility does not scrape landing pages, guess download links, normalize provider data or import observations into SQLite. Those source-specific steps remain separate so the captured source bytes and provenance are auditable.


## Explicit source crosswalk format

WP1.5 crosswalk validation is implemented in `tools/database/source_crosswalk.py`. A crosswalk is a curated JSON file for one provider dataset. It maps each provider's stable identifier to exactly one persistent `game_id`; it does not use labels as keys and it does not perform fuzzy matching.

Example:

```json
{
  "schema_version": 1,
  "dataset": "un_wpp_2024",
  "source_key": "un_wpp_2024",
  "mappings": [
    {
      "game_id": "tc_0123456789abcdef0123456789abcdef",
      "source_id": "4",
      "source_name": "Afghanistan",
      "match_method": "authoritative_identifier",
      "evidence_url": "https://population.un.org/wpp/"
    }
  ]
}
```

Allowed match methods are `authoritative_identifier` and `reviewed_manual`. Provider source IDs and game IDs must each be unique within a crosswalk. Optional evidence URLs must use HTTPS. When the canonical identity set is supplied, unknown game IDs are rejected. Partial coverage is permitted and explicitly reported; a source's absence of a country is not converted to a zero or an inferred match. Name-only, fuzzy-name, ISO-inferred and coordinate-inferred matches are rejected by this validator.

Focused validation:

```fish
uv run pytest -v tests/test_wp1_5_source_crosswalk.py tests/test_wp1_5_source_acquisition.py tests/test_wp1_5_source_contract.py
uv run python -m compileall -q tools/database
``

The crosswalk validator is a validation primitive, not yet a production importer. It does not write `country_sources` or statistic rows. Source-specific crosswalk files must be assembled and reviewed before any dataset import.


## Normalized observation import contract

The generic SQLite importer is `tools/database/statistics_import.py`, exposed through `tools/import_wp1_5.py`. It consumes three explicit inputs: (1) a normalized observation JSON file, (2) the source-specific country crosswalk, and (3) the immutable acquisition manifest whose raw file is still present locally. It verifies the raw-file SHA-256 against the manifest before any database write.

Normalized observations use this versioned envelope:

```json
{
  "schema_version": 1,
  "work_package": "WP1.5",
  "source_key": "un_wpp_2024",
  "release": "2024-r1",
  "source_sha256": "<64-character captured raw-file SHA-256>",
  "observations": [
    {
      "game_id": "tc_0123456789abcdef0123456789abcdef",
      "source_id": "4",
      "field_id": 1,
      "value": 123456,
      "value_status": "observed",
      "observation_period": "2024",
      "unit": "people",
      "source_reference": "https://population.un.org/wpp/",
      "methodology": "Provider-reported total population"
    }
  ]
}
```

Every row must resolve through the explicit crosswalk, use a field ID whose contracted primary source matches the manifest source key, and have a non-empty observation period. Scalar values must be finite numbers; explicit SQL NULL requires `unavailable` or `not_applicable`. Structured values must be JSON objects or arrays. Duplicate country/field rows are rejected. The importer preserves actual/estimated/projected status and source release, reference, method and retrieval timestamp.

Writes are transactional. Repeating an identical snapshot is idempotent. A newer release from the same contracted provider replaces that provider's current value for the same country/field; a conflicting value already owned by a different provider is rejected and the transaction is rolled back. The dataset import remains a candidate; this stage does not approve source data or mark any country identity/review status as verified. It does not populate `country_sources`, infer missing rows, or create the final completeness audit.

The generic importer is intentionally not a raw-file parser. Provider-specific adapters must inspect and normalize each exact source release before calling it. Do not manufacture normalized files from placeholder URLs or unverified source schemas.

CLI help:

```fish
uv run python -m tools.import_wp1_5 --help
```
