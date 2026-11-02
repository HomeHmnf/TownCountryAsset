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
| 15 | gdp | IMF WEO primary | Not registered |
| 16 | gdp_per_capita | IMF WEO primary | Not registered |
| 18 | gdp_ppp | IMF WEO primary | Not registered |
| 20 | inflation | IMF WEO primary | Not registered |
| 21 | unemployment | IMF WEO primary | Not registered |

The current registry has no WDI download definitions, no indicator-code catalogue, and no WDI-specific acquisition/normalization adapter.

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
5. Verify indicator-level licensing/third-party notes and determine a reproducible WDI release/snapshot identity. The API's rolling dataset and `lastupdated` metadata must be captured with the immutable response snapshots.
6. Propose any registry and source-selection changes separately. Do not add WDI as a fallback or alter the approved 41-field policy merely because a similarly named series exists.
7. Only after review, implement immutable acquisition, provider-specific parsing, normalization, crosswalk validation, coverage reports and source semantic tests. Keep release validation, database application and release promotion as separate approval-gated operations.

## Current conclusion

WDI is a technically suitable candidate for comparative macroeconomic observations and already serves the registered density/area fields. The five economic series above are plausible matches to WP1.5 fields, but their presence in WDI does not establish policy compatibility. The next work item is a read-only coverage and IMF-comparability assessment; no WDI data has been acquired or imported as part of this review.


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

A read-only country-year comparison utility is now documented in [`imf-weo-wdi-comparison.md`](imf-weo-wdi-comparison.md) and implemented at `tools/compare_imf_weo_wdi.py`. It compares the five candidate economic indicators through the existing identity registry, using the fixed October 2026 IMF CSV and live WDI API observations. The WDI API is rolling rather than an immutable release. The comparison does not change source policy, acquire snapshots, create approvals, or write to the canonical database. Run `uv run python -m tools.compare_imf_weo_wdi` from the repository root after the IMF manual snapshot is present.
