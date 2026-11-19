# World Bank ICP DataBank saved-report workflow

## Scope and identity

The ICP-Annual-PPPs DataBank saved report is registered as the distinct source
`world_bank_icp` and dataset `world_bank_icp_databank_saved_report`. A saved-report
capture is a timestamped acquisition event, not a new provider-declared ICP release
vintage.

Each acquisition retains three artifacts:

- the original DataBank ZIP archive;
- the extracted `*_Data.csv`, which is the canonical observation representation;
- the extracted Series Metadata CSV, which repeats the observations and adds a
  trailing indicator-code dictionary.

Do not append both CSVs as observations. They contain the same observation keys and
indicator values. The metadata CSV is supporting evidence and a parity check.

## Validation contract

`tools.validate_world_bank_icp_databank` verifies:

- manifest-referenced artifact byte counts and SHA-256 hashes;
- ZIP CRC integrity and exact byte identity between archive members and extracted CSVs;
- the selected Country, Classification, Series and Time members recorded in the manifest;
- indicator columns matching the selected Series members;
- a complete Country × Classification × Time observation cross-product;
- unique `(classification_code, time_code, country_code)` keys;
- numeric finite values or the source missing-value token `..`;
- exact observation-key, dimension-field and indicator-value parity between the two CSVs;
- the Series Metadata CSV's trailing indicator-code dictionary;
- strict UTF-8 decoding with Windows-1252 fallback, without changing source bytes.

The validator writes a timestamped report under
`reports/sources/world-bank-icp/`. It does not write either database.

## Commands

Validate the known 19 November 2026 capture:

```fish
uv run python -m tools.validate_world_bank_icp_databank \
  --manifest data_manifests/sources/world_bank_icp/databank_exports/databank_20261119T075746677306Z.json
```

Run the full gated workflow in preflight mode. This audits and semantically validates
every manifest in the ICP DataBank manifest directory, synchronizes the Project DB
source/dataset catalogues, and performs a dry-run acquisition-registration preflight:

```fish
uv run python -m tools.process_world_bank_icp_databank
```

Only after the preflight reports `ready_for_registration`, register acquisition and
artifact provenance in the Project SQLite database:

```fish
uv run python -m tools.process_world_bank_icp_databank --register
```

The `--register` flag does not import statistical observations. The Project DB
records the acquisition event, manifest evidence and artifact provenance. The Game
DB is not opened or changed.

To produce the existing normalized long-form inspection outputs after validation:

```fish
uv run python -m tools.assess_world_bank_icp_exports
```

## Database and approval boundary

Catalogue synchronization and acquisition registration are provenance operations.
They do not establish that the observations are semantically approved for canonical
use. Observation normalization, statistical interpretation, source selection,
approval, retention promotion and Game DB application remain separate governed
steps. In particular, missing values remain missing; no imputation, interpolation,
extrapolation or carry-forward is authorized by this workflow.

## Regression tests

```fish
uv run python -m pytest -v \
  tests/test_validate_world_bank_icp_databank.py \
  tests/test_process_world_bank_icp_databank.py \
  tests/test_world_bank_icp_databank.py
```
