# IMF WEO field 15 identity review — automatic batch generation

**Status:** source-driven batch generator implemented; local execution and source-reconciliation verification pending.  
**Scope:** IMF WEO October 2026, NGDPD, WP1.5 field 15.

## Purpose

The ten manual batches demonstrated the review process. They are not inputs to the automatic process.

The generator rebuilds the complete 210-identity inventory from the original IMF WEO CSV, identifies aggregate series from the IMF Appendix classification, reconciles individual economies through the IMF Appendix and UN M49 evidence, and generates all ten cumulative review batches in one invocation.

It does **not** read any of the manually prepared files:

- no `field_15_identity_review_register_batch*.csv`;
- no manual field-15 identity inventory CSV;
- no manual aggregate exclusion register;
- no manual proposal register or completed review seed.

The original immutable source snapshots, the canonical identity registry, and the separately owner-approved WBG crosswalk are the inputs.

## Command

From the repository root:

```fish
uv run python tools/build_imf_weo_field15_identity_review.py
```

The command verifies source checksums, parses the inputs, builds and validates the complete review, then writes a new timestamped directory under:

`reports/sources/imf-weo-field15-identity-review/automatic/<UTC timestamp>/`

It refuses to overwrite an existing run directory.

## Original source inputs

1. IMF WEO October 2026 NGDPD annual CSV:
   `raw_data/sources/imf_weo/october_2026/dataset_2026-11-02T07_37_00.482492506Z_DEFAULT_INTEGRATION_IMF.RES_WEO_9.0.0.csv`
2. IMF October 2026 Database Appendix PDF and its verified extracted-text sidecar:
   `raw_data/sources/imf_weo/october_2026/October 2026 WEO Database Appendix.pdf`
   `derived_data/pdf_text/sources/imf_weo/october_2026/October 2026 WEO Database Appendix.pdf.txt`
3. UN Statistics Division M49 HTML snapshot and acquisition manifest:
   `raw_data/sources/un_m49/country_area_overview_html/2026-10-current/m49-country-area-overview.html`
   `data_manifests/sources/un_m49/country_area_overview_html/2026-10-current.json`
4. Official UN M49 FAQ, fetched during each run, validated for statistical-use codes 158 and 412, and saved with a timestamp and SHA-256 in the output directory.
5. Read-only canonical registry:
   `config/country_identity_registry.json`
6. Existing explicit owner-approved WBG-only crosswalk:
   `data/manual/source_crosswalks/imf_weo.json`

The tool parses the M49 HTML snapshot with the existing project M49 parser and retrieves the official FAQ separately. It does not use the manually generated M49 identity-review reports or the ten field-15 batch registers as source inputs.

## Automated reconciliation

### 1. Inventory and aggregate classification

- Read the raw WEO CSV and derive all annual NGDPD series, source IDs, source names, populated-year counts and first/last populated years.
- Read the IMF Appendix Country Data Documentation ISO Code table.
- Recognize WEO group aggregates only when their group-code pattern and source label match a documented IMF Appendix classification heading.
- Generate the aggregate exclusion register from those source records and Appendix evidence.

For the recorded October 2026 snapshot, validation requires 210 source identities, 13 aggregate exclusions and 665 populated aggregate values.

### 2. Individual-economy identity reconciliation

- Match IMF WEO source codes to the IMF Appendix ISO Code table.
- Match those official codes to the UN M49 ISO-alpha3 reference rows.
- Resolve the M49 country/area name to the canonical registry English name using exact normalized names or the existing explicit reviewed name-variant rules.
- Select the persistent `game_id` from that name reconciliation.
- Registry `source.current_source_id` and registry ISO fields are not used to establish identity.

The generated mapping remains a proposal. Name variants are recorded in the review rationale and do not constitute owner approval.

### 3. Explicit exceptions and existing approval

- **WBG:** preserve the separately owner-approved field-15-only WBG-to-Palestine crosswalk. It is not added to the new proposal set.
- **KOS:** keep `hold_for_evidence`. The WEO source uses KOS while the IMF Appendix identifies Kosovo as UVK. The M49 FAQ permits statistical-use code 412, but that does not resolve the IMF source-code discrepancy.
- **TWN:** use M49 FAQ numerical code 158 strictly for statistical purposes. The standard M49 country/area table does not list Taiwan separately. The proposal makes no sovereignty determination.

