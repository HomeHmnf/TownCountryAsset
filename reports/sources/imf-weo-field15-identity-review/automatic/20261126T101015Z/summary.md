# IMF WEO field 15 identity review — automatic generation

- Generated (UTC): 2026-11-26T10:10:15.772683+00:00
- Inputs: immutable IMF WEO CSV and Appendix, UN M49 HTML snapshot, live official M49 FAQ snapshot, canonical registry, approved WBG crosswalk.
- No manually prepared identity inventory, batch register, or aggregate exclusion register was read.

| Measure | Count |
|---|---:|
| Source identities | 210 |
| Aggregate exclusions | 13 |
| Individual economies | 197 |
| Existing WBG approved crosswalk | 1 |
| Proposal-only mappings | 195 |
| Held identities | 1 |
| Owner-approved new mappings | 0 |
| Automatic batches | 10 |

## Governance

- All 195 generated mappings remain pending explicit project-owner approval.
- KOS remains held because WEO uses KOS while the October 2026 IMF Appendix identifies Kosovo as UVK. The M49 FAQ's statistical-use code 412 is recorded as evidence but does not resolve the IMF code discrepancy.
- TWN uses M49 FAQ numerical code 158 strictly for statistical purposes; no sovereignty determination is made.
- WBG remains the separately owner-approved field-15-only mapping.
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
- `field_15_identity_review_register_final.csv`: final 196-row register.
- `m49_faq_snapshot.html` and `m49_faq_provenance.json`: retrieved FAQ evidence and fingerprint.
- `summary.json`: counts and source fingerprints.
