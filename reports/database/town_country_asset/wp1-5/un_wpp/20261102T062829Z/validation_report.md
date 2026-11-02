# WP1.5 validation: un_wpp

- Result: **WARNING**
- Candidate: `generated/un_wpp_2026_candidate_20261101`
- Database: `/home/hmnf/Projects/Python/TownAndCountry/data/canonical/town_country_asset.sqlite`
- Checked at: 2026-11-02T06:28:29.928120+00:00

## Checks

| Check | Status | Detail |
|---|---|---|
| snapshot_fingerprints | PASS | 6 immutable inputs verified |
| database_integrity | PASS | integrity_check=ok; foreign_key_check=0 |
| candidate_field_coverage | PASS | 199 countries; 1194 unique country-field rows; expected six fields per country |
| wpp_age_sex_population_semantics | PASS | age countries=199; max age-total delta=6.000; max age/sex delta=6.000; max sex-total delta=1.000 |
| canonical_database_value_parity | PASS | Compared 1194 candidate country-field records against import_id=2; mismatches=0 |
| togo_supplement_provenance_review | WARNING | Togo observations cite these source references: UN WPP 2024 2026-01-19-togo-update; https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/WPP2024_CSV_files_update.zip. Confirm each reference matches the actual source member supplying that field. |

## Exceptions

- Togo observations cite these source references: UN WPP 2024 2026-01-19-togo-update; https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/WPP2024_CSV_files_update.zip. Confirm each reference matches the actual source member supplying that field.
