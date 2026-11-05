# Stage 3C — IMF WEO October 2026 manual acquisition registration

**Status:** implementation committed; awaiting owner-run validation.  
**Architecture contract:** [Data-store separation plan](../architecture/data-store-separation-plan.md)  
**Manual source evidence:** [IMF WEO October 2026 manual acquisition record](../data-sources/imf-weo-october-2026-manual-acquisition.md)  
**Prerequisites:** Project DB schema v3, source/dataset/stream catalogue synchronized, and Stage 3B manifest-backed registration.

## 1. Purpose and scope

The IMF October 2026 CSV and its vintage-specific Database Appendix are a documented two-artifact manual acquisition bundle. They have no formal provider manifest, so they are deliberately outside the Stage 3A manifest adapter.

This increment adds a source-specific registration path for that already acquired bundle. It writes one acquisition event and two artifact records to the Project DB. It does not:
- create a fictitious manifest or exact acquisition timestamp;
- infer a new provider release or acquisition from the CSV filename timestamp;
- run semantic validation or WDI comparison;
- approve, retain, supersede or promote a release;
- change source-selection policy or write to the Game DB;
- move, rewrite or delete raw files.

## 2. Evidence and event identity

The registration is grounded in:
- the manual acquisition record's stated download date, 2026-11-02;
- its documented provider publication date, 2026-10-13;
- the exact two filenames, byte counts and SHA-256 checksums;
- Stage 0 confirmation that both raw files are Git-tracked and their Git blobs match the working tree;
- the 2026-11-05 read-only assessor's independent fingerprint match for both files.

The acquisition date is stored as `2026-11-02` with explicit precision `day`. No time-of-day is available. The CSV filename timestamp `2026-11-02T07:37:00.482492506Z` is retained as an observed export-generation token only; it is not used as `acquired_at`.

The stable event key is `manual:october_2026:2026-11-02` within the registered `imf_weo/world_economic_outlook/manual_vintage_bundle` stream. The provider release ID is `october_2026`; the provider dataset version is `IMF.RES_WEO_9.0.0`.

No formal manifest exists, so `manifest_sha256` remains NULL. Instead, `evidence_json` records the manual record path and its SHA-256, the explicit absence of a formal manifest, timestamp precision/limitations, provider dates, source page and the two artifact fingerprints.

## 3. Artifact mapping

| Artifact | Project DB role | Media type |
|---|---|---|
| October 2026 WEO CSV export | `dataset` | `text/csv` |
| October 2026 WEO Database Appendix | `supporting_document` | `application/pdf` |

Both artifacts point to the official WEO dataset page as the documented manual retrieval page. Artifact metadata retains the manual record, acquisition date precision, provider vintage/version, recorded fingerprint and retrieval method.

## 4. Registration command

First inspect the proposed event without writing:

    uv run python -m tools.register_imf_weo_manual_acquisition --dry-run

Then register it:

    uv run python -m tools.register_imf_weo_manual_acquisition

The command:
1. Resolves both artifact paths inside the repository and rejects paths outside it.
2. Recomputes byte counts and SHA-256 values and compares them with the exact recorded snapshot constants.
3. Requires the manual record to corroborate each filename and checksum.
4. Requires exactly one active registered IMF WEO manual-vintage stream.
5. Uses a deterministic event key and checks any existing event/artifacts for exact evidence equality.
6. Inserts one `acquired` event with `integrity_status=verified` and both artifact rows in one Project DB transaction.
7. Treats exact replay as unchanged and changed evidence as a conflict.

The command fails closed on changed bytes, missing evidence, missing/ambiguous stream registration or conflicting prior event content.

## 5. State and retention boundary

Successful registration means the two files match the recorded byte-level snapshot and are associated with one manual acquisition event. It does **not** mean the five indicator series are semantically valid, their units are approved, country identities are resolved, WDI comparison is complete, or the acquisition is eligible for retention.

The acquisition remains `acquired`, not `validated` or `retained`. No retention window is enforced by this command. The Project DB is the only database written.

## 6. Tests and owner-run validation

The new tests cover:
- dry-run performs no acquisition/artifact writes;
- exact snapshot fingerprints are required;
- the two artifact roles are recorded under one event;
- the documented day-level date is preserved without inventing a time;
- exact replay is idempotent;
- changed snapshot bytes fail without writing;
- absent stream registration fails closed.

Owner-run validation is pending. After pulling the implementation, run:

    git pull --rebase --autostash origin work/compiler-hardening

    uv run --extra dev python -m pytest -v \
        tests/test_imf_weo_manual_acquisition_registration.py \
        tests/test_imf_weo_assessment.py \
        tests/test_project_acquisition_registration.py \
        tests/test_acquisition_manifest_audit.py \
        tests/test_project_dataset_catalogue.py \
        tests/test_project_source_catalogue.py \
        tests/test_project_database_schema.py \
        tests/test_database_schema.py \
        tests/test_application_approval.py

    uv run python -m tools.register_imf_weo_manual_acquisition --dry-run
    uv run python -m tools.register_imf_weo_manual_acquisition

Expected result: one IMF WEO acquisition event with two artifact rows; status `acquired`, integrity `verified`; no Game DB writes, semantic promotion or retention action. The exact acquisition ID will be determined by the owner's Project DB.

## 7. Next gates

After owner validation, proceed to indicator-level semantic validation and WDI comparison. Resolve:
- PPPGDP actual/estimate/projected status;
- LUR unit and definition;
- country-code and alias exceptions;
- annual reporting-year month semantics;
- WEO versus WDI definition, unit, period and value comparability;
- country × field × year coverage and missingness.

Only validated and explicitly approved observations may be proposed for guarded Game DB application. Source-selection policy remains unchanged.
