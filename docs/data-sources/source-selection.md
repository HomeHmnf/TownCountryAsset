# Source selection engine

## Responsibility boundary

`tools/database/source_selection.py` validates `config/source_selection.json` against the central source catalogue and resolves normalized observations for one identity/field. It is shared policy logic, not a provider adapter or an import step.

The engine:
- accepts only an approved policy using `latest_validated`;
- resolves historical source IDs to stable provider IDs without rewriting provenance;
- excludes observations that do not belong to the source's current `latest_validated` release;
- applies the three approved modes: `priority_source`, `primary_with_fallback`, and `custom_mixture`;
- requires explicit compatibility evidence before accepting a fallback;
- applies matching, explicitly scoped manual overrides before provider observations;
- returns the selected value together with policy version, source, release, period, unit, status, retrieval time, method, override/fallback evidence and rejected-candidate reasons.

It does not acquire data, perform provider-specific semantic validation, create release validation approvals, derive values, write a completeness audit, update SQLite, or publish assets. A refresh result marked `acquired_pending_source_validation` is not eligible for selection.

## Runtime interface

Validate the approved policy and all source references from the repository root with:

```fish
uv run python -m tools.validate_source_selection
```

The command checks the policy against the central registry and prints field/mode/source counts. It does not resolve or modify data.

Load the central source registry and policy, then call `resolve_field` with normalized observations:

```python
from pathlib import Path

from tools.database.source_selection import load_policy, resolve_field
from tools.database.structured_source_selection import resolve_structured_field
from tools.sources.registry import load_registry

registry = load_registry()
policy = load_policy(Path("config/source_selection.json"), registry)

decision = resolve_field(
    policy,
    registry,
    game_id="tc_...",
    field_key="population",
    observations=normalized_observations,
    manual_overrides=override_records,
)
```

For scalar fields, the observation input is an iterable of records with these fields. For structured fields, use the same fields plus `record_key` and optional `subfield_key`, and call the structured resolver:

| Field | Meaning |
|---|---|
| `game_id` | Persistent project identity; must already be resolved through an explicit reviewed crosswalk |
| `field_key` | Key from the approved selection policy |
| `source_id` | Stable provider ID or a supported historical alias |
| `release_id` | Exact immutable/declared release identifier |
| `value`, `unit`, `status` | Normalized value and its canonical unit/status |
| `observation_period` | Provider reference period; retained, not silently harmonized |
| `source_reference` | Provider table/record/URL reference when available |
| `methodology` | Normalization or source methodology |
| `retrieved_at` | Timezone-aware ISO 8601 retrieval timestamp |

The scalar and structured resolvers read `reports/sources/releases/<source-id>.json` and accepts only the release recorded as `latest_validated`. Tests and controlled callers may supply an explicit `release_states` mapping. A latest-available discovery, a successful download, or a pending-validation snapshot is never enough.

## Mode semantics

- **Priority source:** only the configured primary provider is eligible. No alternative source is considered.
- **Primary with fallback:** a valid primary value always wins. An explicit `unavailable` primary may be filled by the first validated, compatible fallback. A `not_applicable` primary is retained and does not trigger fallback. A fallback observation must carry `compatibility_status="compatible"` and a non-empty `compatibility_reference` documenting the field definition, unit, geographic/demographic/sector scope and period assessment.
- **Custom mixture:** the caller must supply an explicit `mixture_assignments` mapping for the identity. The assigned provider must be the primary or appear in the field's registered `mixture_sources` allowlist. No implicit mixing is performed.

A missing source row is not zero, absence, or not-applicable. Explicit null values are accepted only with `unavailable` or `not_applicable` status.

## Manual overrides

Manual overrides are supplied separately from the policy. A matching record requires `override_id`, `game_id`, `field_key`, `scope`, `value`, `unit`, `status`, `reason`, `author`, and timezone-aware `effective_at`. The scalar resolver applies field-level overrides. The structured resolver applies record-level and optional subfield-level overrides independently; multiple matching overrides are rejected.

A valid matching override wins over provider observations. Its identifier, reason, author, optional source, effective time, and the prior primary provider candidate are returned in the decision. Multiple matching overrides are an error, not an arbitrary tie-break.

## Current implementation boundaries

