# IMF WEO field 15 semantic status review

**Status:** deterministic semantic proposal build, post-fix tests and complete proposal CSV audit passed on 2026-11-27. The 9,361-row proposal is ready for explicit owner semantic review; approval and any subsequent application remain pending. No semantic statuses have been written to the Game DB.

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

**Post-fix owner-run result — 2026-11-27:** `uv run --extra dev python -m pytest -q tests/test_imf_weo_field15_semantic_review.py` returned **12 passed in 0.03s**. This confirms the fiscal-pattern correction in `ec38d21` and the focused regression suite.

## Owner-run build result — 2026-11-27

The owner ran `tools/build_imf_weo_field15_semantic_review.py` twice. Both executions returned the same complete result and wrote no database rows or approvals:

- Output: `reports/sources/imf-weo-field15-semantic-review/20261127T152134Z/`
- Raw source SHA-256: `a19b2bd65b050a91d593cb6bcfc77a303e6359e058f03c3c92cf5ad849cda74d`
- Candidate observations SHA-256: `8f2c2dccfb3263d67544e6772ad2fe3acb47885040967db3a22feb560ed48365`
- Proposal CSV SHA-256: `28e8b9c1afd983e429a8a8f6ca37d97ee3f14fa4eb4455b7a512f524f6424006`
- 197 individual series; 13 aggregate series / 665 populated aggregate values explicitly excluded.
- 9,361 candidate observations and 9,361 proposed classifications.
- 8,168 proposed `observed`; 1,193 proposed `estimated`.
- 178 integer-metadata series; 19 fiscal-year-ending-year series.
- Zero unresolved series; zero proposed `projected` values.
- `complete=true`, `database_written=false`, `approval_created=false`.

The generated `summary.json`, `summary.md` and `classification_proposals.csv` were committed in repository commit `7e064a4`. The identical second build confirms deterministic output for the recorded source and candidate fingerprints. The proposal was subsequently approved by the project owner as recorded in `owner_semantic_approval.md`; no semantic status application has been performed.

### Complete proposal CSV audit — 2026-11-27

The owner ran a read-only audit over the complete committed `classification_proposals.csv` and reported **PASS**:

- Proposal SHA-256 exactly matches `summary.json`: `28e8b9c1afd983e429a8a8f6ca37d97ee3f14fa4eb4455b7a512f524f6424006`.
- 9,361 rows and 9,361 unique `(source_country_code, observation_year)` keys.
- 197 distinct source series; year range 1980–2031.
- Status counts exactly 8,168 `observed` and 1,193 `estimated`.
- Rule counts exactly 178 `integer_latest_actual_year` series and 19 `fiscal_year_ending_year` series.
- Every proposed status agrees with its recorded cutoff; every current status remains `unclassified`.

The audit validates proposal-file integrity, uniqueness, coverage and internal cutoff consistency. The separate owner decision below supplies semantic approval; neither the audit nor the approval record changes the database.

## Owner semantic approval — 2026-11-27

The project owner explicitly approved the classification convention and exact proposal artifact. The immutable decision record is:

`reports/sources/imf-weo-field15-semantic-review/20261127T152134Z/owner_semantic_approval.md`

- Decision: **APPROVED**.
- Scope: WP1.5 field 15 only, IMF WEO October 2026 `NGDPD.A`.
- Proposal SHA-256: `28e8b9c1afd983e429a8a8f6ca37d97ee3f14fa4eb4455b7a512f524f6424006`.
- Approved counts: 8,168 `observed`; 1,193 `estimated`.
- The approved convention is exactly the five-rule policy above; no `projected` values are inferred.

This is semantic approval, **not authorization to write the statuses**. No database rows were changed by this decision. The existing field-15 observation rows remain `unclassified`.

## Remaining gate

1. Implement and test a separate guarded application path bound to the exact approved proposal and owner-approval record.
2. Run read-only application preflight against the current Game DB and a fresh, independently verified backup. The preflight must prove all 9,361 target rows match the approved proposal and remain `unclassified`.
3. Obtain explicit authorization for the actual status write. Apply transactionally, recording an application approval/event, and verify all 9,361 statuses, checksums, SQLite integrity and foreign keys independently.
4. Complete field-15 closeout documentation and all remaining field-level checks before beginning field 16.

Do not alter the existing importer to accept classified candidate rows: its requirement that imported source observations remain `unclassified` is intentional. Field 16 remains blocked.
