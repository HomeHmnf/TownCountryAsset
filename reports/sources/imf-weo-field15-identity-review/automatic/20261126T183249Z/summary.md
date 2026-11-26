# IMF WEO field 15 identity review — automatic generation

- Generated (UTC): 2026-11-26T18:32:49.511373+00:00
- Inputs: immutable IMF WEO CSV and Appendix, UN M49 HTML snapshot, live official M49 FAQ snapshot, canonical registry, owner-approved WBG/KOS crosswalk.
- No manually prepared identity inventory, batch register, or aggregate exclusion register was read.

| Measure | Count |
|---|---:|
| Source identities | 210 |
| Aggregate exclusions | 13 |
| Individual economies | 197 |
| Existing WBG/KOS approved crosswalk | 2 |
| Proposal-only mappings | 195 |
| Held identities | 0 |
| Owner-approved new mappings | 0 |
| Automatic batches | 10 |

## Governance

- All 195 generated mappings remain pending explicit project-owner approval.
- KOS is resolved by the explicit owner-approved field-15-only crosswalk to the existing Kosovo game_id. The WEO KOS / IMF Appendix UVK discrepancy remains documented as a source-code qualification; no ISO/M49 assignment is inferred or changed.
- TWN uses M49 FAQ numerical code 158 strictly for statistical purposes; no sovereignty determination is made.
- WBG and KOS remain separately owner-approved field-15-only mappings; the KOS/UVK Appendix discrepancy is documented without changing ISO/M49 assignments.
- Registry source IDs and registry ISO fields are not used to establish identity; registry targets are resolved by official M49 English names and explicit reviewed name variants.

## Side effects

- Database writes: none.
- Owner approvals created: none.
- Canonical registry modified: no.
- IMF WEO crosswalk modified: no.
- Source snapshots modified: no.

## Generated artifacts

- `field_15_identity_inventory.csv`: regenerated from the raw IMF WEO CSV.
- `field_15_exclusion_register.csv`: regenerated from IMF group-code and Appendix classification evidence.
- `identity_exceptions.csv`: unresolved identity exceptions.
- `field_15_identity_review_register_batch01.csv` through `batch10.csv`: all cumulative batches generated in one run.
- `field_15_identity_review_register_final.csv`: final 195-proposal register.
- `m49_faq_snapshot.html` and `m49_faq_provenance.json`: retrieved FAQ evidence and fingerprint.
- `summary.json`: counts and source fingerprints.
