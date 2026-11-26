# IMF WEO field 15 owner review and application workflow

This workflow consolidates the ten automatically generated identity batches into one owner-review Markdown document. It is restricted to IMF WEO October 2026, field 15 / NGDPD.

## 1. Generate the review document

After syncing the branch and confirming the automatic source-derived package is present:

```fish
cd ~/Projects/Python/TownAndCountry
uv run python tools/manage_imf_weo_field15_review.py generate-review
```

The command creates:

`reports/sources/imf-weo-field15-identity-review/field_15_owner_review_kos_approved.md`

It refuses to overwrite an existing review file. It reads the automatic final identity register and aggregate exclusion register generated from the original IMF WEO source and official evidence. It does not read the historical manually prepared batch files or manual inventory/exclusion registers.

The new document contains all 195 proposals in ten batches. WBG and KOS are separately owner-approved fixed crosswalk mappings and are not new proposal rows. The earlier `field_15_owner_review.md` is retained as a historical review artifact; it is not the active review because it predates the KOS approval. It also records the already-approved WBG mapping and the 13 already-approved aggregate exclusions (665 populated values).

Generation is read-only with respect to both databases. It creates no application approval and does not change the owner-approved IMF WEO crosswalk or canonical identity registry.

## 2. Review the single Markdown file

Do not edit 195 table rows manually. The bulk approval command below creates a separate, immutable approval copy, marks all 195 new proposals APPROVE, copies each proposed game_id into its approved field, and records the owner's decision note on every row. WBG and KOS remain fixed, previously owner-approved mappings.

WBG and KOS are reused from their prior owner decisions, and the 13 aggregate exclusions are reused from their prior owner decision. KOS maps to the existing Kosovo game_id through an explicit IMF WEO field-15-only reviewed-manual crosswalk; the IMF Appendix KOS/UVK discrepancy is documented and does not change ISO/M49 assignments. The command does not modify the original review Markdown, owner-approved source crosswalk, or identity registry.

## 3. Validate the completed review

First run the bulk command without write flags. This is a dry-run and validates all source fingerprints and all 195 proposal rows:

```fish
uv run python tools/approve_imf_weo_field15_all.py
```

It must report 195 proposals to approve, reuse of the WBG and KOS mappings and aggregate decisions, and no database write.

## 4. Prepare and reconcile before any database application

First create the owner-approved review copy and candidate without creating a database approval or writing to either database:

```fish
uv run python tools/approve_imf_weo_field15_all.py --prepare-only --confirm-all-proposals --actor "project-owner" --note "I approve all 195 source-derived IMF WEO October 2026 NGDPD identity proposals for WP1.5 field 15 only."
```

The prepare-only report must be inspected before application. It reports the actual candidate observation count, the candidate KOS row count, the existing KOS rows by source code, candidate identity checks, and Project DB acquisition verification. It must show all 32 existing KOS observations inside the candidate with the same target game_id and source code. The preflight compares every existing source-version/checksum field-15 row against the candidate, including source code, year, value, source name, unit/scale, status and provenance. Any mismatch blocks preparation; no legacy row is overwritten or remapped.

Before applying, create and verify a SQLite online backup of the Game DB using SQLite's backup API (or the SQLite CLI `.backup` command). Do not copy the live database file directly and do not manipulate WAL/SHM sidecars. Keep the backup outside Git.

Only after inspecting the prepare-only report and verifying the backup, run the application command:

```fish
uv run python tools/approve_imf_weo_field15_all.py --apply --confirm-all-proposals --actor "project-owner" --note "I approve all 195 source-derived IMF WEO October 2026 NGDPD identity proposals for WP1.5 field 15 only."
```

This is the sole database approval and application command. The actor and note are recorded in the generated review artifact and application approval ledger. It:

1. Revalidates the Markdown decisions and immutable source fingerprints.
2. Creates a versioned, derived IMF WEO crosswalk containing the existing WBG mapping plus only the rows marked APPROVE. The original manual crosswalk is not modified.
3. Builds a deterministic field-15-only candidate from the original IMF WEO CSV. EXCLUDE and HOLD decisions remain explicit candidate exceptions; the 13 aggregate exclusions are preserved, while the owner-approved KOS mapping is reused.
4. Uses the existing application-approval ledger. An identical pending approval is resumed; an identical approved approval is applied; an already-applied identical artifact is not applied twice. A different artifact cannot reuse an old approval.
5. Applies the approved candidate transactionally using the existing IMF WEO importer.
6. Independently compares imported observation keys, values, units, statuses and provenance against the candidate; checks the approval event history; runs SQLite integrity and foreign-key checks; and verifies Project DB acquisition ID 5.

The application is bound to the review document SHA-256 through the derived crosswalk, as well as the candidate, raw source, registry, migration and acquisition evidence. Any changed input invalidates the review/application fingerprint.

## 5. Safety and closure conditions

- The command is field 15 / NGDPD only. It cannot apply fields 16, 18, 20 or 21. The KOS/UVK source-code discrepancy remains documented; no ISO/M49 assignment is created.
- The canonical identity registry and owner-approved IMF WEO crosswalk remain unchanged. The 32 legacy KOS rows must reconcile exactly before application; no database backup is created automatically by the application command.
- No identity is inferred from names, provider IDs or registry ISO fields at application time; only explicit owner-approved crosswalk entries resolve identities.
- WEO observation statuses remain `unclassified`. Technical import verification is not semantic classification or field-level semantic approval.
- The Project DB acquisition is checked, not rewritten or re-registered.
- A successful command is not sufficient to close field 15 until the owner inspects the verification report and the field's remaining semantic review requirements are satisfied.
- Do not begin field 16 until field 15 has been fully reviewed, approved, applied, independently verified in both databases, and documented.

## 6. Tests

```fish
uv run --extra dev python -m pytest -q tests/test_imf_weo_field15_identity_review.py tests/test_imf_weo_field15_review_workflow.py tests/test_manage_imf_weo_field15_review.py tests/test_approve_imf_weo_field15_all.py
```
