# Stage 3B — acquisition provenance registration design

**Status:** Design approved; initial manifest-backed registration implemented in Stage 3B. Owner-run validation pending.  
**Prerequisites:** Stage 1 Project DB foundation, Stage 2 catalogue registration, and owner-validated Stage 3A manifest audit.  
**Architecture contract:** [Data-store separation plan](../architecture/data-store-separation-plan.md)  
**Stage 3A evidence:** [Manifest adapter and integrity audit](data-store-separation-stage-3a-manifest-audit.md)

## 1. Purpose and non-goals

Define a lossless, idempotent mapping from existing acquisition manifests and explicitly documented manual captures into `acquisitions` and `acquisition_artifacts` in `data/project/project_data.sqlite`.

This design does not execute acquisition, semantic validation, approval, application to the Game DB, source selection, retention cleanup, or raw-file movement/deletion. It does not rewrite historical manifests. The Game DB remains isolated from project provenance.

## 2. Identity model

An acquisition is one successful or attempted capture event for one registered dataset/stream. Its identity must distinguish separate captures even when provider release labels and artifact hashes repeat.

Proposed stable idempotency key:

```text
(source_key, dataset_key, stream_key, acquisition_event_key)
```

- `source_key`, `dataset_key`, and `stream_key` resolve through the registered catalogue; they are not inferred from a display name.
- `acquisition_event_key` is derived from an explicit immutable event identity: the manifest's repository-relative path for manifest-backed captures, or a separately reviewed stable manual-capture key for unmanifested material.
- A manifest path is an event locator, not proof that two different manifests are different provider releases. Distinct Bahrain manifest paths must remain distinct acquisition rows despite identical content hashes.
- Re-running registration for the same manifest must update/reconcile the same acquisition event, not create a duplicate.
- Moving/renaming a manifest must not silently create a second event. A future alias/manifest-history relation or immutable event UUID is needed before supporting manifest relocation; until then, manifest paths are treated as immutable source identifiers.
- Provider release identifiers remain metadata and are not unique keys.

Before implementation, inspect whether schema v1's uniqueness constraints can express this identity. If not, add a migration with an explicit unique idempotency column/key. Do not overload `provider_release_id` as the idempotency key.

## 3. Manifest-to-acquisition mapping

| Evidence | Project DB field | Mapping rule |
|---|---|---|
| Registered source key | `acquisitions.stream_id` via catalogue joins | Resolve exact source/dataset/stream; fail closed if no stream exists. |
| Manifest `release` / `snapshot_id` | `provider_release_id` | Preserve exact original string; nullable only when genuinely absent. |
| Manifest `retrieved_at` / `recorded_at` | `acquired_at` | Preserve original timestamp and offset; normalise only in a separate sortable UTC field if schema requires it. |
| Manifest relative path | `metadata_json` | Store relative path, manifest format/version and source field names. |
| `release_kind`, snapshot/discovery fields | `metadata_json` | Preserve complete original metadata losslessly. |
| Artifact path | `acquisition_artifacts.path` | Repository-relative POSIX path; verify containment and existence. |
| `file_id`, filename, source field names | artifact metadata | Preserve role hint and original identifiers; role is not guessed from extension alone. |
| Declared SHA-256 / byte count | artifact hash/byte fields | Store declarations and verify against actual bytes before registration. |
| Media/content type | artifact media type | Preserve exact source value. |
| Download URL, when explicitly recorded | artifact retrieval URL | Preserve only if supplied; do not infer from homepage or provider URL. |

The existing manifest's full parsed JSON should be retained in acquisition metadata (or a separately versioned immutable manifest payload) so future schema revisions can re-interpret fields without losing source evidence. The implementation must define canonical JSON serialization and hash the manifest payload itself; this manifest hash is distinct from each artifact hash.

## 4. Artifact roles

Use stable role identifiers, but retain the raw source role hint separately:

- Bahrain: dataset metadata and records page are separate artifacts within one capture event.
- ICASEES: workbook, definitive accounts PDF and GDP rebasing memo retain their distinct `file_id` values. This is a provenance bundle only; it does not decide whether these are one dataset or several.
- UN M49: HTML reference page is one artifact.
- WPP: main demographic CSV, age/sex CSV, notes CSVs and Togo ZIP remain separate artifacts associated with their own manifest event. Their shared provider/purpose does not create a common retention stream.
- IMF WEO: CSV role `dataset`; Appendix PDF role `supporting_document`, attached to one explicitly documented manual vintage-bundle event only after its source evidence and capture timestamp are confirmed.

Do not derive a semantic dataset identity from artifact extension, filename or role.

## 5. State and validation semantics

The schema's acquisition lifecycle includes candidate, acquired, validated, retained, superseded, failed and rejected. Registration must not jump to `validated` or `retained`.

Proposed initial states:
- Existing, integrity-audited manifest capture: `acquired` only after the registration transaction verifies the artifacts still match the manifest; otherwise registration fails without inserting a successful acquisition.
- Explicitly registered manual bundle: `acquired` only after all required bundle artifacts are present and verified.
- Failed/incomplete future attempt: `failed` with an error record and no successful retained-version effect; detailed attempt/report retention needs separate policy.

Byte integrity is not semantic validation. The already settled Bahrain validation disposition must be linked to the matching acquisition event using its existing assessment/approval evidence; do not rerun or downgrade it. If the current schema cannot represent that historical validation evidence without changing lifecycle state or inventing a report, add a reviewed evidence-link design before implementation.

