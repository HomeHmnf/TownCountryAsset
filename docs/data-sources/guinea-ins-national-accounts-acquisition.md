# Guinea INS national-accounts acquisition

The command captures two official INS publications as separate immutable
acquisition events: the legacy series in *La Guinée en chiffres 2023* and the
revised 2018-base SNA 2008 accounts in the June 2026 note.

## Acquire the publications

From the repository root:

```fish
uv run python -m tools.acquire_guinea_ins_national_accounts
```

The command downloads each official PDF over HTTPS, verifies the PDF signature,
and records final URL, retrieval timestamp, byte count and SHA-256. It writes
one timestamped manifest per dataset. Existing manifests are never overwritten;
a later retrieval creates a new event.

For the PDFs already downloaded manually, capture their current bytes with:

```fish
uv run python -m tools.acquire_guinea_ins_national_accounts --use-existing
```

This mode explicitly labels the filesystem modification time as its timestamp
basis; it does not claim an independently verified HTTP retrieval timestamp.

## Audit and register provenance

```fish
uv run python -m tools.audit_acquisition_manifests --manifest-dir data_manifests/sources/guinea_ins --format json
uv run python -m tools.register_project_acquisitions --manifest-dir data_manifests/sources/guinea_ins --dry-run
```

Inspect both outputs, then omit --dry-run to register the two events and their
artifacts in the Project DB. Registration records byte-level provenance only.

## Safeguards

- Each publication has its own dataset, stream, manifest and acquisition.
- Failed or partial downloads do not produce a manifest.
- The workflow does not validate statistical values, approve sources, change
  source selection, promote retention, or write to the Game DB.
- The source licence remains unclear or unverified.
