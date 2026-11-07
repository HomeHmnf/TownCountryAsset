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
