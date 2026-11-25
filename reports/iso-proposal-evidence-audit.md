# ISO proposal evidence audit

- Registry file: `config/country_identity_registry.json`
- Captured reference: `raw_data/iso/m49-iso-reference.csv`
- Proposal report: `reports/iso-assignment-proposals.md`
- Registry records: 242
- Unique registry game IDs: 242
- Reference rows: 248
- Proposal rows: 242
- Proposed code pairs: 234
- Consistency issues: 0

## Issue summary

| Issue type | Count |
|---|---:|
| missing proposal rows | 0 |
| stale proposal rows | 0 |
| duplicate proposal/registry IDs | 0 |
| candidate code conflicts | 0 |
| invalid candidate evidence | 0 |
| other consistency issues | 0 |

## Findings

No proposal/registry/reference consistency issues detected by this audit.

## Interpretation and safeguards

- This audit checks report freshness, registry coverage, candidate code pairs, and reference-label consistency.
- A passing audit does not establish ISO scope, political/entity semantics, or the correctness of an explicit name variant.
- The captured reference is a third-party distribution; provenance and retrieval metadata must be reviewed separately.
- This tool is read-only: it does not modify the registry, verify or approve assignments, change game IDs, or publish game assets.
- Review explicit variants and unmatched entities individually before designing any registry update workflow.
