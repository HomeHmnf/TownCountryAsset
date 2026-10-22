# ISO alpha-2 gap review report

**Review status:** Step 1 decision applied; no ISO assignments are marked verified.
**Branch:** `work/compiler-hardening`
**Decision:** Store `FR` for France and `NO` for Norway in the persistent identity registry as unverified proposals. Keep the other six official ISO alpha-2 values empty. Defer any Kosovo-specific `XK` application code to a later decision.
**Data boundary:** No approved snapshot or TownCountryGame files were changed. Stable `game_id` values were preserved.

## Summary

Eight records had Natural Earth `ISO_A2=-99`. Two records now have registry alpha-2 proposal values backed by Natural Earth `ISO_A2_EH`; both remain `status=proposed` and `assignment_status=unverified`. The other six remain null in the registry's official ISO alpha-2 field.

| Natural Earth ID | Entity | Registry ISO alpha-2 after decision | Assignment status | Decision rationale |
|---|---|---|---|---|
| `FRA` | France | `FR` | `unverified` | Natural Earth `ISO_A2_EH=FR`; official listing confirmation remains required before verification. |
| `NOR` | Norway | `NO` | `unverified` | Natural Earth `ISO_A2_EH=NO`; official listing confirmation remains required before verification. |
| `SOL` | Somaliland | `null` | `unverified` | No official alpha-2 assignment evidenced in the inspected source. |
| `KOS` | Kosovo | `null` | `unverified` | `XK` is not an official ISO 3166-1 alpha-2 assignment; defer separate application-code design. |
| `CYN` | Northern Cyprus | `null` | `unverified` | No official alpha-2 assignment evidenced in the inspected source; entity classification is still open. |
| `IOA` | Indian Ocean Territories | `null` | `unverified` | `ISO_A2_EH=AU` is a parent-state fallback, not a distinct code for this feature. |
| `ATC` | Ashmore and Cartier Islands | `null` | `unverified` | `ISO_A2_EH=AU` is a parent-state fallback, not a distinct code for this feature. |
| `KAS` | Siachen Glacier | `null` | `unverified` | No official alpha-2 assignment evidenced in the inspected source; entity classification is still open. |

## Record-level traceability

| Natural Earth ID | Stable game ID |
|---|---|
| `FRA` | `tc_471ae6d7112b4537a7ae5ca1e6a816a5` |
| `NOR` | `tc_f4a6e15a05474af2b81c9524ed988d89` |
| `SOL` | `tc_9a78f2eebcc24906a5c67581c0c3895e` |
| `KOS` | `tc_28aa17b84db24952b92fc51b421075e0` |
| `CYN` | `tc_d3e7f81572fd44ab920bfc066d592873` |
| `IOA` | `tc_7cd2130353a64e57bd3782773a8e12c7` |
| `ATC` | `tc_b61ca098adb74efc84564fd9fa800bf8` |
| `KAS` | `tc_644aaabf37604038996e34c1bc91c970` |

## Verification and limitations

- This step records proposals only. It does not claim that France or Norway has passed direct confirmation against the current ISO Online Browsing Platform.
- Source fallback fields are evidence for review, not automatic approvals.
- Kosovo's `XK` must not be represented as an official ISO alpha-2 assignment.
- The two Australian-associated features must not inherit `AU` as if it were their unique ISO code.
- No entity type, Persian localization, flag mapping, source feature identity, or stable game ID was approved or changed.

## Sources

- [ISO 3166 country codes](https://www.iso.org/iso-3166-country-codes.html)
- [Natural Earth issue #675: ISO_A2 / ISO_A3 sentinel values](https://github.com/nvkelso/natural-earth-vector/issues/675)
- [Natural Earth country-field metadata mirror](https://source.coop/portolan/portolan-pipeline/portolan-reference/PRs/175/reference/natural-earth-countries/README.md)
- [Persistent country identity registry](https://github.com/HomeHmnf/TownCountryAsset/blob/work/compiler-hardening/config/country_identity_registry.json)
- [Detailed gap investigation](https://github.com/HomeHmnf/TownCountryAsset/blob/work/compiler-hardening/docs/review/iso-alpha2-gap-investigation.md)

## Decision record

- User decision: applied.
- France proposal: `FR`, proposed and unverified.
- Norway proposal: `NO`, proposed and unverified.
- Other six official ISO alpha-2 values: null.
- Kosovo `XK`: deferred to a later application-code decision.
- Approved data changed: no.
