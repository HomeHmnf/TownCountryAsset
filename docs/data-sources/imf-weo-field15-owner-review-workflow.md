# IMF WEO field 15 owner review and application workflow

This workflow consolidates the ten automatically generated identity batches into one owner-review Markdown document. It is restricted to IMF WEO October 2026, field 15 / NGDPD.

## 1. Generate the review document

After syncing the branch and confirming the automatic source-derived package is present:

```fish
cd ~/Projects/Python/TownAndCountry
uv run python tools/manage_imf_weo_field15_review.py generate-review
```

The command creates:

`reports/sources/imf-weo-field15-identity-review/field_15_owner_review.md`

It refuses to overwrite an existing review file. It reads the automatic final identity register and aggregate exclusion register generated from the original IMF WEO source and official evidence. It does not read the historical manually prepared batch files or manual inventory/exclusion registers.

The document contains all 196 source identities in their original ten-batch sequence: 195 proposed mappings and the fixed KOS hold. It also records the already-approved WBG mapping and the 13 already-approved aggregate exclusions (665 populated values).

Generation is read-only with respect to both databases. It creates no application approval and does not change the original WBG crosswalk or canonical identity registry.

## 2. Review the single Markdown file

Review every proposal row. For each of the 195 new identity proposals:

- Set Decision to `APPROVE`, `EXCLUDE`, or `HOLD`.
- For `APPROVE`, copy the exact Proposed game_id into Approved game_id.
- For `EXCLUDE` or `HOLD`, leave Approved game_id as `-`.
- Enter a substantive Owner rationale for every decision.
- Do not change source IDs, source names, series, proposed game IDs, registry names, M49 codes, evidence references, or batch numbers.

The KOS row is prefilled as HOLD and must remain unmapped. WBG and the 13 aggregate exclusions are carried forward from their prior owner decisions; they are not re-proposed.

At the top of the document, complete:

- Owner actor — the approving identity.
- Approval date — actual date in YYYY-MM-DD format.
- Approval statement — explicit statement approving the completed field-15 decisions for application.

The approval statement is a human owner decision. Do not fill it until the full review is complete.

## 3. Validate the completed review

After editing the Markdown file:

```fish
uv run python tools/manage_imf_weo_field15_review.py validate-review --require-complete
```

Validation checks the complete 196-row / ten-batch structure, all 195 source-derived proposal identities, exact proposed targets, owner decisions and rationales, KOS hold, and every captured input fingerprint. It performs no database writes.

## 4. Explicitly approve, apply, and verify

Only after the Markdown review has been inspected and approved by the project owner, run:

```fish
uv run python tools/manage_imf_weo_field15_review.py apply-reviewed --actor "project-owner"
```

The `--actor` value must exactly match the Owner actor in the Markdown document. This is the sole write command. It:

1. Revalidates the Markdown decisions and immutable source fingerprints.
2. Creates a versioned, derived IMF WEO crosswalk containing the existing WBG mapping plus only the rows marked APPROVE. The original manual crosswalk is not modified.
3. Builds a deterministic field-15-only candidate from the original IMF WEO CSV. EXCLUDE and HOLD decisions remain explicit candidate exceptions; the 13 aggregate exclusions and KOS hold are preserved.
4. Uses the existing application-approval ledger. An identical pending approval is resumed; an identical approved approval is applied; an already-applied identical artifact is not applied twice. A different artifact cannot reuse an old approval.
5. Applies the approved candidate transactionally using the existing IMF WEO importer.
6. Independently compares imported observation keys, values, units, statuses and provenance against the candidate; checks the approval event history; runs SQLite integrity and foreign-key checks; and verifies Project DB acquisition ID 5.

The application is bound to the review document SHA-256 through the derived crosswalk, as well as the candidate, raw source, registry, migration and acquisition evidence. Any changed input invalidates the review/application fingerprint.

## 5. Safety and closure conditions

- The command is field 15 / NGDPD only. It cannot apply fields 16, 18, 20 or 21.
- The canonical identity registry and original manual WBG crosswalk remain unchanged.
- No identity is inferred from names, provider IDs or registry ISO fields at application time; only explicit owner-approved crosswalk entries resolve identities.
- WEO observation statuses remain `unclassified`. Technical import verification is not semantic classification or field-level semantic approval.
- The Project DB acquisition is checked, not rewritten or re-registered.
- A successful command is not sufficient to close field 15 until the owner inspects the verification report and the field's remaining semantic review requirements are satisfied.
- Do not begin field 16 until field 15 has been fully reviewed, approved, applied, independently verified in both databases, and documented.

## 6. Tests

```fish
uv run --extra dev python -m pytest -q tests/test_imf_weo_field15_identity_review.py tests/test_imf_weo_field15_review_workflow.py
```
