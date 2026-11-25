# World Bank WDI WP1.5 application record

**Status:** applied and independently verified by the project owner.  
**Application date:** 2026-11-25.  
**Scope:** World Bank WDI fields 3, 33 and 34 for the captured API release.

## Frozen candidate and approval

- Dataset: `world_bank_wdi_wp1_5_area`
- Canonical source key: `world_bank_wdi`
- Release: `api_snapshot_20261121T074357472382Z`
- Raw source SHA-256: `7196c4bf58e63a75c4576fef063b0fd96cba99c118f9c112dadc4afbbd2a0476`
- Normalized candidate: `temp/wdi-wp15-regenerated/observations.json`
- Import manifest: `temp/wdi-wp15-regenerated/import_manifest.json`
- Candidate artifact SHA-256: `86196b1cdb1783c00e6d391d11d5314cf5c50ad4351b1664f24fa65735349c5b`
- Validated observations: 561 (187 each for fields 3, 33 and 34)
- Explicit crosswalk mappings: 187
- Normalized populated-value status: `unclassified` for all 561 rows; blank provider `obs_status` was not promoted to an inferred observed/estimated state.

The first stale proposal, `wp1-5-wdi-20261125`, was rejected because its candidate contained the invalid status `unspecified`. Its audit history was preserved. The corrected candidate was proposed and approved under `wp1-5-wdi-20261125-regenerated`. The approval actor is the owner-confirmed identifier `project-owner`.

Approval timestamp: `2026-11-25T12:56:38Z`. The approval event records the exact candidate hash and the approval rationale.

## Application result

The owner ran the existing transactional importer with the regenerated observations, explicit crosswalk, manifest and approval ID. It completed with exit status 0:

| Result | Value |
|---|---:|
| Database import ID | 4 |
| Scalar observations | 561 |
| Structured observations | 0 |
| Crosswalk mappings | 187 |
| Import idempotent | false (first application) |
| Importer integrity | ok |
| Importer foreign keys | ok |

Application ID: `wp1-5:world_bank_wdi:api_snapshot_20261121T074357472382Z:7196c4bf58e6`.

The approval ledger now reports status `applied`, with `approved_by=project-owner`, approval timestamp `2026-11-25T12:56:38Z`, and application timestamp `2026-11-25T12:57:35Z`. Its event sequence is `proposed` → `approved` → `applied`. The applied event records import ID 4, 561 observations, 561 scalar observations, zero structured observations and `idempotent=false`.

## Independent post-application verification

The owner supplied the read-only verification output on 2026-11-25:

- `PRAGMA integrity_check`: `ok`.
- `PRAGMA foreign_key_check`: no violations.
- Approval status, actor, artifact SHA-256, timestamps and application ID all match the approved application.
- `current_statistics`: 561 rows with `import_id=4`.
- `country_sources`: 187 rows with `import_id=4`.
- `dataset_imports`: one row with `import_id=4`.

This independently confirms that all expected scalar observations and explicit provider mappings persisted under import ID 4. The importer was not rerun during verification.

## Validation boundary and follow-up

The full repository test suite had passed before this application: 561 tests passed on `work/compiler-hardening` at commit `95f056cadfc0a1a3c6f57604c0cb82db5016a97a`. That test result is recorded as pre-application validation; it is not represented as a post-import test run.

This application imports the WDI observations and mappings only. It does not change source-selection policy, promote candidate/verification states, or approve IMF WEO comparability. The next WP1.5 batch remains the IMF WEO consolidated review for fields 15, 16, 18, 20 and 21, under the shared review/approval/application workflow.
