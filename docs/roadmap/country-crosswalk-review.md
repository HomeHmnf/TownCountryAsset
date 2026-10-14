# Country crosswalk review: first regional discrepancy triage

**Status:** Preliminary read-only triage; no game data changed.  
**Game branch reviewed:** `stage/data-architecture`  
**Asset branch:** `work/compiler-hardening`

## Purpose

Record what can be established from the existing country catalogs, color maps, and `Country_Aliases.json` before making any runtime or catalog changes. This is a review worksheet, not an approved country-ID crosswalk. The asset project's canonical identity contract is documented in [country-identity-contract.md](../architecture/country-identity-contract.md); the game repository is compatibility evidence, not the source of canonical country records.

## America

| Finding | Evidence in current game data | Preliminary assessment | Decision/status |
|---|---|---|---|
| Catalog label `دومینیکن` is absent from the color map | `MapAmerica_Countries.json` contains both `دومینیکن` and `جمهوری دومینیکن`; the color map uses `جمهوری دومینیکن`; `Country_Aliases.json` maps `دومینیکن` to `جمهوری دومینیکن` | Existing alias strongly indicates these are two display labels for one selectable map entity, not two separate countries. | Candidate resolution identified; preserve existing alias behavior. Any catalog cleanup requires separate compatibility review. |

## Africa

| Finding | Evidence in current game data | Preliminary assessment | Decision/status |
|---|---|---|---|
| `جمهوری دموکراتیک کنگو` vs `جمهوری دمکراتیک کنگو` | Both spellings appear in the country catalog; color map uses the latter; alias maps the latter to the former. | Known spelling alias for one entity. | Candidate resolution identified; do not create a second country identity. |
| `جمهوری کنگو` vs `کنگو` | Catalog includes `جمهوری کنگو`; color map uses `کنگو`; alias maps `کنگو` to `جمهوری کنگو`. | Known display alias for one entity. | Candidate resolution identified. |
| `اسواتینی` vs `سوازیلند` | Catalog includes both; color map uses `سوازیلند`; alias maps `سوازیلند` to `اسواتینی`. | Legacy and current names for the same country. | Candidate resolution identified; retain compatibility alias unless a migration explicitly replaces it. |
| `جزایر مایوت` vs `مایوت` | Catalog includes both; alias maps `مایوت` to `جزایر مایوت`; neither is a color-map label in the report. | Duplicate display labels for a territory; map selectability is not established by the alias alone. | Verify source-map coverage and intended game scope. |
| `جزایر قناری`, `سبته`, `ملیلیه`, `مادیرا` | Catalog includes these entries; none appears in the color-map label set. Their catalog descriptions identify them as parts of Spain or Portugal. | These are subnational/autonomous or geographically distinct territories, not separate sovereign countries. Whether the existing map raster has distinct selectable regions is not established by JSON labels alone. | Inspect the actual map image/pixel regions and decide whether these entries should be selectable, aliases, or informational-only. |
| `جمهوری دموکراتیک عربی صحرا` | Catalog includes it; color map has no corresponding label. Catalog description calls it a self-proclaimed disputed state; `صحرای غربی` also exists in the catalog. | Disputed Western Sahara representation requires an explicit product/content policy and geometry check; do not merge or duplicate automatically. | Unresolved; require explicit decision. |

## Important interpretation

The audit's catalog/color-map difference counts compare labels, not geographic identities. An alias can explain a label mismatch, but it does not prove that the target has a valid selectable region in the current raster. Conversely, a color-map label with a legacy spelling may still represent the intended entity.

Before changing any JSON:
1. Inspect the corresponding map image and color-map pixels for each purported map entity.
2. Confirm whether the current catalog key is used by GDScript, quiz answers, aliases, or save data.
3. Decide whether the entry represents a sovereign state, dependency/territory, constituent region, disputed entity, or a legacy name.
4. Record the decision and evidence in a versioned crosswalk; only then plan compatibility-safe data edits.

## Next review batch

After updating and testing the candidate matcher, implement and review the asset-owned `game_id` registry for all source records before approving legacy crosswalk rows. Then review unmatched country-catalog labels in small regional batches, starting with the labels that are likely name/translation variants (for example, `امارات متحده عربی`, `بوتان`, `تیمور`, `هلند`, `چک`, and `واتیکان`). Validate each against source attributes and the game's intended geographic scope. Do not infer an approved ISO code from name similarity or three-letter syntax.

## Guardrails

- No game catalogs, flags, questions, save data, or GDScript are modified by this review.
- Source IDs and ISO codes remain separate.
- Existing aliases are compatibility rules, not proof of a future stable game ID.
- Do not treat every Natural Earth feature as a sovereign country or require every feature to appear in every regional map.
