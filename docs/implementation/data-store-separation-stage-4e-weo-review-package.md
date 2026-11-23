# IMF WEO–WDI consolidated review package builder

**Status:** implementation added; owner-run validation pending.  
**Purpose:** turn the completed Stage 4C semantic matrix into one observation-level review package and a linked edge-case work queue.

## Outputs

`tools/build_imf_weo_wdi_review_package.py` creates a timestamped package containing:

- `review_register.csv`: the single authoritative review/decision surface, one row per persistent identity × field × year. Each row has a stable review ID, linked edge-case IDs, pending decision, rationale and reviewer metadata columns.
- `edge_cases.csv`: grouped identity, field-semantic, country-case and observation/comparison-status issues, linked to the affected review-row IDs. This is a work queue only; decisions are recorded in the review register.
- `package.json`: row/case counts and SHA-256 fingerprints for the upstream semantic matrix and package outputs.
- `README.md`: review instructions, decision vocabulary and governance safeguards.

The builder rejects duplicate country/field/year keys. It does not alter source values, infer identities or status, create normalized application data, create approval records, change source policy or write either database.

## Run

Use the owner-generated Stage 4C semantic matrix:

```fish
uv run python -m tools.build_imf_weo_wdi_review_package \
  --input reports/sources/imf-wdi-semantic-disposition/20261107T145725Z/semantic_disposition_matrix.csv
```

Focused tests:

```fish
uv run --extra dev python -m pytest -v tests/test_imf_weo_wdi_review_package.py
uv run python -m compileall -q tools/build_imf_weo_wdi_review_package.py
```

Review decisions are made only in `review_register.csv`: `approve`, `exclude`, `hold_for_evidence` or `not_applicable`. A blank/pending decision is not approval. The upstream matrix and package hashes must be retained. If the candidate changes, regenerate and review again rather than carrying decisions by row position.

## Governance boundary

This package is not an application artifact. After decisions and edge cases are resolved, a separate validation/normalization step must construct the exact WP1.5 normalized observation artifact and crosswalk dependencies. That artifact then goes through the shared application-approval workflow before the existing transactional importer may write to the database. Owner-run tests and output inspection are still required.
