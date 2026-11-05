# Stage 3B — acquisition provenance registration

**Status:** Implemented; owner-run validation pending.  
**Architecture contract:** [Data-store separation plan](../architecture/data-store-separation-plan.md)  
**Design record:** [Stage 3B provenance design](data-store-separation-stage-3b-provenance-design.md)  
**Prerequisites:** Project DB schema v2, approved dataset/stream catalogue, and owner-validated Stage 3A manifest audit.

## 1. Scope delivered

This increment implements manifest-backed acquisition event registration in the Project DB. It does not perform semantic validation, approval, Game DB application, retention promotion/cleanup, source selection, or raw-file movement.

Files:
- migrations/project/003_acquisition_event_provenance.sql
- tools/database/acquisition_registration.py
- tools/register_project_acquisitions.py
- tests/test_project_acquisition_registration.py

## 2. Event identity and evidence

The event identity is (stream_id, acquisition_event_key), where the event key is the immutable repository-relative manifest path. A partial unique index enforces one acquisition per stream/event key. Provider release labels are retained as metadata and are not unique.

Migration 003 adds:
- acquisition_event_key — stable manifest event locator;
- manifest_sha256 — checksum of the exact manifest bytes;
- integrity_status — pending, verified, or failed, separate from semantic lifecycle status;
- evidence_json — original parsed manifest payload and registration method.

The acquisition metadata_json also retains the manifest path and schema version. Every artifact row retains its complete original artifact object in metadata_json, in addition to normalized path, role, hash, byte count, media type and retrieval URL.

The original manifest files are not rewritten. A changed manifest or changed artifact set for an already registered event fails closed; the tool does not mutate historical provenance. Repeated content hashes at different manifest paths remain distinct events.

## 3. Registration behaviour

Run:

    uv run python -m tools.register_project_acquisitions --dry-run
    uv run python -m tools.register_project_acquisitions

For each manifest, the command:
1. Runs the Stage 3A integrity audit across the manifest directory. Any audit error prevents registration.
2. Resolves the source and dataset using exact catalogue keys. The manifest dataset_id is preferred over download_id; this is necessary for Bahrain, whose provider dataset ID is 03-unemployment-yearly while its download folder key is unemployment_yearly.
3. Requires exactly one active registered stream for that dataset. Missing or ambiguous stream mappings are reported as deferred.
4. Requires a timezone-aware acquisition timestamp.
5. Re-reads and hashes every artifact immediately before registration.
6. Inserts the acquisition and all artifact rows in one Project DB transaction, initially as acquired with integrity_status=verified.
7. Treats an exact replay as unchanged and rejects changed evidence for an existing event.

The operation is transactional per event. It writes only to data/project/project_data.sqlite.

## 4. Eligibility and deliberate deferrals

| Source | Disposition |
|---|---|
| Bahrain Open Data | Eligible: exact dataset ID and one registered rolling API stream. Existing Bahrain semantic validation/approval evidence is not reopened or downgraded; registration records byte integrity only. |
| UN M49 | Eligible: exact dataset ID and one registered rolling reference-page stream. |
| IMF WEO October 2026 | Deferred from manifest registration: no formal manifest exists. The manual acquisition note byte counts/checksums must first be reconciled with the currently tracked raw files, and the two artifact event timestamp relationship must be represented explicitly. Do not infer a shared exact acquisition timestamp from the CSV export timestamp. |
| ICASEES | Deferred: dataset and stream boundaries remain unresolved. |
| UN WPP | Deferred: dataset identities exist but stream boundaries remain unresolved. |

The implementation does not create placeholder streams or infer source boundaries.

## 5. State semantics and non-effects

Registration marks byte integrity as verified and acquisition lifecycle state as acquired. It does not mark any acquisition validated or retained. Byte integrity is not semantic validity.

No acquisition approval, application, retention, cleanup, source-selection or Game DB operation is performed. The existing approval/application workflow remains in its current location pending the separately designed cross-database state machine.

## 6. Tests and owner validation

The new tests cover:
- dry-run has no writes;
- two captures with identical bytes remain separate events;
- registration records acquisition and artifact provenance;
- exact replay is idempotent;
- an unregistered stream is deferred without writes;
- changed manifest evidence conflicts with the existing event.

After pulling, run:

    git pull --rebase --autostash origin work/compiler-hardening

    uv run --extra dev python -m pytest -v \
        tests/test_project_acquisition_registration.py \
        tests/test_acquisition_manifest_audit.py \
        tests/test_project_dataset_catalogue.py \
        tests/test_project_source_catalogue.py \
        tests/test_project_database_schema.py \
        tests/test_database_schema.py \
        tests/test_application_approval.py

    uv run python -m tools.migrate_project_database
    uv run python -m tools.sync_project_source_catalogue
    uv run python -m tools.sync_project_dataset_catalogue
    uv run python -m tools.register_project_acquisitions --dry-run
    uv run python -m tools.register_project_acquisitions

Expected registration eligibility from the current tracked manifest set: three Bahrain capture events and one UN M49 reference-page event; ICASEES and WPP are deferred. IMF WEO is not part of the formal manifest inventory. Owner-run test and command output must be recorded before this stage is marked validated.
