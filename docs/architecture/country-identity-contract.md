# Canonical country identity contract

**Status:** Persistent proposal registry committed; compiler integration is implemented as an opt-in path and requires local verification.  
**Owner:** TownCountryAsset  
**Scope:** Source-derived country/territory records and the future game-facing identity layer.

## Core rule

Every accepted record in the asset project's country/territory catalog must have one non-empty, unique, immutable `game_id`. That ID identifies the entity inside the game and joins its geometry and metadata. It must not be derived from a display name, Persian translation, ISO code, array position, or a source identifier that may change between source releases.

The Natural Earth dataset is input data processed by TownCountryAsset. The legacy game repository is inspected only to audit compatibility; it is not the authority for asset records, source attributes, ISO values, or canonical identity.

## Separate identity from attributes

A future canonical record should have a structure equivalent to:

```json
{
  "game_id": "country_<stable-opaque-id>",
  "source": {
    "dataset": "natural_earth_admin_0",
    "source_id": "source-provided-id"
  },
  "iso": {
    "alpha2": null,
    "alpha3": null,
    "assignment_status": "unverified"
  },
  "names": {
    "en": "Source-backed English name",
    "fa": null,
    "aliases_en": [],
    "aliases_fa": []
  },
  "entity_type": "unreviewed",
  "regions": [],
  "geometry_key": "source-or-geometry-key"
}
```

This is an illustrative contract, not a claim that these fields or values are already implemented. Field names may be finalized during implementation. Missing ISO values are allowed; missing `game_id` values are not. Persian names must be authored or verified as asset-project localization data, not copied automatically from the legacy game's translation dictionary.

## ID lifecycle

1. Maintain an explicit identity registry in TownCountryAsset. Each current source feature must resolve to exactly one canonical `game_id`.
2. For the initial registry, propose IDs for all records from the processed source, including records without ISO codes and records that are dependencies, territories, or disputed entities. Do not silently exclude a feature just because it is not a sovereign state.
3. Once reviewed and committed, keep each `game_id` stable across source updates. If a source ID changes, add a reviewed source-ID-to-`game_id` mapping rather than minting a new game identity automatically.
4. New source features must be assigned IDs explicitly; removed or merged source features require a documented lifecycle decision. Never use row order or a display name as fallback identity.
5. ISO alpha-2/alpha-3 codes are attributes with source provenance and verification status, not primary keys. A syntactically valid code is not proof of the assignment.
6. English and Persian names, aliases, region membership, and geometry references attach to `game_id`. Name changes must not change the ID.
7. Multiple display labels may refer to one entity. Distinct entities must not be merged merely because their names or translations resemble each other.

## Source and game compatibility

- Source attributes and geometry come from the selected, versioned input dataset and its recorded provenance.
- Canonical identity and reviewed localization belong to TownCountryAsset.
- Legacy game catalogs, flag translations, aliases, quiz data, map color labels, and saved progress are compatibility evidence only. They can suggest a candidate mapping but cannot create or override a canonical asset record.
- The crosswalk audit remains read-only. A proposed match must record evidence and a human decision before it is approved.
- The game repository should consume a generated manifest keyed by `game_id` only after the identity registry and compatibility migration are reviewed. Do not change game runtime data as part of the initial registry creation.

## Registry tooling and compiler integration\n\n`tools/country_identity_registry.py` creates an initial proposal with `--bootstrap` and validates a persisted registry against compiled `countries.json`. Bootstrap uses random UUID-backed IDs and refuses to overwrite an existing registry. The committed registry contains source-derived English names, aliases, regions, and ISO alpha-3 candidates as unverified/provisional metadata; it does not approve those assignments.\n\nThe compiler now accepts `--identity-registry config/country_identity_registry.json`. With that option, it validates full source coverage and unique IDs, adds `game_id` to every country record, and emits parallel `geometry_game_id_low.json`, `geometry_game_id_medium.json`, and `geometry_game_id_high.json` files keyed by canonical `game_id`. Existing `id` fields and `geometry_{profile}.json` files remain source-ID-keyed for compatibility. The generated manifest includes hashes for both output families, and the asset audit checks canonical-keyed geometry when `game_id` is present. This dual-output stage is intentional; the game must not migrate until downstream consumers are reviewed.\n\nThe integration is opt-in for now. A successful registry-only check does not prove compiler integration; run the compiler with `--identity-registry`, then audit the resulting candidate directory.\n\nWhen a source release changes, do not rerun bootstrap. Review the source diff first. For a source ID rename, edit the existing registry record to keep its `game_id`, record the old source ID in `previous_source_ids`, set the reviewed new `current_source_id`, and update `geometry_key`. New features require an explicit new registry entry; removed, split, or merged features require a documented decision. The validator fails on coverage/count mismatches and conflicting mappings rather than auto-assigning identities.\n\n## Required validation

Before a registry can be considered usable, automated checks must establish that:

- every source feature is represented exactly once or has an explicit reviewed exclusion;
- every included record has a unique, non-empty `game_id`;
- every source feature resolves to a registry entry, with no implicit ID fallback;
- no ISO value is copied from an administrative source ID;
- each name and ISO attribute retains source/localization provenance and verification status;
- source updates report added, removed, changed, and re-keyed features without silently changing `game_id`; and
- all candidate links to legacy game labels remain review-only until approved.

## Migration order

1. Improve crosswalk candidate discovery and its tests without modifying game data.
2. Implement the explicit identity registry and schema in TownCountryAsset.
3. Generate a complete proposed registry from the current source, covering all records; review IDs and entity scope.
4. Add verified ISO/name/localization attributes and explicit unresolved statuses.
5. Validate the registry against the source and geometry outputs.
6. Produce a separate legacy-game compatibility crosswalk keyed by `game_id`.
7. Only after review, plan a compatibility-safe game migration for catalogs, maps, flags, questions, and saved progress.