ICASEES and WPP stream boundaries remain unresolved. Their manifests can be parsed and integrity-audited, but acquisition registration requiring an `acquisition_streams` foreign key must be deferred until a valid stream mapping is approved. Do not create placeholder streams or attach these captures to unrelated streams.

UN M49 and IMF WEO have registered stream identities. IMF WEO still requires a manually curated bundle descriptor and evidence of the common capture event before registration.

## 6. Transactionality and idempotency

Registration should be one Project DB transaction per acquisition event:

1. Re-resolve source, dataset and stream identities.
2. Re-read and hash the manifest and each referenced artifact.
3. Validate the complete event payload and artifact list before writing.
4. Insert or reconcile one acquisition using the idempotency key.
5. Insert/reconcile all artifact rows.
6. Commit only if the event and all artifacts are complete and internally consistent.

A failure must roll back the entire event. Re-running an unchanged manifest must be a no-op. If the same idempotency key is presented with changed manifest bytes, changed artifact paths, hashes or event identity, fail with a conflict; do not silently mutate historical provenance. Corrected evidence should be represented by an explicit superseding event or reviewed repair operation.

Do not perform file I/O mutations inside the database transaction. The audit/verification phase reads files first; the transaction records the verified snapshot. A file changing between verification and commit is a race. Mitigate by rechecking stat/hash immediately before insertion, and document that filesystem immutability is an operational prerequisite; stronger protection would require content-addressed staging, which is outside this stage.

## 7. Stream boundary and registration matrix

| Source | Dataset / stream | Stage 3B disposition |
|---|---|---|
| Bahrain | `03-unemployment-yearly / rolling_api_snapshot` | Eligible for provenance registration after linking existing settled validation evidence. Three manifest paths remain three events. |
| UN M49 | `country_area_overview_html / rolling_reference_page` | Eligible for provenance registration as one reference-page capture. |
| IMF WEO | `world_economic_outlook / manual_vintage_bundle` | Eligible only after manual bundle descriptor confirms both artifacts and their shared acquisition event/timestamp. |
| ICASEES | unresolved | Parse/audit only; no acquisition registration until dataset/stream boundary decision. |
| UN WPP | two dataset identities; streams unresolved | Parse/audit only; no acquisition registration until independent retention boundaries are approved. |

## 8. Retention separation

This stage must not mark any acquisition `retained`, `superseded` or delete data. The fixed stream retention limit of two is a future policy constraint, not an instruction to apply it during provenance registration.

A later retention stage must first prove candidate validation and approval gates, per-stream ordering, failure safety, atomic metadata transitions and coordinated artifact/derivative deletion. Repeated identical-hash captures remain separate events; blob deduplication, if later added, must not erase event-level provenance.

## 9. Required schema review before implementation

Inspect and explicitly decide:
- immutable acquisition event key and uniqueness constraint;
- original timestamp preservation plus sortable UTC representation;
- manifest payload/hash storage and schema version;
- artifact role vocabulary and original role-hint preservation;
- acquisition-level integrity status distinct from semantic validation;
- links to assessment reports and approval/application records, especially Bahrain;
- representation of manual acquisition events without formal manifests;
- conflict behaviour when an existing event's evidence changes;
- whether acquisition_artifacts.path must be unique globally or only within an acquisition;
- no mutation of source manifests or canonical Game DB.

No migration should be written until this schema review and the owner-approved field mapping are complete.

## 10. Acceptance criteria for the implementation stage

- Every inserted acquisition resolves to an explicitly registered dataset and stream.
- One event key maps to at most one acquisition row.
- All manifest and artifact source evidence is preserved losslessly.
- Hashes and byte counts are verified at registration time.
- Bahrain's distinct capture events remain distinct and link to existing validation evidence without reopening it.
- No ICASEES/WPP acquisition rows are inserted while their stream boundaries remain unresolved.
- IMF WEO is not registered until its manual bundle evidence is explicit.
- Re-running registration is idempotent; changed evidence fails closed.
- All writes are transactional and confined to the Project DB.
- No validation promotion, approval, application, retention, file deletion or Game DB changes occur.

## 11. Proposed implementation sequence

1. Schema review and migration design, including acquisition event identity and evidence links.
2. Add a manifest-to-domain adapter with golden tests for every existing manifest variant.
3. Add an explicit manual bundle descriptor for IMF WEO after confirming capture evidence.
4. Add dry-run mapping output showing eligible/deferred events and exact artifact roles.
5. Implement transactional registration for eligible streams only.
6. Add owner-run validation and reconcile counts against manifest inventory.

Each substep must update this design/implementation documentation and preserve the no-retention/no-Game-DB boundary.


## 12. Implemented schema decisions

Migration 003 implements the initial event identity and integrity-evidence portion of this design:

- Event uniqueness is enforced by (stream_id, acquisition_event_key), with the manifest's repository-relative path as the immutable event key.
- The exact manifest bytes are fingerprinted in manifest_sha256.
- integrity_status is independent of the acquisition lifecycle status.
- evidence_json preserves the complete parsed manifest payload; acquisition_artifacts.metadata_json preserves each original artifact object.
- Manifest-backed registration resolves manifest dataset_id before download_id, preventing Bahrain's download-folder key from being mistaken for the registered provider dataset ID.
- Only datasets with exactly one active registered stream are eligible.

The initial implementation registers eligible Bahrain and UN M49 events. ICASEES and WPP remain deferred. IMF WEO remains deferred until its manual acquisition record is reconciled against the tracked files and the bundle's event-time evidence is made explicit. No acquisition is marked semantically validated or retained.

See [Stage 3B provenance registration implementation](data-store-separation-stage-3b-provenance-registration.md) for the command, tests and owner-run acceptance procedure.
