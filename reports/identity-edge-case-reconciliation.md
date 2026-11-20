# Identity edge-case reconciliation

**Status:** Owner-approved decision set prepared for transactional application to the canonical database.
**Decision date:** 2026-11-20
**Scope:** Eight persistent identities with historic ISO, naming, classification, territory-scope or flag ambiguities.
**Identity invariant:** All canonical `game_id` values are preserved.

## Decision matrix

| Entity | ISO | Entity type | Flag treatment | Catalogue scope |
|---|---|---|---|---|
| Falkland Islands | Verify `FK/FLK` from UN M49 formal-name variant | `dependent_territory` | Pinned `fk` source SVG | Retain |
| Taiwan | Verify `TW/TWN` from ILO metadata and Natural Earth fallback fields; M49 CSV remains unmatched | `disputed_or_partially_recognized_entity` | Pinned `tw` source SVG | Retain |
| Somaliland | No official ISO code; null fields, `not_applicable` | `disputed_or_partially_recognized_entity` | Unresolved until reviewed manual SVG exists | Retain |
| Kosovo | No official ISO code; `XK` is project-only | `disputed_or_partially_recognized_entity` | Pinned `xk` flag asset; source code is user-assigned | Retain |
| Northern Cyprus | No official ISO code; null fields, `not_applicable` | `disputed_or_partially_recognized_entity` | Unresolved pending manual asset review | Retain |
| Indian Ocean Territories | No individual ISO code; `AU` is parent fallback | `dependent_territory` | No single flag for the Christmas Island + Cocos (Keeling) Islands composite | Retain as composite dependency |
| Ashmore and Cartier Islands | No individual ISO code; `AU` is parent fallback | `dependent_territory` | Parent-flag fallback to Australia; no duplicate `au` mapping | Retain |
| Siachen Glacier | No country ISO assignment | `geographic_feature` | No national flag | Retire from active country catalogue; preserve identity history |

## Naming decisions

- Preserve canonical display names.
- Add `Falkland Islands (Malvinas)` and `Falkland Islands (the) [Malvinas]` as English aliases for Falkland Islands.
- Add `Taiwan, Province of China` as a reference-name alias for Taiwan.
- Do not overwrite canonical names with reference-specific geopolitical labels.

## Legacy identifier reconciliation

| Stale association | Current canonical record |
|---|---|
| `tc_a3f73fd3bb6d4d7fb4ea31d433453bae` labelled Somaliland | Mali |
| `tc_3c148b1f7650455fa710ca87cf376728` labelled Northern Cyprus | Cyprus |
| `tc_73138c628d2a4509bad88f66deb5b27b` labelled Indian Ocean Territories | British Indian Ocean Territory |
| `tc_39ad5030b5f94f068d4a1528c60e5638` labelled Indian Ocean Territories | India |

These are historical report errors, not duplicate identities. The canonical edge-case IDs in the decision matrix are authoritative.

## Database representation

Migration `006_review_decisions.sql` adds append-only `country_review_decisions` rows with a domain, decision code, status, structured rationale, evidence, reviewer, timestamp, application approval and deterministic fingerprint.

The reconciler writes five decision domains for each identity: ISO assignment, entity classification, flag treatment, catalogue scope, and naming. It also writes approved `review_proposals` where applicable and updates canonical `countries`, `country_flags` and `country_names` rows. Kosovo's project code is stored in ISO decision JSON with `is_official_iso=false`; it is never stored in the ISO columns.

Siachen is marked `record_status='retired'`, not deleted. Historical foreign keys remain valid.

## Deliberately unresolved work

- Somaliland: flag remains unresolved because no reviewed manual SVG asset is present.
- Northern Cyprus: flag remains unresolved pending a separately reviewed manual SVG.
- Those two unresolved flag mappings remain candidates; the decision log records the unresolved outcome explicitly.
- Unresolved flags do not block the approved ISO, entity, naming or catalogue decisions.

## Sources

- [ISO 3166-1:2020](https://www.iso.org/standard/72482.html)
- [UN M49 overview](https://unstats.un.org/unsd/methodology/m49/overview/)
- [ILO Taiwan metadata](https://metadata.ilo.org/thesaurus/351.html)
- [Natural Earth disputed-boundaries policy](https://www.naturalearthdata.com/about/disputed-boundaries-policy/)
- [Natural Earth ISO sentinel issue #675](https://github.com/nvkelso/natural-earth-vector/issues/675)
- [EU Vocabularies — Kosovo code note](https://op.europa.eu/en/web/eu-vocabularies/countries-and-territories)
- [UK Kosovo toponymic factfile](https://assets.publishing.service.gov.uk/media/6941525329501ea90654a505/Kosovo_Toponymic_Factfile.pdf)
- [Natural Earth IOA feature metadata](https://api.mapserverstudio.net/mapserver/naturalearth/ogcapi/collections/ne_10m_admin_0_countries/items/1159320363?f=html)
- [Australian Government — Australian territories](https://www.infrastructure.gov.au/territories-regions/australian-territories)
- [Australian Government — Ashmore and Cartier Islands](https://www.infrastructure.gov.au/territories-regions/territories/ashmore-and-cartier-islands)
- [Geoscience Australia — external territories](https://www.ga.gov.au/scientific-topics/national-location-information/geography/external-territories)
- [Britannica — Siachen Glacier](https://www.britannica.com/place/Siachen-Glacier)
- Pinned flag-icons SVGs: [FK](https://github.com/lipis/flag-icons/blob/ac7e0eb3259eb62aa6100c435607e2fe03896a97/flags/4x3/fk.svg), [TW](https://github.com/lipis/flag-icons/blob/ac7e0eb3259eb62aa6100c435607e2fe03896a97/flags/4x3/tw.svg), [XK](https://github.com/lipis/flag-icons/blob/ac7e0eb3259eb62aa6100c435607e2fe03896a97/flags/4x3/xk.svg)

