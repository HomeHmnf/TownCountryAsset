# Source ZIP evolution and country-catalog review plan

**Status:** Compiler safeguards, snapshot comparison, persistent registry proposal/validator, and opt-in compiler identity integration are implemented. Local verification of the integrated pipeline remains pending. No generated assets or game data changed.  
**Branch:** `work/compiler-hardening`

## Goal

Keep the asset project maintainable when a newer Natural Earth database ZIP replaces the current local archive. The ZIP is an input dataset, not the application's stable identity database. A source update must be treated as a controlled data migration, with a fresh compile, audit, crosswalk review, and generated-asset diff before release.

## ZIP update procedure

1. Preserve the current source archive and record its SHA-256 before replacing it. Never overwrite the only known-good copy.
2. Download the intended Natural Earth Admin 0 Countries 1:50m release from the official source. Record the actual release/version and retrieval date in `config/generation.json`; do not guess either value.
3. Verify the new archive is the intended layer and inspect the archive contents. The compiler rejects unsafe ZIP paths and archives containing zero or multiple shapefiles, but a structurally valid archive can still be the wrong dataset.
4. Run the compiler to a **new temporary output directory** first, rather than overwriting the currently validated output:
   ```fish
   uv run python tools/compile_natural_earth.py --source /path/to/new_ne_50m_admin_0_countries.zip --output generated/town_country_asset_candidate
   uv run python tools/audit_generated_assets.py --data generated/town_country_asset_candidate --source /path/to/new_ne_50m_admin_0_countries.zip
   uv run python tools/generate_country_svgs.py --data generated/town_country_asset_candidate --output generated/town_country_asset_candidate/svg
   ```
5. Run `uv run pytest -v`. Then compare the approved snapshot with the candidate:
   ```fish
   uv run python tools/compare_asset_snapshots.py --old generated/town_country_asset --new generated/town_country_asset_candidate --output reports/source-update-comparison.md
   ```
   The report includes source/schema/config changes, added/removed IDs, possible rekeys inferred from unique shared ISO candidates, changed source attributes/names/regions, and per-feature geometry changes. Review all added, removed, renamed, split, merged, or re-keyed features. It does not approve mappings automatically.
6. Re-run `tools/audit_game_country_crosswalk.py` against the candidate output and the game checkout. Review every changed candidate and every newly unmatched label. The crosswalk is a proposal, not permission to change game identity.
7. Promote the candidate only after review and successful tests/audits. Keep the previous source ZIP and output snapshot available for rollback.

## Identity and schema safeguards

- The current compiled `id` is a source identifier used by geometry files; it is not yet the canonical `game_id`. The canonical identity contract is documented in [country-identity-contract.md](../architecture/country-identity-contract.md). Never derive a game ID from ISO, a display name, or array order.
- A three-letter string is only syntactically ISO-shaped; verify the assignment independently before treating it as authoritative.
- Source identifiers can change between releases. If a configured stable-ID field disappears, changes meaning, or becomes non-unique, fail and review rather than silently treating array order as identity.
- Preserve raw source attributes and source archive SHA-256. A changed archive hash is expected after an update, but it must be accompanied by a reviewed change report.
- New or missing source fields, changed region values, changed feature counts, and changed IDs are data-contract changes to investigate—not changes to accept automatically.
- Do not commit the downloaded ZIP or generated output unless repository policy explicitly changes; `raw_data/` is ignored. Keep generated data reproducible from the recorded source and config.
- Do not update runtime catalogs, save IDs, flag data, aliases, quiz answers, or Godot code merely because Natural Earth changed a name or feature. These need an explicit compatibility plan.

## Next implementation steps\n\n1. Run the updated crosswalk tests and regenerate both audit reports. Direct source-name matches and translation-bridge matches must remain review-only candidates.\n2. Run the new registry tool on the validated compiled metadata: `uv run python tools/country_identity_registry.py --source-data generated/town_country_asset/countries.json --registry config/country_identity_registry.json --bootstrap`. Review the proposal; do not rerun bootstrap over an existing registry.\n3. Validate it with `uv run python tools/country_identity_registry.py --source-data generated/town_country_asset/countries.json --registry config/country_identity_registry.json`, and add the registry invariants to the full test run.\n4. Run the compiler with `--identity-registry config/country_identity_registry.json` into a candidate output directory. The compiler adds `game_id` to metadata and emits parallel game-ID-keyed geometry files while preserving existing source-ID-keyed files. Verify the dual outputs with the asset audit.\n5. Verify regression tests for source attribute preservation, unique game IDs, missing registry entries, and source-ID rename behavior. Add any missing simulated compile-time source-ID rename coverage.\n6. Build a separate compatibility crosswalk from legacy game labels to canonical `game_id`; do not use legacy game data as the source of canonical records.\n\n## First unmatched-label review batch

These are review targets from the current game's Persian catalog, not approved matches. For each one, confirm the exact catalog key and its use, inspect the compiled Natural Earth `name`, `source_attributes`, `iso3`, `regions`, and geometry, then record a decision. Do not infer a match solely from translation or similar spelling.

| Game label / candidate label | Review question | Status |
|---|---|---|
| `امارات متحده عربی` | Is the catalog entry intended to map to the source's United Arab Emirates feature, and is its ISO assignment independently supported? | Needs source-backed confirmation |
| `بوتان` | Confirm the source feature and whether existing catalog spelling/translation normalization accounts for the unmatched label. | Needs source-backed confirmation |
| `تیمور` | The game already has a legacy alias for Timor-Leste. Confirm that alias target and map representation before creating any crosswalk entry. | Alias exists; identity still needs review |
| `هلند` | Confirm the Netherlands feature and distinguish country identity from naming conventions such as Holland. | Needs source-backed confirmation |
| `چک` | Confirm the intended Czechia/Czech Republic source feature and any legacy display-name behavior. | Needs source-backed confirmation |
| `واتیکان` | Confirm the source's Vatican City / Holy See representation and inspect source ISO attributes; do not assume that names imply a particular code. | Needs source-backed confirmation |

### Required review record

Each approved crosswalk row should eventually include:
- region and exact legacy catalog key;
- stable game ID (only if/when a migration design defines one);
- Natural Earth source ID and source name;
- ISO alpha-3 value, source field, and independent verification status;
- mapping kind (exact, alias, renamed, territory/dependency, disputed, excluded, unresolved);
- evidence and reviewer decision;
- compatibility notes for flags, quizzes, aliases, maps, and saved progress.

Unresolved rows must remain explicitly unresolved. The current audit's single-candidate match is not an approval.

## Release gate

A new source ZIP is ready for downstream integration only when:
- the source layer/version and archive hash are recorded;
- the compiler, unit tests, generated-data audit, and SVG generation pass;
- the old/new source and output diff has been reviewed;
- every changed or unmatched game crosswalk row is either approved with evidence or clearly marked unresolved;
- runtime and save compatibility has a separate plan; and
- the prior known-good archive/output can be restored.
