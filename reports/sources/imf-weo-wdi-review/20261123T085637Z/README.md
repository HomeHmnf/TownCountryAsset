# IMF WEO–WDI consolidated review package

- Observation rows: 13310
- Project identities: 242
- Edge cases: 1511
- Upstream semantic matrix SHA-256: `b365d3f6fb2f3d1d52fbc0dda32658a5060c86b024ceebf7f4987c015eed7dde`
- Review register SHA-256: `9247bb20c7f3e4cfd51955ad8d5dcca57d1f805697947c0d642407bef2326691`

## Single review surface

`review_register.csv` is the authoritative decision surface. Enter each observation decision there using `approve`, `exclude`, `hold_for_evidence`, or `not_applicable`; record rationale in `review_note` and reviewer identity/time in the corresponding columns. Leave unsupported rows pending or explicitly held.

## Linked edge-case work queue

`edge_cases.csv` groups exceptions and links them to affected `review_row_id` values. It is a supporting work queue, not a second decision surface. Record final observation decisions only in `review_register.csv`.

## Required safeguards

- This package is review-only. It is not a normalized import artifact and creates no approval.
- Identity and semantic gates remain explicit; a source series or numerical match is not identity or semantic approval.
- Unknown actual/estimate/projection status remains unknown.
- Country-specific evidence is bounded to the years documented in the source assessments. Settled cases are not reopened without new evidence.
- If the upstream semantic matrix changes, regenerate the package and re-review; do not transplant decisions by row position.
- After review, a separate validated builder must produce the exact normalized application artifact and dependencies for shared approval.

## Counts by field

| Field | Review rows |
|---:|---:|
| 15 | 2662 |
| 16 | 2662 |
| 18 | 2662 |
| 20 | 2662 |
| 21 | 2662 |

## Edge cases by category

| Category | Cases |
|---|---:|
| comparison_status | 996 |
| country_case | 15 |
| field_semantics | 5 |
| identity | 242 |
| observation_status | 253 |
