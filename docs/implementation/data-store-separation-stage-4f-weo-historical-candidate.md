# IMF WEO annual historical candidate and storage

**Status:** first implementation committed; owner-run validation pending.  
**Scope:** source-faithful normalization of the October 2026 IMF WEO annual values for WP1.5 fields 15, 16, 18, 20 and 21. This stage creates a candidate only; it does not write the canonical database or create an approval.

## Design decision

The existing `current_statistics` table is deliberately one-current-value-per-country/field and only accepts `observed`, `estimated`, `projected`, `unavailable` and `not_applicable`. The October 2026 WEO file contains a multi-year annual series, and its `LATEST_ACTUAL_ANNUAL_DATA` column is series-level metadata, not a reliable classification for every annual cell. Field 21 also has a blank source unit. Therefore, forcing all annual rows into `current_statistics` would lose history or require invented statuses/units.

Migration `008_imf_weo_historical_observations.sql` adds a dedicated annual table. It preserves the original numeric value, source unit and scale, reporting-year months, latest-actual metadata, release/checksum, source country code/name and persistent `game_id`. The table permits `unclassified` and nullable unit. It does not alter country identity or ISO assignment status.

## Candidate builder

`tools/build_imf_weo_historical_candidate.py`:

- Reads the existing immutable October 2026 CSV; verifies the recorded SHA-256 and byte count by default.
- Selects only the five approved WEO indicator codes and annual-frequency series.
- Maps source codes through the existing identity registry to an existing persistent `game_id`; does not verify/promote ISO assignments.
- Emits one candidate row for each finite, populated annual source cell.
- Leaves blank cells absent; records non-numeric tokens and identity exceptions separately.
- Retains missing field-21 unit as null; does not infer percent.
- Sets every row to `unclassified`; retains `LATEST_ACTUAL_ANNUAL_DATA` as metadata only.
- Does not use WDI values or comparability decisions to decide WEO observation eligibility.
- Writes `observations.csv`, `identity_exceptions.csv` and fingerprinted `candidate.json`.

Run from the repository root:

```fish
uv run python -m tools.build_imf_weo_historical_candidate
uv run python -m pytest -v tests/test_imf_weo_historical_candidate.py
uv run python -m compileall -q tools/build_imf_weo_historical_candidate.py
```

Optional paths: `--csv`, `--identity-registry`, `--output-root`. The recorded-snapshot check may only be bypassed for isolated tests using `--skip-snapshot-check`; do not use that option for the October 2026 production candidate.

## Acquisition-time precision

The formal IMF WEO acquisition record confirms the download date (2026-11-02), not an exact acquisition timestamp. The candidate records `acquired_on=2026-11-02` and `acquisition_time_precision=day`; it does not fabricate a timestamp. The official dataset page is retained as the source reference.

## Governance and next gate

This is not an application artifact and no data has been inserted. The annual-table migration and candidate normalizer require owner-run tests. Next implementation step is a dedicated approval-gated, transactional WEO historical importer that fingerprints the candidate, source bytes, identity registry and migration/schema dependencies; checks existing observation keys for idempotent replay; writes only after the shared approval engine confirms the exact artifact; and records `unclassified` status and nullable units without changing identity records or dataset release policy. WEO historical rows remain source observations, not a claim of WDI comparability or release promotion.
