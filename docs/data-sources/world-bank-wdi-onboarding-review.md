# World Bank WDI onboarding review

**Status:** initial source assessment; not an acquisition, policy change, approval, or import  
**Reviewed:** 2026-11-02  
**Source ID:** `world_bank_wdi`  
**Provider:** World Bank World Development Indicators (WDI)

## Decision boundary

This review records the currently registered WDI scope and candidate economic indicators. It does not change `config/data_sources.json`, `config/source_selection.json`, release eligibility, normalized observations, or canonical SQLite.

WDI is already registered for WP1.5 fields 3 (population density), 33 (total area), and 34 (land area). Fields 15 (GDP), 16 (GDP per capita), 18 (GDP PPP), 20 (inflation), and 21 (unemployment) currently designate `imf_weo` as their priority source. WDI must not be used for those fields unless a separately reviewed policy change explicitly assigns it as a fallback or primary source.

## Provider and access

The World Bank Indicators API v2 provides programmatic access to WDI and other World Bank databases. API keys are not required. Responses can include indicator metadata (code, name, unit, source note, source organization), and data requests support date ranges, multiple indicators, JSON responses, and pagination.

- API documentation: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
- Basic API call structures: https://datahelpdesk.worldbank.org/knowledgebase/articles/898581
- Indicator API queries: https://datahelpdesk.worldbank.org/knowledgebase/articles/898599
- WDI dataset catalog: https://datacatalog.worldbank.org/infrastructure-data/search/dataset/0037712/world-development-indicators

The WDI catalog describes annual national data with a displayed temporal coverage of 1960–2025. This is dataset-level coverage only; it does not establish that every indicator has observations for every year or every project identity. Per-indicator and per-country coverage must be measured from acquired responses.

## Current registered scope

| WP1.5 field | Field key | Current policy assignment | Current WDI registration |
|---:|---|---|---|
| 3 | population_density | WDI primary; derived fallback only under aligned-period/definition rules | Registered |
| 33 | total_area | WDI primary | Registered |
| 34 | land_area | WDI primary | Registered |
| 15 | gdp | IMF WEO primary | Registered for immutable diagnostic comparison only |
| 16 | gdp_per_capita | IMF WEO primary | Registered for immutable diagnostic comparison only |
| 18 | gdp_ppp | IMF WEO primary | Registered for immutable diagnostic comparison only |
| 20 | inflation | IMF WEO primary | Registered for immutable diagnostic comparison only |
| 21 | unemployment | IMF WEO primary | Registered for immutable diagnostic comparison only |

The Project DB catalogue now registers a bounded six-indicator diagnostic dataset and a rolling API snapshot stream. The snapshot adapter preserves raw response bytes and metadata; it does not normalize or approve observations. Existing WDI fields 3, 33 and 34 remain separately registered, and source-selection policy is unchanged.

## Candidate economic indicators

The following WDI indicator metadata was checked through the official v2 indicator API on 2026-11-02. These are candidates for comparative assessment only, not approved replacements or fallbacks.

| Field | WDI indicator | Provider label | Canonical interpretation / caveat |
|---:|---|---|---|
| 15 GDP | `NY.GDP.MKTP.CD` | GDP (current US$) | Current-price US dollars; nominal, not inflation-adjusted. |
| 16 GDP per capita | `NY.GDP.PCAP.CD` | GDP per capita (current US$) | Current-price US dollars per person; retain the WDI population denominator and source vintage. |
| 18 GDP PPP | `NY.GDP.MKTP.PP.CD` | GDP, PPP (current international $) | Current international dollars. The series note describes linked time series and warns that historical values may not be comparable with other national-accounts series in the database. |
| 20 Inflation | `FP.CPI.TOTL.ZG` | Inflation, consumer prices (annual %) | Annual percentage change in consumer prices; originating source is IMF International Financial Statistics. Confirm comparability with the project's intended annual-average/end-period convention. |
| 21 Unemployment | `SL.UEM.TOTL.ZS` | Unemployment, total (% of total labour force) (modeled ILO estimate) | ILO modelled estimate. Do not treat as automatically equivalent to an IMF WEO unemployment series without definition, coverage, vintage and status comparison. |

Official API metadata endpoints:

- https://api.worldbank.org/v2/indicator/NY.GDP.MKTP.CD?format=json
- https://api.worldbank.org/v2/indicator/NY.GDP.PCAP.CD?format=json
- https://api.worldbank.org/v2/indicator/NY.GDP.MKTP.PP.CD?format=json
- https://api.worldbank.org/v2/indicator/FP.CPI.TOTL.ZG?format=json
- https://api.worldbank.org/v2/indicator/SL.UEM.TOTL.ZS?format=json

WDI publishes indicators compiled from multiple originating organizations. Retain both the WDI series identity and its indicator-level source organization/note; WDI publication does not mean every observation was produced by the World Bank.

## Licensing and attribution

