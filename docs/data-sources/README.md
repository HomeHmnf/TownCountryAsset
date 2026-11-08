# Data sources documentation index

This section documents providers, acquisition, source-specific validation, release provenance, data comparability and source-selection decisions.

## Project-wide source governance

- [Source management](source-management.md) — central registry, acquisition/storage conventions, manifests, licenses and commands.
- [Source selection](source-selection.md) — priority/fallback/custom-mixture policy and resolution rules.
- [WP1.5 source coverage](wp1-5-sources.md) — the 41 selected data fields and provider coverage.
- [World Bank WDI onboarding review](world-bank-wdi-onboarding-review.md) — indicator coverage and onboarding assessment.
- [World Bank WDI immutable API snapshot acquisition](world-bank-wdi-snapshot-acquisition.md) — byte-preserving capture, manifest integrity, Project DB provenance registration and snapshot-backed comparison.
- [IMF WEO October 2026 manual acquisition](imf-weo-october-2026-manual-acquisition.md) — immutable export provenance and metadata.
- [IMF WEO coverage assessment](imf-weo-coverage-assessment.md) — series coverage and code assessment.
- [UN WPP crosswalk review](un-wpp-crosswalk-review.md) — reviewed M49-to-project identity mapping.

## Provider acquisition and validation

- [Bahrain unemployment data acquisition](bahrain-unemployment-data-acquisition.md) — official API acquisition and immutable snapshots.
- [ICASEES Central African Republic national accounts](icasees-central-african-republic-national-accounts.md) — source entry point; its [dedicated index](icasees/README.md) separates acquisition, workbook structure and GDP reconciliation.
- [Guinea national-accounts vintage reconciliation](guinea-national-accounts-vintage-reconciliation.md) — legacy 1993 SNA versus 2018-base SNA 2008, WDI/IMF/UNSD comparison and source-acquisition targets.\n- [Guinea INS national-accounts acquisition](guinea-ins-national-accounts-acquisition.md) — repeatable official-PDF download, timestamped manifests, integrity audit and Project DB provenance registration.
- [Turkmenistan macroeconomic evidence acquisition](turkmenistan-macroeconomic-evidence-acquisition.md) — five IMF/TurkmenStat research and methodology publications, three verified captures, two documented IMF access gaps, and a guarded end-to-end Project DB provenance workflow.\n- [Turkmenistan GDP conversion-basis reconciliation](turkmenistan-gdp-conversion-reconciliation.md) — WDI/IMF WEO nominal-GDP arithmetic, official/DEC/parallel-rate distinctions, 2022–2023 residuals and national-accounts modernization evidence.

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
