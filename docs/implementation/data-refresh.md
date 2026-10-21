# Data refresh implementation log

**Scope:** TownCountryAsset fetches online data and prepares game-ready candidate assets. Updating TownCountryGame is explicitly out of scope.

## Step 1 — Environment configuration and CLI contract

**Status:** Configuration contract documented; runtime CLI implementation is the next step.

Added `.env.example` with source URLs, fetched-data folders, candidate/approved output folders, report folder, compiler configuration paths, feature toggles, and HTTP timeout. Added `docs/cli-tool.md` describing the intended one-command interface, output/report behavior, and safety boundaries.

Design decisions captured:
- Local `.env` is not committed; `.env.example` is the shareable template.
- Process environment variables override values from `.env`.
- Candidate output is distinct from approved output.
- ISO matches remain proposals; the identity registry is persistent and must never be regenerated automatically.
- This repository does not modify the game repository.

Validation still required locally: check that `.env` is ignored, run the CLI help/tests once the CLI implementation lands, and verify no workflow touches the game repository.

## Remaining phases

1. Environment loader and orchestrating CLI, including stage-by-stage success/failure reporting.
2. Atomic fetch/provenance and input validation, with safe failure behavior.
3. Candidate compile, SVG generation, asset/identity audits, ISO proposal refresh, and approved-snapshot comparison.
4. Tests for configuration precedence, offline/failing fetches, partial failure summaries, and safe output boundaries.
5. Final CLI README review and local end-to-end verification.

Each phase must be recorded here after its implementation and before moving to the next phase. Any product/data-policy decision that cannot be safely inferred must be asked before proceeding.
