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

The crosswalk validator is used by the transactional normalized-observation importer. Each source-specific crosswalk must be explicitly assembled and reviewed before import; the importer persists its provider IDs in `country_sources` and rejects conflicts with existing identity mappings.


## Normalized observation import contract

The transactional importer is \`tools/database/statistics_import.py\`, exposed through \`tools/import_wp1_5.py\`. Provider-specific adapters must convert captured source files into a normalized JSON file; the importer does not parse provider CSV/XLSX/PDF formats.

The normalized file identifies the exact source snapshot using \`source_key\`, \`release\` and \`source_sha256\`, and carries one row per country/field:

\`\`\`json
{
  "schema_version": 1,
  "work_package": "WP1.5",
  "source_key": "un_wpp_2024",
  "release": "2024",
  "source_sha256": "<64-character SHA-256 from the acquisition manifest>",
  "observations": [
    {
      "game_id": "tc_0123456789abcdef0123456789abcdef",
      "source_id": "4",
      "field_id": 1,
      "value": 42000000,
      "value_status": "estimated",
      "observation_period": "2024",
      "unit": "people",
      "methodology": "Provider-reported total population"
    },
    {
      "game_id": "tc_0123456789abcdef0123456789abcdef",
      "source_id": "4",
      "field_id": 12,
      "value": {"0-4": 3500000, "5-9": 3400000},
      "value_status": "estimated",
      "observation_period": "2024",
      "unit": "people by five-year age band"
    }
  ]
}
\`\`\`

Use the provider's exact source identifier in \`source_id\`; \`game_id\` must match the same pair in the explicit crosswalk. The \`field_id\` must be one of the 41 selected IDs and the source must match that field's declared primary source. Scalar \`value\` must be a finite number, or JSON null with \`value_status\` set to \`unavailable\` or \`not_applicable\`. Structured \`value\` must be a finite JSON object or array. The importer stores scalar values in \`current_statistics\` and structured values in \`selected_game_data\`.

The importer verifies the captured raw file against the manifest checksum, release and source key; validates the crosswalk and canonical database identities; persists crosswalk mappings in \`country_sources\`; and writes observations plus dataset provenance in one SQLite transaction. It rejects duplicate country/field rows, wrong-source fields, identity conflicts, and overwrites from a different provider. A later release from the same provider may replace that provider's current observation while preserving the prior dataset-import provenance row. Imported records remain candidate data; no verification/review status is promoted.

Run:

\`\`\`fish
uv run python -m tools.import_wp1_5 \\
  --observations path/to/normalized-observations.json \\
  --crosswalk path/to/provider-crosswalk.json \\
  --manifest data_manifests/wp1_5/provider-key/release.json \\
  --database /tmp/tca-wp1-5-import.sqlite
\`\`\`

The placeholders above are illustrative. Do not run the command until a real provider snapshot, matching manifest, reviewed crosswalk and source-specific normalized file exist.


### Import validation and release ordering

The importer now verifies that the manifest's raw snapshot path is under the repository's `raw_data/` tree, the file is non-empty, and both its byte count and SHA-256 match the manifest. The retrieval timestamp must be timezone-aware ISO-8601; a supplied terms URL must use HTTPS. The source contract's declared unit (or one of its explicitly listed `_or_` alternatives) is enforced for every observation. A missing methodology defaults to the field's documented method; a missing row-level source reference falls back to the manifest's final source URL.

A release from the same provider may replace that provider's current value only when its manifest retrieval timestamp is strictly later than the current row's retrieval timestamp. Equal-time changed content and older snapshots are rejected, preventing a late replay of an older release from rolling current data backward. Conflicts with values owned by another source are rejected. All mapping/provenance/observation writes remain in one transaction.


## Verified UN WPP 2024 acquisition profile

The official UN download catalogue was inspected on 2026-10-31. It declares CC BY 3.0 IGO and documents the CSV schema. The main WPP 2024 release covers 237 countries/areas; estimates run through 2023 and the medium projection covers 2024–2100. CSV location columns include `LocID` (ISO 3166-1 numeric for countries/areas), `ISO3_code`, `ISO2_code`, `LocTypeID`, `LocTypeName`, `ParentID`, and `Location`. Use the codes and type metadata; do not join by `Location` text. The common dimensions include `Time` and `MidPeriod`; age-disaggregated files add `AgeGrp`, `AgeGrpStart`, and `AgeGrpSpan`.

Pinned direct downloads from the official catalogue:

| Snapshot purpose | Release key | File |
|---|---|---|
| Total population, population growth, median age, male/female population, net migration | `2024-main-demographic` | [WPP2024_Demographic_Indicators_Medium.csv.gz](https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_Demographic_Indicators_Medium.csv.gz) |
| Population by five-year age group and sex | `2024-main-age-sex` | [WPP2024_PopulationByAge5GroupSex_Medium.csv.gz](https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_PopulationByAge5GroupSex_Medium.csv.gz) |
| Interim revision bundle | `2026-01-19-togo-update` | [WPP2024_CSV_files_update.zip](https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/WPP2024_CSV_files_update.zip) |

The interim update is dated 19 January 2026 and corrects Togo population estimates and medium projections using newly available 2022 census results. The UN says other locations and global/regional aggregates are unchanged. Apply its matching `*_Update.csv` rows only to Togo; do not replace the full base dataset with this Togo-only bundle. It includes updated demographic-indicator, total-population-by-sex and population-by-age/sex files. The next WPP revision was postponed to 11 July 2027, so this is the latest published WPP revision/update identified in this source review.

The exact URLs, filenames, release keys, field IDs and rights metadata are machine-readable under `sources.un_wpp_2024.downloads` in `config/wp1_5_data_sources.json`. Capture each file as its own immutable acquisition snapshot using the release key shown above. Use terms URL `https://population.un.org/wpp/`, licence status `CC BY 3.0 IGO`, and attribution: United Nations, Department of Economic and Social Affairs, Population Division (2024). *World Population Prospects 2024, Online Edition*.