Unexpected source codes, missing M49 rows, ambiguous registry-name claims, duplicate targets, or changed source contracts fail closed rather than generating guessed mappings.

## Outputs

Each run writes:

- `field_15_identity_inventory.csv` — all 210 source identities, derived from the original WEO CSV;
- `field_15_exclusion_register.csv` — 13 aggregate dispositions;
- `identity_exceptions.csv` — KOS hold and evidence rationale;
- `field_15_identity_review_register_batch01.csv` through `field_15_identity_review_register_batch10.csv` — all ten cumulative batches, generated in one run;
- `field_15_identity_review_register_final.csv` — final 196-row review register;
- `m49_faq_snapshot.html` and `m49_faq_provenance.json` — the live official FAQ evidence and its retrieval fingerprint.
- `summary.json` and `summary.md` — counts, source fingerprints, validation and governance status.

Expected October 2026 result:

| Disposition | Count |
|---|---:|
| Proposal-only mappings | 195 |
| Held identity (KOS) | 1 |
| Aggregate exclusions | 13 |
| Existing approved WBG crosswalk | 1 |
| New owner-approved mappings | 0 |

The 196 review identities are divided into nine batches of 20 and one final batch of 16. Batch 5 contains 19 proposals and the KOS hold.

## Governance and side effects

This is an automatic evidence-reconciliation and review-artifact generator, not an approval or import tool.

It does not:

- approve any mapping;
- alter `data/manual/source_crosswalks/imf_weo.json`;
- modify `config/country_identity_registry.json`;
- create or modify a Project DB or Game DB record;
- alter the immutable IMF or UN source snapshots;
- infer identities from registry source IDs, registry ISO assignments, fuzzy names or record order.

All 195 mappings remain pending explicit project-owner approval. The WBG approval remains the only existing approved mapping in the IMF WEO crosswalk.

## Tests

Run the focused tests:

```fish
uv run --extra dev python -m pytest -q tests/test_imf_weo_field15_identity_review.py
```

The tests cover raw CSV inventory derivation, IMF Appendix code parsing, KOS/UVK detection, M49 FAQ statistical-code validation, M49-name-only registry matching, WBG crosswalk exclusivity, and one-run generation of all ten cumulative batches.


## Owner review, batch approval and field-15 application workflow

The ten generated CSV batches are now consolidated into one owner decision document. The workflow reuses the previously approved WBG-to-Palestine mapping, the 13 aggregate exclusions (665 populated values), and the KOS hold. It does not treat the 195 proposal rows as approved.

### Generate the single Markdown review file

From the repository root:

```fish
uv run python tools/manage_imf_weo_field15_review.py generate-review
```

This creates:

`reports/sources/imf-weo-field15-identity-review/field_15_owner_review.md`

Generation refuses to overwrite an existing review. It fingerprints the original IMF CSV and Appendix, M49 source snapshots and FAQ evidence, automatic source-derived inventory/registers, canonical identity registry, existing WBG crosswalk, prior-decision documentation, acquisition record and importer migration. It performs no database writes and creates no approval record.

### Owner review

Inspect all 195 proposal rows across batches 01–10. For each row:

- `APPROVE`: accept the exact proposed persistent `game_id`, copy it into **Approved game_id**, and record an evidence-based rationale.
- `HOLD`: leave **Approved game_id** as `-` and explain what evidence is missing.
- `EXCLUDE`: leave **Approved game_id** as `-` and explain why the source identity is outside this field's candidate scope.

Do not change the proposed identity, M49 code, source name, series, year coverage or proposal-basis evidence. The validator compares these columns with the fingerprinted source-derived register and canonical registry.

The document's owner declaration must also contain the actual owner actor, approval date, and an explicit overall approval statement. The KOS hold is fixed. The WBG mapping and aggregate exclusions are carried forward from their prior approvals; they are not re-decided by editing the new proposal rows.

### Validate the edited Markdown

