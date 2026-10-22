# ISO alpha-2 gap investigation — Step 1

**Status:** Step 1 decision recorded. Registry already contains `FR` and `NO` as unverified proposals; no registry values needed changing. Candidate and approved data remain unchanged.
**Branch:** `work/compiler-hardening`
**Scope:** Investigate the eight candidate records whose Natural Earth `ISO_A2` value is `-99`. This report is a review aid, not an approval.

## Findings

The source's `ISO_A2` field is not authoritative by itself when its value is `-99`. Natural Earth provides `ISO_A2_EH` as a separate field that repairs some of these values. ISO's own guidance says its Online Browsing Platform is the current source for officially assigned codes; user-assigned code elements are not official ISO assignments ([ISO 3166 overview](https://www.iso.org/iso-3166-country-codes.html)). Natural Earth metadata and related documentation explain that France and Norway are exceptions with recoverable official codes, while several disputed/special areas have no ISO 3166-1 code ([Natural Earth issue documenting the sentinel values](https://github.com/nvkelso/natural-earth-vector/issues/675); [Natural Earth field notes mirrored by Source Cooperative](https://source.coop/portolan/portolan-pipeline/portolan-reference/PRs/175/reference/natural-earth-countries/README.md)).

| Stable `game_id` | Natural Earth ID | Name | Source `TYPE` | `ISO_A2` | `ISO_A2_EH` | Initial evidence-based assessment |
|---|---|---|---|---|---|---|
| `tc_9a78f2eebcc24906a5c67581c0c3895e` | `SOL` | Somaliland | Sovereign country | `-99` | `-99` | No official ISO alpha-2 code evidenced. Natural Earth marks it outside ISO recognition; keep official ISO field empty unless stronger evidence says otherwise. |
| `tc_f4a6e15a05474af2b81c9524ed988d89` | `NOR` | Norway | Sovereign country | `-99` | `NO` | Strong source evidence for official code `NO`; confirm against ISO's current listing before recording as verified. |
| `tc_28aa17b84db24952b92fc51b421075e0` | `KOS` | Kosovo | Disputed | `-99` | `XK` | `XK` is used by some systems but is not an officially assigned ISO 3166-1 alpha-2 code. Do not store it as an official ISO code; a separate application-specific code would need explicit design approval. |
| `tc_471ae6d7112b4537a7ae5ca1e6a816a5` | `FRA` | France | Country | `-99` | `FR` | Strong source evidence for official code `FR`; confirm against ISO's current listing before recording as verified. |
| `tc_d3e7f81572fd44ab920bfc066d592873` | `CYN` | Northern Cyprus | Sovereign country | `-99` | `-99` | Natural Earth treats this as a disputed/special entity outside ISO coding. Keep official ISO alpha-2 empty unless authoritative contrary evidence is found. Entity classification needs separate review. |
| `tc_7cd2130353a64e57bd3782773a8e12c7` | `IOA` | Indian Ocean Territories | Dependency | `-99` | `AU` | The feature is associated with Australia and has `ISO_A2_EH=AU`; this is the parent country's code, not evidence of a distinct code for this feature. Do not assign `AU` as the territory's own ISO code. |
| `tc_b61ca098adb74efc84564fd9fa800bf8` | `ATC` | Ashmore and Cartier Islands | Dependency | `-99` | `AU` | The feature is associated with Australia and has `ISO_A2_EH=AU`; this is not a distinct code for the dependency. Do not assign `AU` as the feature's own ISO code. |
| `tc_644aaabf37604038996e34c1bc91c970` | `KAS` | Siachen Glacier | Indeterminate | `-99` | `-99` | Natural Earth marks this as an indeterminate/disputed area without an official ISO alpha-2 code. Keep official ISO alpha-2 empty; entity classification needs separate review. |

## Important distinctions

- The current candidate records retain each source feature's persistent `game_id`; no IDs should be regenerated or rekeyed based on ISO values.
- `ISO_A2_EH` is source evidence, not an automatic approval instruction. It supports the France/Norway proposals, but the registry's assignment status must remain unverified until a human decision and current ISO evidence are recorded.
- Kosovo's `XK` is not an official ISO 3166-1 alpha-2 assignment. If the game needs it, represent it explicitly as an application-specific or source-specific code rather than labelling it ISO.
- `AU` on Indian Ocean Territories and Ashmore and Cartier Islands identifies the parent/sovereign state in the source's fallback field; it must not be mistaken for a unique code for each feature.
- The source `TYPE` values are Natural Earth classifications, not final project decisions. In particular, Somaliland and Northern Cyprus should not be classified solely from the label `Sovereign country`.

## Recommended decision for this step

1. Approve recording `FR` and `NO` as **proposed official ISO alpha-2 candidates**, while leaving their assignment status unverified until the current ISO listing is checked and cited.
2. Keep the official ISO alpha-2 value empty for the other six records for now.
3. Do not introduce a separate non-ISO code field for Kosovo in this step; consider it later only if the project needs a separate application identifier.
4. Keep all eight records in review status. Do not change stable IDs, candidate output, approved output, entity classifications, or flag mappings in this step.

## Sources

- ISO, [ISO 3166 — Country Codes](https://www.iso.org/iso-3166-country-codes.html): official source for current assignments; explains the distinction between official and user-assigned code elements.
- Natural Earth, [Issue #675: ISO_A2 and ISO_A3 contain -99](https://github.com/nvkelso/natural-earth-vector/issues/675): documents the sentinel field issue and the affected feature types.
- Source Cooperative mirror of Natural Earth metadata, [Natural Earth country fields](https://source.coop/portolan/portolan-pipeline/portolan-reference/PRs/175/reference/natural-earth-countries/README.md): describes `ISO_A2_EH` as repairing France, Norway, and Kosovo while noting areas with no ISO code.
- Current branch files inspected: [identity registry](https://github.com/HomeHmnf/TownCountryAsset/blob/work/compiler-hardening/config/country_identity_registry.json) and [candidate countries](https://github.com/HomeHmnf/TownCountryAsset/blob/work/compiler-hardening/generated/town_country_asset_candidate/countries.json).

## Decision record

- Decision: **Applied per user decision.**
- France: registry `iso.alpha2=FR`, `status=proposed`, `assignment_status=unverified`.
- Norway: registry `iso.alpha2=NO`, `status=proposed`, `assignment_status=unverified`.
- Somaliland, Kosovo, Northern Cyprus, Indian Ocean Territories, Ashmore and Cartier Islands, and Siachen Glacier: registry `iso.alpha2=null`; assignment status remains unverified.
- Kosovo `XK`: deferred; it is not treated as an official ISO code.
- Stable `game_id` values unchanged; no approved snapshot or TownCountryGame files changed.
- Full decision report: [reports/iso-alpha2-gap-review.md](../../reports/iso-alpha2-gap-review.md).