Do not implement the WPP adapter until the owner has acquired these snapshots and the actual CSV headers/notes have been inspected locally. In particular, retain WPP's thousand-person units and distinguish historical estimates (through 2023) from medium-variant projections (2024 onward). Population density is not sourced from WPP under this contract; field 3 remains World Bank WDI.


### WPP acquisition commands

Run each snapshot separately; the distinct release keys prevent the acquisition utility's immutable-manifest collision. These commands use the verified official direct-download URLs and the WPP attribution/licence metadata:

```fish
uv run python -m tools.acquire_wp1_5_sources \
  --source un_wpp_2024 \
  --release 2024-main-demographic \
  --url "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_Demographic_Indicators_Medium.csv.gz" \
  --filename WPP2024_Demographic_Indicators_Medium.csv.gz \
  --terms-url "https://population.un.org/wpp/" \
  --attribution "United Nations, Department of Economic and Social Affairs, Population Division (2024). World Population Prospects 2024, Online Edition." \
  --license-status "CC BY 3.0 IGO"

uv run python -m tools.acquire_wp1_5_sources \
  --source un_wpp_2024 \
  --release 2024-main-age-sex \
  --url "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_PopulationByAge5GroupSex_Medium.csv.gz" \
  --filename WPP2024_PopulationByAge5GroupSex_Medium.csv.gz \
  --terms-url "https://population.un.org/wpp/" \
  --attribution "United Nations, Department of Economic and Social Affairs, Population Division (2024). World Population Prospects 2024, Online Edition." \
  --license-status "CC BY 3.0 IGO"

uv run python -m tools.acquire_wp1_5_sources \
  --source un_wpp_2024 \
  --release 2026-01-19-togo-update \
  --url "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/WPP2024_CSV_files_update.zip" \
  --filename WPP2024_CSV_files_update.zip \
  --terms-url "https://population.un.org/wpp/" \
  --attribution "United Nations, Department of Economic and Social Affairs, Population Division (2024). World Population Prospects 2024, Online Edition." \
  --license-status "CC BY 3.0 IGO"
```

After acquisition, inspect the captured CSV headers and the ZIP member list before adapter implementation. The base files are gzip-compressed CSVs; the interim update is a ZIP containing uncompressed CSV replacements. Do not extract or overwrite the captured ZIP. The adapter should read the ZIP member streams directly and select the matching `*_Update.csv` tables. The WPP catalogue states the update changes Togo only; apply those rows only to the Togo crosswalk entry.
