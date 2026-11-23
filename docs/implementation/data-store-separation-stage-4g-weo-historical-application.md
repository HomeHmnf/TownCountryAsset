# Stage 4G — IMF WEO historical application

**Status:** importer and tests committed; owner-run validation pending. No canonical observations have been written by this implementation.

## Application contract

`tools/database/imf_weo_import.py` is the provider-specific adapter for the annual candidate produced by Stage 4F. The CLI wrapper is `tools/import_imf_weo_historical.py`.

The importer:

- Revalidates the candidate JSON, both CSV fingerprints, the raw October 2026 source checksum/byte count, the persistent identity registry path and the migration dependency.
- Validates every observation's indicator/field mapping, finite numeric value, source checksum, release, acquisition date and status. It rejects duplicate (game, indicator, year, vintage) keys.
- Includes the candidate observations, exception register, candidate summary, immutable raw CSV, identity registry, manual acquisition record and historical-table migration in the shared approval fingerprint.
- Creates a pending application proposal only in `--prepare`; it does not insert observations.
- Requires an explicit human decision with actor and note. `--apply` requires an approved application with an exact matching fingerprint.
- Requires each candidate `game_id` to exist already in canonical `countries`. If not, the error directs the owner to import the identity registry first; it does not create identities or change ISO assignment status.
- Inserts annual rows into `imf_weo_historical_observations`, not `current_statistics`.
- Preserves nullable source unit, reporting-year months, latest-actual metadata, acquisition date precision and `unclassified` status.
- Treats an exact existing row as unchanged and inserts missing rows; any same-key conflicting row aborts the transaction.
- Records the application event and validates SQLite integrity/foreign keys in the same transaction.
- Leaves `dataset_imports.import_status='candidate'`; applying an observation import does not approve the source release or change source-selection policy.

The unique observation key includes `source_version`, so a later WEO vintage can coexist with October 2026 observations.

## Owner validation

After syncing the branch, run:

```fish
uv run python -m pytest -v tests/test_imf_weo_historical_candidate.py tests/test_imf_weo_historical_import.py
uv run python -m compileall -q tools/database/imf_weo_import.py tools/import_imf_weo_historical.py
```

Use the candidate directory reported by Stage 4F (for the committed owner run: `reports/sources/imf-weo-historical-candidate/20261123T103749Z`).

First create a pending approval proposal:

```fish
uv run python -m tools.import_imf_weo_historical --candidate-dir reports/sources/imf-weo-historical-candidate/20261123T103749Z --prepare
```

Record the returned `approval_id`. Inspect the candidate rows and 47 identity/source exceptions before making the decision. If the proposal is approved, explicitly record the decision:

```fish
uv run python -m tools.import_imf_weo_historical --candidate-dir reports/sources/imf-weo-historical-candidate/20261123T103749Z --approval-id YOUR_APPROVAL_ID --decide approved --actor YOUR_REVIEW_ID --note "Reviewed October 2026 WEO historical candidate and exception register"
```

Then apply the exact approved artifact:

```fish
uv run python -m tools.import_imf_weo_historical --candidate-dir reports/sources/imf-weo-historical-candidate/20261123T103749Z --approval-id YOUR_APPROVAL_ID --apply
```

Do not run `--decide approved` or `--apply` until the owner has reviewed the candidate and deliberately authorized the exact artifact. A changed candidate/source/identity/migration file invalidates the fingerprint and requires a new approval.

## Expected owner verification

The preparation step also reports which candidate identities are already present in canonical `countries` and lists missing `game_id` values. Missing identities do not disqualify observations, but they must be registered through the existing identity workflow before application. The importer reports candidate, inserted and unchanged counts, distinct identities, import ID, approval state and database integrity. Owner verification should additionally query:

- Total rows and distinct `game_id` in `imf_weo_historical_observations` for the October 2026 source version.
- Per-indicator counts (expected candidate counts: NGDPD 9,329; NGDPDPC 9,190; PPPGDP 9,354; PCPIPCH 9,217; LUR 4,934).
- All rows have `value_status='unclassified'`; units remain nullable.
- Distinct years and identity counts match the candidate summary.
- `application_approvals.status='applied'` and its event ledger contains proposed/approved/applied.
- `dataset_imports.import_status='candidate'`.
- `PRAGMA integrity_check` returns `ok`; `PRAGMA foreign_key_check` returns no rows.

The 47 exception rows are not imported as observations. The importer deliberately does not create missing country identities; resolve missing canonical identity rows through the established identity-registry workflow without upgrading proposal or ISO status.
