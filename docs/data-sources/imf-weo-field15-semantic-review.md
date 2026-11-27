# IMF WEO field 15 semantic status review

**Status:** source and candidate reconciliation audit passed; deterministic classification proposal builder and focused tests committed; local execution and owner review pending. No semantic statuses have been written to the Game DB.

## Scope and evidence

- Provider: IMF World Economic Outlook, October 2026.
- Indicator: `NGDPD.A` (annual nominal GDP), WP1.5 field 15.
- Raw CSV SHA-256: `a19b2bd65b050a91d593cb6bcfc77a303e6359e058f03c3c92cf5ad849cda74d`.
- Field-15 candidate: `reports/sources/imf-weo-field15-reviewed-candidate/656073575edb005a/candidate`.
- Candidate observations: 9,361 across 197 individual source codes and 197 persistent game identities.
- Aggregate exclusions: 13 series and 665 populated values, under the previously owner-approved dispositions.

The IMF WEO FAQ defines `Latest Actual Annual Data` as the year of the latest actual data, or zero when the entire series is estimated; years after that date are IMF staff estimates. The October 2026 Database Appendix states that slash-separated year labels denote fiscal/financial years, that WEO data generally refer to calendar years except for economies using fiscal years, and that the Country Data Documentation table records the latest actual annual data for national accounts. The raw CSV's 19 fiscal-year metadata values were reconciled against that appendix table; the ending-year interpretation agrees with the annual columns and the appendix entries.

Official evidence:

- IMF WEO FAQ: https://data.imf.org/en/Datasets/WEO/Frequently-Asked-Questions
- October 2026 WEO Database Appendix: https://data.imf.org/-/media/iData/External-Storage/Documents/C4182C5C54794FC48892DE8F6C74FF82/en/October-2026-WEO-Database-Appendix.pdf

## Owner-run read-only audit result — 2026-11-27

The owner ran a read-only audit against the raw CSV and reported:

| Measure | Result |
|---|---:|
| Individual annual series | 197 |
| Populated observations | 9,361 |
| Integer-metadata series | 178 |
| Fiscal-year metadata series | 19 |
| Fiscal-year observations | 861 |
| Proposed observed | 8,168 |
| Proposed estimated | 1,193 |
| Unresolved metadata series | 0 |
| Accounting check | PASS |
| Database writes | 0 |

For fiscal-year labels, the annual observation cutoff is the **ending year**: for example, `FY2024/25` maps to annual column 2025 and `FY2025/26` maps to 2026. The 19 fiscal series account for 861 observations. All 19 metadata labels and ending-year cutoffs were checked against the October 2026 Appendix's National Accounts / Latest Actual Annual Data country documentation. Examples include AFG `2024/25`, BGD `2025/26`, MMR `2021/22`, and NRU `2020/21`.

## Classification proposal

The proposal builder applies these rules only to field 15:

1. Integer `LATEST_ACTUAL_ANNUAL_DATA`: the integer year is the inclusive latest-actual cutoff.
2. Fiscal label `FYyyyy/yy`: parse and validate a consecutive fiscal-year span; use its ending year as the inclusive annual-column cutoff.
3. Metadata `0`: classify every populated observation in that series as `estimated`.
4. Blank or unrecognized metadata: leave that series unresolved and mark the run incomplete; do not infer a status.
5. A populated annual column later than the cutoff is `estimated`; a column at or before the cutoff is proposed as `observed`.
6. Do not infer `projected` from this metadata. The WEO FAQ describes years after the latest-actual cutoff as IMF staff estimates.

The 8,168 / 1,193 split is a **proposal**, not an owner approval. It does not imply that the Game DB has been updated.

## Reproducible builder

Run from the repository root:

```fish
uv run python tools/build_imf_weo_field15_semantic_review.py
```

The builder:

- verifies the raw source fingerprint and the candidate's source and observation fingerprints;
- requires a field-15-only candidate with 9,361 observations;
- reconciles all 197 raw individual source codes to the candidate;
- verifies each populated source value, year, latest-actual metadata and reporting-period metadata against the candidate;
- requires the 13 approved aggregate codes to be present in the raw source and keeps their 665 values outside the country candidate;
- writes a timestamped `classification_proposals.csv`, `summary.json` and `summary.md`;
- fails closed on duplicate keys, mismatches, malformed metadata or incomplete coverage.

Output directory:

`reports/sources/imf-weo-field15-semantic-review/<UTC timestamp>/`

This is a read-only proposal builder. It does not modify the source CSV, candidate, identity registry, crosswalk, Project DB, Game DB, approval ledger or dataset-import status. It creates no approval and performs no application.

## Tests

```fish
uv run --extra dev python -m pytest -q tests/test_imf_weo_field15_semantic_review.py
```

Tests cover integer cutoffs, zero/all-estimated metadata, fiscal-year ending-year parsing, malformed metadata, raw/candidate reconciliation, and rejection of candidate rows that are already classified.

## Remaining gate

1. Sync the branch and run the focused tests.
2. Run the read-only proposal builder and inspect the generated summary and proposal CSV.
3. Reconcile the generated counts to 8,168 observed and 1,193 estimated, with zero unresolved and exact 9,361-row coverage.
4. Owner-review the semantic rule and the full proposal artifact.
5. Only after explicit owner approval, design a separate guarded status-application workflow with exact artifact fingerprints, backup/preflight and independent post-write verification.

Do not alter the existing importer to accept classified candidate rows: its requirement that imported source observations remain `unclassified` is intentional. Do not write statuses to the canonical database or begin field 16 until the field-15 semantic and closeout gates are complete.
