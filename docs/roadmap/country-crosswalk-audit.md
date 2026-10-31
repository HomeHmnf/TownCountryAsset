# Game country crosswalk audit

**Status:** Read-only comparison tool implemented; review report must be generated locally.  
**Asset branch:** `work/compiler-hardening`  
**Game branch:** `stage/data-architecture`

## Scope

`tools/audit_game_country_crosswalk.py` compares generated asset metadata with the existing game JSON data without editing either repository's data. It reads the regional country catalogs, color-map labels, map question answers and choices, flag tiers and translations, general-information country entries, and the existing alias map.

The script proposes candidate links only when a country name can be bridged through the existing English-to-Persian `Flag_Translation.json` and then matched by normalized Persian text. Normalization handles common Persian/Arabic Yeh and Kaf variants, whitespace, and zero-width formatting characters. It does not use fuzzy matching and never writes a crosswalk or changes gameplay data.

## Run locally

With both repositories checked out:

```fish
builtin cd ~/Projects/Python/TownAndCountry
uv run pytest -v
uv run python tools/audit_game_country_crosswalk.py --asset-data generated/town_country_asset --game-root ~/Projects/Godot/TownCountryGame
```

The command writes two untracked report files under `reports/country-crosswalk-audit/`:

- `country-crosswalk-audit.md` — review summary, per-region catalog/map/question discrepancies, unmatched and ambiguous labels, and single-candidate suggestions.
- `country-crosswalk-audit.json` — full machine-readable records and label-level evidence.

The reports are local generated outputs; do not commit them automatically. Inspect them first, then share the Markdown summary and relevant JSON findings for review.

## Interpretation rules

- An asset `source_id` is not automatically an approved game `country_id`.
- An `iso3_candidate` must be checked against applicable ISO reference/provenance; syntax alone is insufficient.
- Candidate matches are not approvals. Review dependencies, disputed territories, constituent countries, country/territory choices, and region-specific game semantics explicitly.
- Catalog keys, color-map labels, and question answers are audited separately. A question answer must resolve to an entity selectable on its map; catalog presence alone does not prove selectability.
- Iran's province/city dataset is local administrative content and is intentionally excluded from the Natural Earth country crosswalk.
- The script is read-only. It must not modify game catalogs, flag data, save data, or runtime GDScript.

## Reporting refinement

The audit distinguishes the count of unmatched labels across all collected game text from the much narrower regional country catalogs. The broad label inventory includes quiz choices and answers, capitals, aliases, translations, and map labels; unmatched broad labels must not be interpreted as missing countries. Each regional section now lists its exact catalog/color-map label differences and reports country-catalog candidate, unmatched, and ambiguous labels separately.
