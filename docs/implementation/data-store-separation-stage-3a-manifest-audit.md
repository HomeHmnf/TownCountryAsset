# Stage 3A — read-only acquisition-manifest adapter and integrity audit

**Status:** Implemented; awaiting owner-run validation.  
**Scope:** Read existing tracked acquisition manifests and verify their referenced artifacts. This stage does not register acquisitions in SQLite.

## 1. Existing manifest variants

The adapter supports the existing representations without rewriting source JSON:

- Bahrain rolling API captures: a `files` array with `local_raw_path`, `byte_count` and `sha256`.
- ICASEES manual publication bundle: a `files` array using `path`/`repository_path`, and both expected and observed byte-count/hash fields.
- UN M49 current reference: one artifact represented by top-level `local_raw_path`, `byte_count` and `sha256`, rather than a `files` array.
- UN WPP main releases, supplements and notes: one-file `files` arrays with release and retrieval metadata.

The adapter maps these variants to a common audit representation. It retains each manifest's original source identity, dataset/download identity, release label, release kind and retrieval/recorded timestamp. It does not infer that different manifests belong to the same retention stream.

IMF WEO is not part of the manifest scan because the October 2026 CSV and Database Appendix currently have no formal source manifest. Their manual bundle record is a separate follow-up; this adapter does not fabricate one.

## 2. Integrity contract

Run:

```fish
uv run python -m tools.audit_acquisition_manifests
```

For machine-readable output:

```fish
uv run python -m tools.audit_acquisition_manifests --format json
```

The audit recursively reads JSON manifests below `data_manifests/sources`, resolves artifact paths relative to the repository root, and checks:

- manifest JSON structure and required source/dataset/release identity;
- supported multi-file or single-file artifact layout;
- repository-contained relative paths (including symlink escape prevention);
- referenced file existence and regular-file status;
- declared byte count and SHA-256 against the actual file;
- conflicting expected and observed checksum/size declarations;
- duplicate artifact paths within one manifest.

The command writes only to stdout. It does not open either SQLite database, write reports, update manifests, create acquisition rows, validate provider semantics, promote releases, or apply retention. Exit status is zero only when all discovered manifest/artifact checks pass.

## 3. Evidence boundaries

A matching checksum proves byte identity against the manifest, not provider authenticity, semantic validity, release suitability, completeness beyond the manifest's own declarations, or approval to apply data.

Repeated Bahrain captures remain separate manifest/acquisition events even where artifact hashes match. The existing Bahrain validation disposition remains settled and is not reconsidered by this integrity audit.

ICASEES remains one manifest bundle for audit purposes only; this does not decide whether it represents one dataset or several. WPP notes and the Togo supplement are audited as manifest artifacts, not assigned independent retention streams. UN M49's alternate top-level representation is adapted in memory only.

## 4. Owner validation

Pending owner-run execution of the command and focused tests. Record exact test counts and audit summary here after the repository owner supplies terminal output.

## 5. Exit criteria and next step

Stage 3A is complete only after the owner confirms the focused tests and repository audit. Resolve every integrity error before acquisition registration. A clean audit permits the next design step: a lossless manifest-to-acquisition provenance mapping, including a formal treatment of the IMF WEO manual bundle. It does not itself create database acquisition records or settle the unresolved ICASEES/WPP stream boundaries.
