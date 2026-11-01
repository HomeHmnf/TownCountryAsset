# UN WPP identity crosswalk review approval

- Decision date: 2026-11-01
- Decision: approved
- Approver: project owner
- Approval evidence: explicit approval in the TownCountryAsset project conversation on 2026-11-01

## Approved scope

The project owner approved the initial UN World Population Prospects 2024 source-specific crosswalk comprising:

- **198** M49-based identity correspondences, where the M49 reconciliation supplied an exact or normalized-name match and the corresponding numeric M49 LocID was present consistently in both the WPP 2026 Medium demographic and age-sex snapshots.
- **1** explicit Taiwan WPP-only exception: game identity `tc_98ab3dee1d554162b6bbd5dac6374fc8` maps to WPP LocID `158`, source location `China, Taiwan Province of China`, ISO2 `TW`, ISO3 `TWN`.

This approval authorizes these correspondences to be represented as `reviewed_manual` in the **UN WPP source crosswalk only**. The Taiwan exception does not establish or modify a global identity, ISO, or M49 assignment.

## Explicit exclusions retained

- **4 source coverage exceptions** remain excluded from the crosswalk because their official M49 identifiers are absent from both WPP snapshots: Norfolk Island (574), British Indian Ocean Territory (86), Antarctica (10), and Heard Island and McDonald Islands (334).
- **39 identities** remain held for separate identity/name review or because no approved source-specific mapping exists.
- No name-only join, inferred substitute identifier, global identity-registry update, ISO assignment, or canonical SQLite write is authorized by this decision.

## Preconditions for downstream application

The generated crosswalk must still pass its schema, uniqueness, coverage, and source-snapshot checks. The WPP adapter must then validate the demographic and age-sex snapshots, the Togo interim supplement, all required provenance manifests, and the 1 July observation mappings. Candidate normalization and coverage reports must be reviewed separately.

This crosswalk approval is **not** approval to apply WPP observations to SQLite. The shared database application workflow remains mandatory: propose the exact normalized artifact, inspect its fingerprint and reports, explicitly approve that application, and only then run the transactional importer.