The WDI dataset catalog currently classifies the dataset as Public and lists Creative Commons Attribution 4.0. World Bank dataset terms state that CC BY 4.0 is the default unless a dataset or indicator is specifically labelled otherwise. Indicator-level exceptions and third-party source restrictions must still be checked and preserved.

- WDI catalog and license: https://datacatalog.worldbank.org/infrastructure-data/search/dataset/0037712/world-development-indicators
- World Bank data licensing: https://datacatalog.worldbank.org/public-licenses
- Dataset terms: https://www.worldbank.org/ext/en/legal/terms-conditions/datasets

Proposed attribution pending confirmation against the acquired release metadata: World Bank, World Development Indicators. Include indicator-level originating organizations and any applicable third-party notices. Do not mark the entire source as unconditionally open if a particular series carries different terms.

## Required next assessment

Before adding downloads or an adapter:

1. Retrieve metadata for the five candidate indicators and the three currently registered WDI fields, including source notes, source organization, units, topics and metadata timestamps.
2. Query annual observations over the intended project period and compute per-indicator coverage by ISO3 and by the reviewed game-identity crosswalk. Separate countries from regional/income aggregates.
3. Record the actual latest non-null observation year per country and indicator. Do not use an API most-recent-value shortcut that silently mixes years as if they were one common reference period.
4. Compare definitions and periods with IMF WEO for fields 15, 16, 18, 20 and 21. Identify actuals versus estimates, currency/PPP basis, inflation convention, unemployment methodology and release-vintage differences.
5. Verify indicator-level licensing/third-party notes. The new snapshot adapter records API last-updated metadata and exact response fingerprints, but the capture remains a timestamped rolling API snapshot rather than a provider-declared vintage.
6. Propose any registry and source-selection changes separately. Do not add WDI as a fallback or alter the approved 41-field policy merely because a similarly named series exists.
7. Run the implemented immutable-response capture and owner-side integrity/registration checks. Then complete provider-specific semantic validation, normalization and identity crosswalk review. Keep release validation, database application and release promotion as separate approval-gated operations.

## Current conclusion

WDI is a technically suitable candidate for comparative macroeconomic observations and already serves the registered density/area fields. The five economic series remain plausible comparands, not approved fallbacks. A byte-preserving snapshot acquisition tool and Project DB dataset/stream registration are now implemented; owner-run capture, manifest audit, provenance registration and frozen comparison remain pending. No WDI observation has been semantically approved or imported into the Game DB.


## Read-only coverage assessment implementation

The first assessment utility is implemented at `tools/assess_world_bank_wdi.py`.

Run it with:

```fish
uv run python -m tools.assess_world_bank_wdi
```

Optional period override:

```fish
uv run python -m tools.assess_world_bank_wdi --start-year 2015 --end-year 2025
```

The utility retrieves metadata and paginated annual observations for the five economic candidates and the three currently registered WDI indicators. It excludes World Bank aggregate regions from country coverage, records non-null observation years by ISO3, preserves indicator source notes and originating organizations, and writes JSON, Markdown and country-level CSV reports under `reports/sources/world-bank-wdi/<timestamp>/`.

This is an online, read-only assessment, not immutable acquisition. It does not write raw snapshots, acquisition manifests, the source registry, the source-selection policy, release ledgers, or SQLite. It deliberately marks IMF WEO comparability as `not_assessed` until a versioned IMF comparison dataset is available. ISO3 coverage is not treated as a game identity crosswalk.

Automated tests: `tests/test_world_bank_wdi_assessment.py`.


## IMF WEO comparative assessment

A read-only country-year comparison utility is documented in imf-weo-wdi-comparison.md and implemented at tools/compare_imf_weo_wdi.py. It compares the five candidate economic indicators through the existing identity registry, with the national unemployment estimate retained as separate diagnostic context. It supports both live WDI API exploration and an integrity-checked immutable response bundle through --wdi-snapshot-manifest. Use the snapshot mode for decision-grade comparison evidence; it does not change source policy, create approvals, or write to the Game DB.


## Immutable API snapshot acquisition

The capture and snapshot-backed comparison workflow is implemented in [World Bank WDI immutable API snapshot acquisition](world-bank-wdi-snapshot-acquisition.md). It captures source and country metadata, metadata for five primary comparison indicators plus the field-21 national-estimate diagnostic, and all observation pages for 2015–2025. Raw response bytes are stored locally; tracked manifests carry per-response SHA-256, byte count, request URL/parameters, response headers and pagination metadata.

The source and dataset catalogues now register this as a rolling API snapshot stream. It is not a provider-declared WDI vintage, not a semantic approval, and not a source-selection change. Run the snapshot command, audit the manifest, register provenance in the Project DB, then pass the manifest to the comparison tool with --wdi-snapshot-manifest. Licensing remains marked unclear_or_unverified until indicator-level third-party restrictions are checked.
