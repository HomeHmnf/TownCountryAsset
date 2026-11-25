# WDI WP1.5 area/density candidate validation

- Snapshot: api_snapshot_20261121T074357472382Z
- Manifest SHA-256: 0f338a0606cdc951245de2c125221c7dacb537601c3d5db6fdb88aa0c0915748
- Explicit crosswalk mappings: 187
- Candidate rows: 648

| Field | Indicator | Candidate ISO3 | Mapped | Unmapped | Null rows | Invalid | Latest year range |
|---:|---|---:|---:|---:|---:|---:|---|
| 3 | EN.POP.DNST | 216 | 187 | 29 | 231 | 0 | 2021–2024 |
| 33 | AG.SRF.TOTL.K2 | 216 | 187 | 29 | 232 | 0 | 2021–2024 |
| 34 | AG.LND.TOTL.K2 | 216 | 187 | 29 | 231 | 0 | 2021–2024 |

## Area consistency

- No same-year surface/land inversion detected.

## Review boundary

- Latest non-null observation is selected independently per indicator and country; years need not align.
- Observation status is preserved verbatim; blank status is not interpreted as actual.
- ISO3-to-game_id mapping is exclusively through the supplied explicit crosswalk.
- Metadata source organization and source notes require human review; WDI source ID alone does not prove originating-organization authority.
- Surface/land consistency is checked only where their selected reference years match.
- No database writes, approval, source-selection or retention changes.
