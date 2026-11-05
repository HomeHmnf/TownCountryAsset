# Implementation documentation index

- [Database implementation log](database.md) — WP1 implementation sequence, migration history, owner-run validation records and current status.
- [Data refresh implementation log](data-refresh.md) — pipeline orchestration, acquisition, candidate generation and guarded publication.
- [Shared PDF text extraction](pdf-text-extraction.md) — automatic text derivatives for acquired PDFs and backfill of existing raw snapshots.
- [Data-store separation Stage 0 inventory](data-store-separation-inventory.md) — read-only baseline procedure for the current database, consumers, source configuration and source-related files.
- [Data-store separation Stage 0 findings](data-store-separation-stage-0-findings.md) — approved owner-supplied database/filesystem evidence, table and artifact disposition, Bahrain validation reference, release lifecycle reconciliation and remaining design gates.
- [Data-store separation Stage 1 design](data-store-separation-stage-1-design.md) — approved project DB foundation scope, relational model, connection/migration isolation, retention-state constraints and owner-run acceptance criteria.
- [Project source catalogue registration audit](data-store-separation-source-catalogue-audit.md) — mapping of all 31 configured source keys and 92 URL records, with the idempotent synchronizer and completed Stage 1/2 validation evidence.
- [Stage 2 dataset and acquisition-stream registration](data-store-separation-stage-2-dataset-registration.md) — five evidence-backed dataset identities, three approved stream boundaries, deferred WPP/ICASEES stream decisions and completed owner-run validation.
- [Stage 3A manifest adapter and integrity audit](data-store-separation-stage-3a-manifest-audit.md) — read-only adapter for historical manifest variants and SHA-256/byte-count/path integrity verification; owner-validated with 10 manifests and 15 artifacts.
- [Stage 3B acquisition provenance registration design](data-store-separation-stage-3b-provenance-design.md) — event identity, lossless manifest/artifact mapping, state semantics, idempotency and deferred stream boundaries; includes the remaining historical-evidence linkage task.
- [Stage 3B provenance registration implementation](data-store-separation-stage-3b-provenance-registration.md) — migration 003, transactional manifest-backed registration, and owner-validated result: four acquisitions and seven artifacts registered; ICASEES/WPP deferred.
- [Stage 3C IMF WEO manual acquisition registration](data-store-separation-stage-3c-imf-manual-acquisition.md) — source-specific registration of the October 2026 CSV and Database Appendix as one date-precision manual acquisition event; owner-validated, acquisition ID 5, two artifacts, byte integrity verified.

These are implementation records, not the normative architecture contract. See [architecture](../architecture/README.md) for stable design rules and [feature documentation standard](../feature-documentation-standard.md) for new work.
- [Stage 4 IMF WEO semantic assessment](data-store-separation-stage-4-imf-weo-semantic-assessment.md) — consolidated five-field semantic disposition, country discrepancy evidence, coverage/identity limitations, outstanding vintage and metadata gates, and governance boundary.
- [Temporary IMF WEO semantic-review workspace](../../reports/workspaces/imf-weo-semantic-review/README.md) — Fish commands to collect the owner-run reports into a review bundle without modifying their originals.
