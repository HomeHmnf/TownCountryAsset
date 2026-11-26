# IMF WEO field 15 identity review compiler

**Status:** one-pass register compilation implemented; source identity decisions remain human-reviewed and owner approval remains separate.

## Purpose

The ten cumulative manual review batches are retained as an audit trail. The final Batch 10 register is the reviewed proposal input for a deterministic one-pass compilation. The compiler rebuilds one consolidated register from the original 196-row baseline and validates it against the source inventory, aggregate exclusion register, canonical identity registry, and the separately approved WBG crosswalk.

Run from the repository root:

```fish
uv run python tools/build_imf_weo_field15_identity_review.py
```

Default outputs:

- `reports/sources/imf-weo-field15-identity-review/20261126/field_15_identity_review_register_final.csv`
- `reports/sources/imf-weo-field15-identity-review/20261126/field_15_identity_review_register_final.verification.json`

The command refuses to overwrite either output. Use `--force` only after inspecting the existing outputs.

## Validation performed

The compiler checks:

- 210 unique source identities in the IMF field-15 inventory;
- 13 unique aggregate exclusions, all scoped to field 15 / NGDPD, accounting for 665 populated values;
- the separately owner-approved WBG mapping remains the only mapping in the IMF crosswalk;
- the review baseline contains exactly the 196 non-aggregate identities other than WBG;
- the Batch 10 seed covers those same 196 identities;
- immutable identity and triage columns have not changed between baseline and seed;
- every proposal has both the official IMF Appendix and UN M49 references;
- each proposed persistent `game_id` exists in the canonical registry and its English name matches;
- proposed M49 numeric codes are three-digit numeric strings;
- all 195 proposals remain pending explicit owner approval and have no approved game ID;
- KOS remains the only held identity, with no proposed game ID or M49 code.

The verification report records input and output hashes and confirms that no database, approval, registry, or crosswalk write occurred.

## Governance boundary

This is a deterministic compiler, not an identity decision engine. It does not infer mappings from names, ISO codes, registry source IDs, or record order. It does not assign or regenerate persistent game IDs. It does not approve mappings or modify the crosswalk, canonical registry, Project DB, or Game DB.

The Batch 10 register is the human-reviewed proposal seed. IMF and UN M49 evidence references and the M49 numeric values are carried forward from that review. This version does not download or parse live IMF/UN evidence; the evidence assessment and mapping proposals remain subject to independent human review. Automating live evidence retrieval and source-format reconciliation is a separate future enhancement and must not be represented as completed by this compiler.

## Tests

Run:

```fish
uv run --extra dev python -m pytest -q tests/test_imf_weo_field15_identity_review.py
```

The tests cover successful compilation, unknown registry targets, approval-state rejection, immutable-baseline protection, and the KOS hold.
