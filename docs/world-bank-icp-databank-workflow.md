# World Bank ICP DataBank saved-report and historical-data workflow

## Acquisition and source interpretation

The ICP-Annual-PPPs saved report is source `world_bank_icp`, dataset
`world_bank_icp_databank_saved_report`, DataBank cube 3869. Acquisition manifests
are timestamped captures of the saved report, not new provider release vintages.
The 2026-11-19 capture and the earlier capture each passed semantic validation;
their Data and Series Metadata CSVs had exact observation-key, identity and value
parity. Only the Data CSV is normalized as observations. The Series Metadata CSV
is retained as source evidence and supplies the trailing indicator definitions.

The selected scope is:

- Classification: `PPPGlob`, “Purchasing power parity (PPP) (US$ = 1)”.
- Years: 2017–2023 inclusive.
- Selected DataBank country dimension: 184 entries, including regional/world
  benchmark aggregates.
- Six series: 1000000, 9020000, 9100000, 9270000, 1501000 and 9250000.
- The source missing token is `..`. It is stored as `value=NULL`,
  `value_status='source_missing'`, and `missing_value_token='..'`. It is not
  converted to zero, not_applicable, or estimated, and is never imputed.

The selected series names and full descriptions are recorded in
`reports/sources/world-bank-icp/country-mapping-review/indicator_dictionary.json`.
The DataBank export does not provide a separate per-row currency field. The
classification states US$ = 1; the importer therefore records the source unit as
“PPP ratio (US$ = 1)” and does not invent country currency codes.

## Country identity mapping

The mapping review compares each distinct ICP Country Code with the generated
asset-country ISO3 identifier. Candidate persistent game IDs are reached only
when the asset's UN_A3 M49 identifier also joins the existing reviewed UN WPP
source crosswalk. That WPP crosswalk is source-specific; it is evidence for a
candidate, not an ICP approval.

The current report distinguishes:
- candidate ISO3 + M49 + WPP game-ID mappings (pending review);
- entities with an asset candidate but no approved WPP game-ID bridge;
- ambiguous identities;
- unmatched identities; and
- benchmark aggregates, which are not game countries and must not be mapped.

No mapping is approved automatically. Edit
`data/manual/source_crosswalks/world_bank_icp.json` only after checking the ICP
entity scope and persistent game identity. Change a mapping's
`review_status` from `pending` to `approved` only when the mapping has been
reviewed. Do not map benchmark aggregates to countries. The importer also checks
that every approved game ID exists in the canonical `countries` table.

The machine-readable and CSV review reports are under
`reports/sources/world-bank-icp/country-mapping-review/`.

## Historical storage

ICP history is stored in `icp_historical_observations`, not
`current_statistics`. Its natural key is
`(game_id, indicator_code, classification_code, observation_year)`.
Each row retains the source country code/name, indicator code/name, classification,
source unit, source report URL, export ID, retrieval timestamp and dataset import
foreign key. Observed numeric values and source-missing values are represented
explicitly. This allows all seven years and all six indicators to coexist without
overwriting a current statistic.

The schema migration is `migrations/005_icp_historical_observations.sql`.

## Commands (fish)

Build the country/indicator review from the latest capture (replace the manifest
path with the 2026-11-19 export ID if needed):

```fish
uv run python -m tools.process_world_bank_icp_history \
  --manifest data_manifests/sources/world_bank_icp/databank_exports/databank_20261119T075746677306Z.json \
  --build-review
```

Inspect the proposed historical import. This is read-only and reports eligible
coverage after explicit mapping approvals:

```fish
uv run python -m tools.process_world_bank_icp_history \
  --manifest data_manifests/sources/world_bank_icp/databank_exports/databank_20261119T075746677306Z.json \
  --dry-run
```

After reviewing and explicitly approving the country mappings in the crosswalk,
create a pending canonical application proposal:

```fish
uv run python -m tools.process_world_bank_icp_history \
  --manifest data_manifests/sources/world_bank_icp/databank_exports/databank_20261119T075746677306Z.json \
  --propose --approval-id icp-history-20261119-v1
```

Approve or reject the proposal through the existing project-wide approval gate:

```fish
uv run python -m tools.manage_database_applications approve \
  --approval-id icp-history-20261119-v1 \
  --actor project_owner \
  --note "Reviewed ICP country crosswalk, indicator definitions, 2017-2023 history and missing-value semantics"
```

Only then may the exact fingerprinted artifact be applied:

```fish
uv run python -m tools.process_world_bank_icp_history \
  --manifest data_manifests/sources/world_bank_icp/databank_exports/databank_20261119T075746677306Z.json \
  --apply --approval-id icp-history-20261119-v1
```

Any edit to the manifest, raw CSV, country crosswalk, asset identity evidence or
WPP crosswalk changes the fingerprint and requires a new proposal and approval.
The application is transactional; the approval is marked applied in the same
transaction as the historical observation inserts. It writes only the canonical
asset database, never the Project DB or Game DB. It does not populate
`current_statistics` or change source selection.

## Regression tests

```fish
uv run python -m pytest -v \
  tests/test_process_world_bank_icp_history.py \
  tests/test_validate_world_bank_icp_databank.py \
  tests/test_process_world_bank_icp_databank.py
```
