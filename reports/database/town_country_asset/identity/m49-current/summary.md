# Identity reconciliation — UN M49

- Generated at (UTC): 2026-11-01T06:28:38.192950+00:00
- Reference: https://unstats.un.org/unsd/methodology/m49/overview
- Raw snapshot SHA-256: b9048114f6e7f2abda83bf03d4263c9d7cd1bd7230e3d0461025ee7839a7a1fb
- Normalized reference SHA-256: 7575550969de58be3909e0c2290478a4331c5c13be123a1043214c73de929b74
- Identity registry SHA-256: 329333a8e51e9c6bb50d9ce7a067ce7073174a2c477583374401a100de56f532
- Matching uses normalized English names and explicitly maintained name variants only.
- ISO codes and source identifiers are compared only after a name match; they are never used to infer identity.
- This report is read-only evidence. It does not change the registry or approve/verify assignments.

## Coverage

| Measure | Count |
|---|---:|
| Registry identities | 242 |
| M49 reference rows | 248 |
| Unique name matches | 225 |
| Unmatched registry identities | 17 |
| Ambiguous registry identities | 0 |
| Unmatched reference rows | 23 |

## Name and code comparisons

| Measure | Count |
|---|---:|
| Exact English-name matches | 199 |
| Normalized name variations | 3 |
| Explicit reviewed name variants | 23 |
| Alpha-2 agreements | 2 |
| Alpha-2 mismatches | 0 |
| Alpha-3 agreements | 223 |
| Alpha-3 mismatches | 0 |

## Combined classifications

| Classification | Count |
|---|---:|
| alpha2_only_agreement | 2 |
| alpha3_only_agreement | 223 |
| unmatched_registry | 17 |

## Source identifier comparison (not an ISO conflict)

- Source ID equals reference alpha-3: 222
- Source ID differs from reference alpha-3: 3

A source identifier may happen to equal an ISO alpha-3 code. That coincidence is not independent evidence of an ISO assignment.

## Artifacts

- `records.csv`: one row for every registry identity, with individual alpha-2/alpha-3 comparisons.
- `unmatched_registry.csv`: registry identities without a unique name match, including ambiguous matches.
- `unmatched_reference.csv`: M49 rows not uniquely associated with a registry identity.
- `provenance.json`: source, parser, checksums, field mapping and matching policy.
