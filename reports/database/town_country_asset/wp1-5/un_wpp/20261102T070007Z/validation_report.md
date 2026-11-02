# WP1.5 validation: un_wpp

- Result: **PASS**
- Candidate: `generated/un_wpp_2026_candidate_20261101`
- Database: `/home/hmnf/Projects/Python/TownAndCountry/data/canonical/town_country_asset.sqlite`
- Checked at: 2026-11-02T07:00:07.871279+00:00

## Checks

| Check | Status | Detail |
|---|---|---|
| snapshot_fingerprints | PASS | 6 immutable inputs verified |
| database_integrity | PASS | integrity_check=ok; foreign_key_check=0 |
| candidate_field_coverage | PASS | 199 countries; 1194 unique country-field rows; expected six fields per country |
| wpp_age_sex_population_semantics | PASS | age countries=199; max age-total delta=6.000; max age/sex delta=6.000; max sex-total delta=1.000 |
| canonical_database_value_parity | PASS | Compared 1194 candidate country-field records against import_id=2; mismatches=0 |
| togo_supplement_provenance | PASS | The Togo archive contains both source members used by the adapter: demographic indicators (fields 1, 2, 6, 13, 14) and age-sex data (field 12); all six Togo observations cite the archive. |
| source_selection_resolver_compatibility | PASS | scalar resolutions=796; structured record/subfield resolutions=4577; mismatches=0; release eligibility simulated in memory only; no promotion. |

## Exceptions

None.
