# Feature: Shared automatic PDF text extraction

> **Status:** Implemented; awaiting owner-run local validation  
> **Owner/work package:** Shared source-management infrastructure  
> **Target branch:** work/compiler-hardening  
> **Last updated:** 2026-11-05

## Problem and motivation

PDF publications are frequent source artifacts. Requiring each provider-specific assessment to implement extraction or asking the owner to run a separate conversion command for every new PDF creates duplicated logic and inconsistent text outputs.

## Goals

- Automatically create a searchable plain-text derivative when the shared acquisition service receives a PDF.
- Reuse one implementation across all source providers and domain assessments.
- Backfill existing PDFs already stored under `raw_data/`.
- Preserve original PDF bytes and their acquisition fingerprints.
- Make each derived text artifact traceable to the exact source PDF and extractor version.

## Non-goals

- OCR of scanned/image-only pages.
- Editing, optimizing, recompressing or replacing source PDFs.
- Treating extracted text as a validated dataset or as a replacement for the original publication.
- Automatically extracting PDFs copied outside the shared acquisition/assessment workflows without a subsequent backfill or explicit helper call.

## Scope and dependencies

- **Code:** `tools/sources/pdf_text.py`, `tools/sources/registry.py`, `tools/assess_icasees_national_accounts.py`.
- **Tests:** `tests/test_pdf_text_extraction.py`, `tests/test_source_registry.py`.
- **Dependency:** `pypdf>=5.0` as a project runtime dependency.
- **Data:** PDF files identified by their content signature, not only by extension.
- **Documentation:** source-management guide, ICASEES source index and implementation index.

## Design and decisions

The shared helper is `tools/sources/pdf_text.py`.

- Original snapshots stay in `raw_data/` and are never modified.
- Derived artifacts are stored in `derived_data/pdf_text/`, mirroring the source-relative path. A text file is accompanied by JSON metadata.
- Metadata records source SHA-256, text SHA-256, page count, pages with text, extractor name/version and document metadata.
- Matching sidecars are reused. Partial, stale or fingerprint-mismatched sidecars fail explicitly rather than being overwritten.
- PDF detection checks the PDF signature in the first 1,024 bytes, so content type and filename suffix are not the sole authority.
- The shared acquisition function invokes extraction automatically after generic response validation. Extraction failure is recorded in the acquisition manifest; the successfully acquired original PDF is retained.
- The ICASEES assessment uses the same helper and page-level text output.
- The backfill CLI scans existing raw-data files: `uv run python -m tools.sources.pdf_text`.

Text extraction is limited to embedded text. A PDF with no extractable page text receives status `no_embedded_text`; OCR is not attempted.

## Implementation plan

1. **Shared extraction helper** — implemented in `tools/sources/pdf_text.py`; produces immutable, fingerprinted text/metadata sidecars.
2. **Acquisition integration** — implemented in `tools/sources/registry.py`; detects PDFs and runs the shared helper automatically.
3. **Existing snapshot backfill** — implemented as the `tools.sources.pdf_text` CLI.
4. **Assessment integration** — implemented in the ICASEES assessment; removed its provider-specific extraction implementation.
5. **Tests and documentation** — added helper/acquisition tests and updated source-management and ICASEES documentation/indexes.

## Data, provenance and compatibility

- Original raw PDF SHA-256 remains authoritative for source integrity.
- Derived text has a separate SHA-256 and is not an original provider artifact.
- Derived outputs are local generated artifacts; they do not change source releases, source-selection policy, normalized observations or canonical SQLite.
- Existing PDF paths and manifests are not rewritten by the backfill.

## Safety and operational boundaries

- No raw PDF is overwritten, deleted or modified.
- No database writes, source-policy changes, approval decisions or release promotions occur.
- A text extraction error does not discard a successfully acquired PDF.
- Manual file copies are not monitored by a background filesystem watcher. Run the backfill after manually adding a batch of PDFs.
- No OCR is performed; image-only PDFs require a separate future OCR feature with explicit language/runtime/licensing review.

## Validation and acceptance criteria

- [ ] `uv run --extra dev python -m pytest -v tests/test_pdf_text_extraction.py tests/test_source_registry.py tests/test_icasees_national_accounts_assessment.py`
- [ ] `uv run python -m tools.sources.pdf_text` backfills current raw PDFs and reports extraction status.
- [ ] `uv run --with pypdf python -m tools.assess_icasees_national_accounts assess` reuses/creates ICASEES sidecars and passes its structural/WEO checks.
- [ ] Verify raw PDF fingerprints are unchanged and each text metadata file references the matching source and text hashes.
- [ ] Owner-run local validation remains pending until command output is supplied.

## Documentation and related records

- Area index: [Implementation](README.md)
- Source-management contract: [Project-wide data source management](../data-sources/source-management.md)
- ICASEES source index: [ICASEES documents](../data-sources/icasees/README.md)
- Feature standard: [Feature documentation standard](../feature-documentation-standard.md)

## Open questions and next steps

- Decide separately whether OCR is required for any scanned publications; current scope intentionally extracts embedded text only.
- Consider CI enforcement for stale/missing derived PDF text only after the project decides whether generated derivatives should be tracked or remain local.
