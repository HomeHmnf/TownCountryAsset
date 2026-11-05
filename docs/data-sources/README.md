# Data sources documentation index

This section documents providers, acquisition, source-specific validation, release provenance, data comparability and source-selection decisions.

## Project-wide source governance

- [Source management](source-management.md) — central registry, acquisition/storage conventions, manifests, licenses and commands.
- [Source selection](source-selection.md) — priority/fallback/custom-mixture policy and resolution rules.
- [WP1.5 source coverage](wp1-5-sources.md) — the 41 selected data fields and provider coverage.
- [World Bank WDI onboarding review](world-bank-wdi-onboarding-review.md) — indicator coverage and onboarding assessment.
- [IMF WEO October 2026 manual acquisition](imf-weo-october-2026-manual-acquisition.md) — immutable export provenance and metadata.
- [IMF WEO coverage assessment](imf-weo-coverage-assessment.md) — series coverage and code assessment.
- [UN WPP crosswalk review](un-wpp-crosswalk-review.md) — reviewed M49-to-project identity mapping.

## Provider acquisition and validation

- [Bahrain unemployment data acquisition](bahrain-unemployment-data-acquisition.md) — official API acquisition and immutable snapshots.
- [ICASEES Central African Republic national accounts](icasees-central-african-republic-national-accounts.md) — official publications, workbook/PDF inventory, GDP scale resolution and WEO cross-check.

## Comparability investigations

- [IMF WEO–WDI comparison](imf-weo-wdi-comparison.md) — shared country-year comparison method and diagnostic constraints.
- [Field 15/16 GDP comparability](field-15-16-gdp-comparability-assessment.md) — nominal GDP and GDP per capita.
- [Field 18 PPP GDP comparability](field-18-ppp-gdp-comparability-assessment.md) — PPP GDP and ICP methodology.
- [Field 20 inflation comparability](field-20-inflation-comparability-assessment.md) — annual-average, fiscal-year and calendar-year issues.
- [Field 21 unemployment comparability](field-21-unemployment-comparability-assessment.md) — modeled versus national estimates and country definitions.
- [Bahrain unemployment series assessment](bahrain-unemployment-series-assessment.md) — country-level evidence and reference-period interpretation.

## Document boundaries

- The registry in config/data_sources.json is the source identity authority; these documents explain it but do not replace it.
- Acquisition documents describe how bytes were obtained. Assessment documents describe what data mean and whether comparisons are valid.
- Comparability findings do not themselves change source policy, create overrides, approve releases or write to the canonical database.
- Provider-specific documents link to shared source-management and source-selection rules rather than restating them.