First validate while decisions are still pending:

```fish
uv run python tools/manage_imf_weo_field15_review.py validate-review
```

After every new row has an explicit decision and rationale, validate the complete approval package:

```fish
uv run python tools/manage_imf_weo_field15_review.py validate-review --require-complete
```

Both commands are read-only. Any changed source, registry, prior approval evidence or protected proposal field causes validation to fail.

### One explicit command to approve, apply and verify

Only after the owner has inspected and completed the Markdown, run:

```fish
uv run python tools/manage_imf_weo_field15_review.py apply-reviewed --actor "project-owner"
```

The `--actor` value must exactly match the Owner actor recorded in the Markdown. This single explicit command:

1. Revalidates the complete review and all source fingerprints.
2. Checks the existing Project DB acquisition ID 5 and its integrity before creating a Game DB approval.
3. Builds a versioned, field-15-only derived crosswalk containing the reused WBG mapping and only the newly approved rows. The original crosswalk and global identity registry are not modified.
4. Rebuilds the candidate from the original IMF WEO CSV, not from manual batch or inventory registers.
5. Confirms every candidate identity is either WBG or explicitly approved, and every unmapped aggregate, KOS hold, owner hold or exclusion has an explicit disposition.
6. Checks that every candidate `game_id` already exists in the canonical Game DB before creating the approval record, and confirms that existing WEO field-15 rows for this source fingerprint are a subset of the candidate. Any legacy row outside the approved candidate (for example, an unresolved KOS mapping) stops the command before approval creation or observation writes. The workflow never deletes or remaps those rows automatically.
7. Reuses an identical existing approval/application if present; otherwise creates the exact-artifact approval, records the owner decision and applies transactionally.
8. Independently compares imported keys, values, units, source metadata and status against the candidate; verifies the approval event history, import linkage, SQLite integrity and foreign keys; and rechecks the Project DB acquisition and its two recorded artifact hashes/byte counts.

The command writes a verification report under `reports/sources/imf-weo-field15-reviewed-candidate/<review-hash>/`. It leaves all WEO observation statuses as `unclassified`. Successful import and technical verification do not themselves complete semantic field review or authorize field 16. Field 15 must be closed and documented under the project workflow before the next field begins.

### Focused tests

```fish
uv run --extra dev python -m pytest -q tests/test_manage_imf_weo_field15_review.py tests/test_imf_weo_historical_candidate.py tests/test_imf_weo_field15_identity_review.py
```

No owner review or database application has been performed by committing this tooling.

## Owner decision addendum — KOS source crosswalk — 2026-11-26

This decision supersedes the earlier KOS `hold_for_evidence` disposition above for IMF WEO October 2026, NGDPD, WP1.5 field 15 only.

The project owner explicitly approved:

- Provider/source key: `imf_weo`
- WEO source code: `KOS` (Kosovo)
- Persistent target: `tc_28aa17b84db24952b92fc51b421075e0` (Kosovo)
- Match method: `reviewed_manual`
- Scope: October 2026 WEO / NGDPD / field 15 only.

The target identity is corroborated by the canonical registry record (English name Kosovo; source and geometry key KOS) and the Game DB identity record for the same persistent game_id. The Game DB record has an approved `disputed_or_partially_recognized_entity` entity-type decision. ISO alpha-2 and alpha-3 remain unassigned.

The IMF Appendix Country Data Documentation uses `UVK` for Kosovo, while the WEO CSV uses `KOS`. This discrepancy is explicitly acknowledged in the owner decision. UN M49 FAQ statistical-use code 412 is contextual statistical evidence only; it is not treated as an IMF code concordance. No global registry, ISO/M49 assignment, entity-type, or other provider mapping is changed.

The 32 existing KOS observations (2000–2031) must be preserved and reconciled exactly against the rebuilt field-15 candidate, including values, target game_id and source provenance. The identity decision does not authorize deletion, remapping, overwriting, semantic status classification, or database application. Candidate generation and review tooling must consume the explicit crosswalk mapping and supersede the old generated KOS hold. Field 15 remains open until the normal approval, safe-backup, application and independent verification gates are completed.

