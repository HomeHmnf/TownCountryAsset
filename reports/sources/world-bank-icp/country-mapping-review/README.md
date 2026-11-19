# ICP country identity mapping review

- Export: databank_20261109T180637192513Z
- Distinct ICP country codes: 184
- Candidate persistent game-ID mappings: 155 (all pending)
- Exact ISO3 asset matches: 171
- Manual review required: 16
- Ambiguous identities: 0
- Benchmark aggregates: 8
- Unmatched identities: 5
- Approved mappings: 0

Candidates join ICP ISO3 to generated asset ISO3 and then asset UN_A3 M49 to the reviewed WPP crosswalk. The WPP approval is source-specific and does not approve ICP mappings. All candidate mappings remain pending. Benchmark aggregates are excluded from country mapping.

Indicator descriptions and missingness are recorded in indicator_dictionary.json. Classification is PPPGlob, years are 2017–2023, and source token .. remains source_missing; no imputation is permitted.


The checked-in report was generated from tracked source files; the local canonical SQLite country registry was not available to the repository review. Its canonical_registry_verified_matches count is therefore null, not zero. Run the workflow's `--build-review` command in the working checkout to add a read-only comparison against verified ISO alpha-3 assignments and approved country records. All resulting ICP mappings remain pending.


## Data and missing-value inspection

- 1,288 country-year rows (184 selected country entries × 7 years) and 7,728 long-form indicator cells.
- Years 2017–2023; classification PPPGlob.
- Data CSV: UTF-8; Series Metadata CSV: Windows-1252. Raw bytes remain unchanged.
- Source missing token `..`: 2,258 cells; 5,470 numeric cells. Missing counts by indicator: GDP 96; AIC 425; household/NPISH final consumption 411; general-government final consumption 442; gross fixed capital formation 442; domestic absorption 442.
- The DataBank report has no separate per-row currency field. Preserve the PPP (US$ = 1) source classification; do not infer national currency codes.
