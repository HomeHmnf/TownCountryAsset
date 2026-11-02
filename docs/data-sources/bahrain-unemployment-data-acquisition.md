# Bahrain annual unemployment data acquisition

## Purpose

Acquire the official Bahrain Open Data Portal dataset `03-unemployment-yearly` directly through its public Opendatasoft Explore API v2.1. This is the dataset titled **“Bahraini Unemployed (15 years and above) and the Unemployment Rate by Sex (Yearly)”**.

- Dataset page: https://data.gov.bh/explore/dataset/03-unemployment-yearly/
- API documentation: https://www.data.gov.bh/api-console/explore/v2.1/
- Dataset API page: https://data.gov.bh/explore/dataset/03-unemployment-yearly/api/
- Metadata endpoint: `https://data.gov.bh/api/explore/v2.1/catalog/datasets/03-unemployment-yearly`
- Records endpoint: `https://data.gov.bh/api/explore/v2.1/catalog/datasets/03-unemployment-yearly/records`

The portal's dataset description identifies the subject as Bahraini unemployed persons aged 15 and above and the unemployment rate by sex. Preserve the provider's original categories and values; do not assume that this is an all-resident unemployment measure.

## Run the acquisition

From the repository root, using Fish:

```fish
uv run python -m tools.sources.bahrain_unemployment
```

Optional HTTP timeout:

```fish
uv run python -m tools.sources.bahrain_unemployment --timeout 90
```

The adapter reads its endpoint and dataset identity from `config/data_sources.json`. It performs HTTPS GET requests only, retrieves the dataset metadata, fetches every records page (100 records per request by default), verifies pagination consistency and stores the original JSON response bytes. It does not require a manually downloaded CSV or an API key.

## Project storage

Each run creates a timestamped, immutable snapshot:

```text
raw_data/
└── sources/
    └── bahrain_open_data/
        └── unemployment_yearly/
            └── <UTC timestamp>/
                ├── dataset_metadata.json
                ├── records_page_0001.json
                └── ...

data_manifests/
└── sources/
    └── bahrain_open_data/
        └── unemployment_yearly/
            └── <UTC timestamp>.json
```

Raw source bytes are local and must not be committed. The manifest is intended to be retained and committed when the acquisition is accepted for project evidence. It records retrieval time, dataset processing timestamps where exposed by the API, record and page counts, endpoint URLs, content types, byte counts, SHA-256 checksums, attribution and terms references.

The adapter refuses to overwrite an existing timestamped snapshot. A later retrieval creates a new snapshot; it never replaces an earlier capture.

## After acquisition

1. Inspect the terminal summary and preserve the exact raw directory and manifest path.
2. Check that the dataset record count and page count are plausible for the current portal release.
3. Inspect the saved metadata and records to identify the exact field names and categories used for year, indicator, sex and value.
4. Reconcile male, female and total unemployment counts and rates independently. Do not derive total values from sex-specific rates.
5. Compare the official national series with every corresponding IMF WEO observation, retaining differences in definition, denominator, population coverage, reference period and vintage.
6. Record missing categories or years as missing; do not fill them from another source without explicit review.

The initial acquisition is raw evidence only. It does **not** parse or normalize observations, create an approval, write to SQLite, alter source-selection policy, promote a source release, or import WP1.5 field 21. IMF WEO remains the configured priority source while this Bahrain-specific reconciliation is in progress. WDI modelled and national estimates remain diagnostic comparators only.

## Source and reuse notes

The source is registered as `bahrain_open_data` in the central source registry. The portal FAQ describes free public access and reuse, but this project records the license classification conservatively as `public_domain_or_unverified`; retain the source attribution and check the portal's current terms before redistributing raw data outside this project.