- All 41 approved WP1.5 field assignments are validated against the 29-source central registry.
- Current assignments contain 36 priority-source fields and five primary-with-fallback fields; no field currently uses custom-mixture mode.
- Explicit fallback compatibility is enforced at runtime. The engine does not infer compatibility from matching units alone.
- The population-density fallback is a declared derivation only. The resolver reports that it requires a separately validated derivation implementation; it does not calculate density.
- Natural-resource specialist fallbacks require a resource/metric mapping and per-record provenance; no unmapped specialist source is selected.
- The conditional capital-city fallback is not activated until a suitable official UN provider is registered and mapped.
- Structured fields use `tools/database/structured_source_selection.py` and `resolve_structured_field`. Each observation has a stable `record_key` and optional `subfield_key`; each item retains its own source, validated release, period, method, reference and retrieval timestamp.
- Structured priority/fallback/custom-mixture behavior is resolved independently per record/subfield. Fallbacks require explicit compatibility status and evidence; custom mixtures require an explicit assignment for each item and an allowlisted source.
- Record/subfield manual overrides are independently audited and take precedence only for their exact scope. The prior primary-provider candidate is retained.
- Callers may supply `expected_records=[{"record_key": "..."}]` (optionally with `subfield_key`) from a fixed resource/category catalogue. Expected-but-missing items are returned with `unavailable` status and null value, rather than silently omitted or interpreted as absent.
- Resource-specific fallback mappings are constrained to the matching `record_key`; a provider mapped for one commodity cannot fill another commodity. Empty mappings mean no specialist fallback is eligible.

The resolver is deterministic for the same policy, validated-release ledger, observations, overrides and assignments. Its returned decision is suitable as input to the standardized source-selection reports planned for the next stage. It never writes a decision or changes the canonical database itself.

## Standardized resolution and audit reports

Resolve an already-normalized input file and produce the complete project-wide selection audit:

```fish
uv run python -m tools.resolve_source_selection --input raw_data/normalized/source-observations.json
```

Optional arguments are `--policy`, `--registry`, `--overrides`, and `--output-dir`. Defaults use the approved policy, central source registry, policy-declared manual override path, and `reports/sources/selections`. The input must be a JSON object with `schema_version: 1`, an `observations` array, and either a `game_ids` array or observations/overrides containing `game_id`. Each `game_id` must already have been assigned through the reviewed identity crosswalk; this command does not perform identity matching.

Optional input properties are:
- `release_states`: explicit mapping of stable source IDs to validated release IDs. If omitted, the resolver reads each source's `latest_validated` release ledger.
- `manual_overrides`: an array of scoped override records. If omitted, the resolver reads the policy-declared override file when it exists.
- `mixture_assignments`: object keyed by field key, each containing explicit game/record-to-source assignments.
- `expected_records`: object keyed by structured field key, each containing the fixed catalogue's expected `record_key` and optional `subfield_key` entries.

The resolver evaluates every policy field for every supplied identity. Structured fields are resolved independently per record/subfield. An expected structured catalogue is needed to emit explicit unavailable rows for catalogue items with no provider observation; without an expected catalogue, the resolver does not invent missing records.

Each run writes one bundle under `reports/sources/selections/<run-id>/`:
- `summary.md`: coverage by status, country/entity, field, selected source and release.
- `records.csv`: every resolved scalar field and structured record/subfield, including source and release provenance.
- `missing.csv`: unavailable values only. Not-applicable values remain distinct in `records.csv`.
- `fallbacks.csv`: fallback decisions and compatibility evidence.
- `conflicts.csv`: rejected candidates and primary candidates not selected because an approved fallback filled the gap.
- `overrides.csv`: override ID, reason, author, effective time and prior provider candidate.
- `release_changes.csv` and `failures.csv`: present in the shared bundle contract; empty for a selection-only run.
- `provenance.json`: input checksum, policy version, release-state snapshot, run metadata and aggregate coverage.

Refresh runs use the same artifact contract under `reports/sources/refreshes/<run-id>/`. Their `records.csv` contains unchanged and attempted snapshots, `release_changes.csv` isolates newly discovered/acquired candidates, and `failures.csv` records acquisition or validation failures. Sources requiring manual review are visible as records, not misclassified as acquisition failures.

Reports are reproducible audit artifacts, not approvals. Neither refresh nor resolution changes the canonical database, advances `latest_validated`, or advances `latest_applied`. The consolidated selection bundle is the single completeness audit for the supplied run; do not create separate competing completeness reports for each field.

