# ISO assignment review log

**Status:** Open review queue; no assignments approved by this document.  
**Registry reviewed:** 242 records  
**Reference snapshot:** 2026-10-21, third-party distribution recorded in `reports/iso-assignment-proposals.md`  
**Rule:** All candidates remain unverified until the evidence and entity-scope review is recorded in the identity registry. Do not change `game_id` during ISO review.

## Review procedure

For each record:

1. Compare the Natural Earth source feature's geometry, source attributes, and feature type with the entity described by the proposed ISO reference row.
2. Confirm the candidate code and English name against an authoritative ISO source, recording the source URL/document, retrieval date, and relevant evidence. The current automated reference is a third-party distribution and is discovery evidence only.
3. Decide whether the feature represents an ISO 3166-1 entity. A territory/dependency may qualify; a geographic feature, subnational area, disputed entity, or combined/mismatched scope may not.
4. Record one explicit outcome: `verified`, `rejected`, or `unresolved`, with rationale and provenance. Keep both ISO fields null when no assignment is appropriate or evidence is insufficient.
5. Do not treat a normalized-name match or an explicit alias as proof. Do not infer codes from Natural Earth administrative IDs, existing provisional ISO values, or nearby features.
6. Re-run `uv run pytest -v` and `uv run python tools/audit_country_identity_registry.py` after reviewed registry edits. Review generated candidate outputs separately; do not replace validated assets automatically.

## Unmatched records requiring a decision

These eight names had no candidate in the 2026-10-21 proposal report. These notes are investigation directions, not final classifications.

| Registry name | Review direction | Initial state |
|---|---|---|
| Falkland Islands | Check alternate official reference naming and confirm the source geometry represents the ISO-listed territory. | unresolved |
| Somaliland | Apply the project's documented policy for entities without an ISO 3166-1 assignment; do not invent a code. | unresolved |
| Kosovo | Apply the project's documented policy for entities without a candidate in this reference; do not invent a code. | unresolved |
| Northern Cyprus | Treat as a scope/policy review; do not infer an ISO assignment from the label. | unresolved |
| Indian Ocean Territories | Inspect the source feature definition and whether it denotes one ISO-listed entity or a grouped geographic feature. | unresolved |
| Ashmore and Cartier Islands | Inspect feature scope and whether it corresponds to a separately coded ISO 3166-1 entity. | unresolved |
| Siachen Glacier | Determine whether this geographic feature belongs in the country/territory identity catalog at all. Do not assign a country code to a glacier by name matching. | unresolved |
| Sint Maarten | Check the reference's official label and confirm the source feature corresponds to the ISO-listed entity, rather than another part of the island. | unresolved |

## Scope-sensitive candidates requiring explicit evidence

The report proposes candidates for these labels, but the name relationship alone does not establish identity equivalence.

| Registry name | Proposed reference label | Review requirement | Initial state |
|---|---|---|---|
| Vatican | Holy See | Resolve entity-versus-display-label semantics; confirm the asset's intended entity matches the ISO entry. | unresolved |
| Taiwan | Taiwan, Province of China | Record the project's approved naming/classification policy and authoritative code evidence. | unresolved |
| Western Sahara | Western Sahara | Apply the project's documented treatment of disputed territories and verify the source feature scope. | unresolved |
| French Southern and Antarctic Lands | French Southern Territories | Confirm that the geometry and feature scope match the ISO-listed territory. | unresolved |
| Saint Helena | Saint Helena, Ascension and Tristan da Cunha | Confirm the source geometry represents the full listed territory rather than Saint Helena island alone. | unresolved |
| Saint Martin | Saint Martin (French part) | Confirm geometry and attributes identify the French part specifically. | unresolved |
| South Georgia and the Islands | South Georgia and the South Sandwich Islands | Confirm the feature's geographic scope matches the ISO-listed territory. | unresolved |

## Decision record template

Append one entry per reviewed record, and update the registry only after evidence is adequate:

- **game_id:**
- **Registry label / source feature:**
- **Candidate code(s):**
- **Decision:** verified / rejected / unresolved
- **Entity-scope finding:**
- **Authoritative evidence URL or document:**
- **Evidence retrieval date:**
- **Reviewer rationale:**
- **Follow-up required:**

## Current checkpoint

At the time this log was created, the proposal report lists 234 candidates, 8 unmatched records, 0 ambiguous matches, and 0 records marked verified. The candidate total includes exact normalized-name matches and explicit name-variant matches; see the report's separate counters after regeneration. This log does not approve any candidate or alter the identity registry.
