# ISO alpha-2 gap review report

**Review status:** Historical France/Norway proposals remain unverified. The eight current identity edge cases have been reconciled in the canonical review-decision workflow.
**Branch:** `work/compiler-hardening`
**Decision date:** 2026-11-20
**Identity invariant:** Preserve all existing `game_id` values. Keep official ISO assignments separate from user-assigned project identifiers and flag-source identifiers.

## Current edge-case decisions

| Natural Earth ID | Entity | Official ISO alpha-2 / alpha-3 | Database assignment status | Decision |
|---|---|---|---|---|
| `FLK` | Falkland Islands | `FK / FLK` | `verified` | UN M49 captured reference provides the formal-name variant “Falkland Islands (Malvinas)”; feature scope reviewed. |
| `TWN` | Taiwan | `TW / TWN` | `verified` | ILO metadata records TW/TWN and M49 158; Natural Earth records `ISO_A2_EH=TW`, `ISO_A3_EH=TWN`. The project M49 CSV has no Taiwan row, so this is separately evidenced, not a M49 name match. |
| `SOL` | Somaliland | null / null | `not_applicable` | No official ISO 3166-1 assignment is evidenced; preserve identity without inventing a code. |
| `KOS` | Kosovo | null / null | `not_applicable` | No official ISO assignment. `XK` is retained only in the project-specific identifier namespace. |
| `CYN` | Northern Cyprus | null / null | `not_applicable` | No official ISO assignment; preserve a distinct reviewed entity classification. |
| `IOA` | Indian Ocean Territories | null / null | `not_applicable` | Natural Earth feature is a grouping of Christmas Island and Cocos (Keeling) Islands. `ISO_A2_EH=AU` is parent-state fallback. |
| `ATC` | Ashmore and Cartier Islands | null / null | `not_applicable` | Australian external territory. `AU` is a parent-state fallback, not a unique code for this feature. |
| `KAS` | Siachen Glacier | null / null | `not_applicable` | Geographic feature, not a country; identity is retired from the active country catalogue. |

## Historical eight-record investigation is a separate cohort

The 2026-10 Natural Earth `ISO_A2=-99` investigation covered France, Norway, Somaliland, Kosovo, Northern Cyprus, Indian Ocean Territories, Ashmore and Cartier Islands, and Siachen Glacier. It is not the same cohort as the current M49 unmatched rows.

- France (`FRA`) and Norway (`NOR`) remain proposed `FR` and `NO` values with `assignment_status=unverified`; this reconciliation does not approve them.
- The six remaining historical records now have explicit `not_applicable` decisions in the database.
- The current M49 proposal report has 235 candidates and 7 unmatched rows. Falkland Islands is a candidate with FK/FLK; Taiwan remains unmatched in that M49 snapshot because its row is absent from the captured CSV. Taiwan's TW/TWN assignment is independently evidenced and recorded separately.

## ISO and project identifier separation

- Official ISO codes are stored only in `countries.iso_alpha2` and `countries.iso_alpha3`.
- Kosovo's `XK` is stored only as a project identifier in the ISO review decision JSON with `is_official_iso=false`.
- Flag asset codes such as `fk`, `tw`, and `xk` are source identifiers and do not establish ISO status.
- Null official ISO values are paired with an explicit decision code and evidence in `country_review_decisions`, rather than left unexplained.

## Sources

- ISO, [ISO 3166-1:2020](https://www.iso.org/standard/72482.html).
- UNSD, [M49 overview](https://unstats.un.org/unsd/methodology/m49/overview/), including Falkland Islands (Malvinas) FK/FLK.
- ILO, [Taiwan metadata](https://metadata.ilo.org/thesaurus/351.html), records TW, TWN and M49 158.
- Natural Earth, [issue #675](https://github.com/nvkelso/natural-earth-vector/issues/675), documenting ISO sentinel values for special/disputed features.
- EU Vocabularies, [Countries and territories](https://op.europa.eu/en/web/eu-vocabularies/countries-and-territories), states Kosovo has no ISO 3166 code and uses user-assigned XK/XKX.
- Natural Earth, [Indian Ocean Territories IOA feature](https://api.mapserverstudio.net/mapserver/naturalearth/ogcapi/collections/ne_10m_admin_0_countries/items/1159320363?f=html).

## Database application

Migration `006_review_decisions.sql` adds append-only decision records. The dedicated reconciler writes five decisions per identity (ISO, entity type, flag, catalogue scope, naming), creates approved review proposals where applicable, updates canonical country fields and validates SQLite integrity/foreign keys transactionally.

