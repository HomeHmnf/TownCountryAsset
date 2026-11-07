# IMF WEO–WDI semantic disposition matrix builder

**Status:** implementation committed; owner-run execution and validation pending  
**Branch:** work/compiler-hardening  
**Purpose:** enrich the complete candidate matrix with explicit, evidence-bounded semantic dispositions.

## Scope

`tools/build_imf_weo_wdi_semantic_disposition.py` reads an existing `candidate_matrix.csv` and writes three read-only review artifacts:

- `semantic_disposition_matrix.csv`: the original candidate rows plus identity, concept, period, methodology, source-status, country-case, field-gate and evidence-document columns;
- `assessment.json`: row counts and disposition summaries;
- `assessment.md`: field gates and the finite country-case register.

The tool does not fetch source data, recompute observations, alter values, promote identities, approve data, change source-selection policy, or write either database.

## Evidence-bounded rules

The matrix records the current field-level dispositions:

| Field | Disposition | Outstanding gate |
|---:|---|---|
| 15 | Qualified comparability | National-account vintage and USD conversion |
| 16 | Qualified comparability | GDP numerator and population denominator/universe |
| 18 | Not demonstrated comparable | ICP benchmark, PPP factor and nominal GDP input |
| 20 | Not demonstrated comparable | Annual-average convention and reference period |
| 21 | Non-equivalent products in general | IMF unit, population, reference period and method |

Country-specific evidence cases are explicitly attached for CAR, Guinea, Turkmenistan, Zimbabwe, Samoa, Tonga, Palau, Bahrain, Moldova and the Philippines. They point to the existing assessments; they do not claim that every year in a country-field series is resolved. Bahrain remains closed under its documented disposition.

All identities remain governed by the identity registry. A row with an identity status other than `mapped_verified` retains an identity-review gate. IMF latest-actual metadata remains a hint. Blank WDI observation status is not converted into actual, estimate or projection. Missing observations remain missing.

## Run

From the repository root, using the frozen 7 November comparison:

```fish
uv run python -m tools.build_imf_weo_wdi_semantic_disposition \
    --input reports/sources/imf-wdi-comparison/20261107T144614Z/candidate_matrix.csv
```

The default output root is `reports/sources/imf-wdi-semantic-disposition/`. The tool creates a new timestamped directory and does not overwrite prior reports.

Run focused tests:

```fish
uv run --extra dev python -m pytest -v \
    tests/test_imf_weo_wdi_semantic_disposition.py \
    tests/test_imf_weo_wdi_comparison.py \
    tests/test_world_bank_wdi_snapshot.py
```

The owner must run these commands locally and provide the output before this stage is marked validated. Review generated rows and summary counts, especially country-name matching and the identity gate, before treating the artifact as a decision input.

## Governance boundary

The generated matrix is a structured review aid, not a semantic approval artifact. It must not be used to change field source priorities, create country overrides, promote identities, retain/promote a release, or apply observations to the Game DB. Those actions remain separately approval-gated.


## Stage 4C.1 — year-bounded evidence and review queues

The builder now adds `year_evidence_scope` and `year_evidence_note` to each country–field–year row. Country cases no longer imply that their evidence applies to every year in 2015–2025. Explicit scope ranges are bounded to the supporting assessment:

- Bahrain field 21: official series covers 2016–2025; 2016 is a reference-period conflict and 2017–2025 exact official/WEO matches. 2015 remains outside the acquired official dataset. This is settled evidence and is not reopened.
- CAR fields 15/16: ICASEES definitive 2019–2021 accounts and pinned WEO cross-check; population denominator remains open for field 16. Other years remain context only. CAR PPP factor decomposition remains open.
- Guinea fields 15/16: 2018–2024 rebased national-accounts evidence; population denominator remains open for field 16. Other years remain context only. PPP factor decomposition remains open.
- Turkmenistan fields 15/16: alternative conversion-factor warning is explicitly scoped to 2019–2025; the 2018 divergence onset remains unexplained.
- Zimbabwe field 18: special IMF ICP-factor currency conversion evidence is scoped to 2017 only.
- Samoa field 20: fiscal-year correspondence evidence for 2021–2024; 2025 residual remains open.
- Tonga field 20: fiscal-year correspondence for 2022–2025, with CPI vintage still open.
- Palau field 20: fiscal-year correspondence for 2023–2025.
- Moldova field 21: NBS LFS corroboration for 2024–2025, retaining the redesign/break caveat.
- Philippines field 21: PSA annual LFS corroboration for 2023–2025, retaining 2025 preliminary status.

These scope labels are evidence classifications, not approvals and not a claim that each observation is directly interchangeable. The row retains its field-level semantic gate, source coverage, identity gate and observation-status uncertainty.

The report now also writes:
- `country_field_review_queue.csv` and `.json`: 242 × 5 country-field groups, with year-scope, coverage and status summaries;
- `field_review_summary.json`: five field-level gate summaries.

The queue is a review worklist, not a recommendation to change the selected source. Identity review remains a separate blocker for all 242 project identities. WDI actual/estimate status remains unclassified where the provider response does not explicitly supply it. No database, policy, approval or release state is changed.


## Stage 4C.2 — decision-readiness assessment

`tools/build_imf_weo_wdi_decision_readiness.py` consumes the year-scoped semantic matrix and produces a separate decision-readiness package:

- `decision_readiness.json` and `.md`: global gates, five field decisions, blockers and next evidence actions;
- `field_decision_queue.csv`: field-level readiness and current disposition;
- `country_case_decision_queue.csv`: country-field evidence cases and explicitly bounded years.

The current result is intentionally **not ready for source-policy change or canonical application**. All 242 identities remain review-required. The IMF October 2026 WEO input and timestamped WDI rolling-API capture are not provider-vintage aligned. Observation status is not complete: WDI status is unclassified in the capture, and IMF latest-actual metadata is not a projection classifier.

Field dispositions remain:
- Fields 15 and 16: qualified concept comparability, but national-account vintages/USD conversion and population denominator remain unresolved.
- Field 18: PPP benchmark/factor and nominal-GDP construction are not demonstrated comparable; WEO actual status/reporting period remain unclassified.
- Field 20: annual-average, fiscal/calendar-year and CPI-vintage alignment remain unresolved.
- Field 21: WDI ILO-modelled and national-estimate products remain distinct from country-specific WEO series; IMF unit/reference population/period need review.

The existing IMF WEO priority assignments remain unchanged. Country-specific corroboration is not promoted to a universal field equivalence or canonical override. Bahrain's settled 2016–2025 evidence is preserved and not reopened; other cases retain their bounded evidence ranges and stated caveats.

Run:
```fish
uv run --extra dev python -m pytest -v tests/test_imf_weo_wdi_decision_readiness.py
uv run python -m compileall -q tools/build_imf_weo_wdi_decision_readiness.py
uv run python -m tools.build_imf_weo_wdi_decision_readiness --input reports/sources/imf-wdi-semantic-disposition/<semantic-run>/semantic_disposition_matrix.csv
```

This is a read-only assessment. It creates no approval, changes no source-selection policy, promotes no release, and writes neither SQLite database.
