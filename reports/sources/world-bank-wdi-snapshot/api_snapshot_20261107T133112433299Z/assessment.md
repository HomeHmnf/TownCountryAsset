# World Bank WDI immutable API snapshot

- Snapshot: api_snapshot_20261107T133112433299Z
- Retrieved: 2026-11-07T13:31:36.501505+00:00
- Period: 2015–2025
- Source: World Development Indicators (API source ID 2)
- Response artifacts: 14 (4,226,626 bytes)
- Manifest: data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators/api_snapshot_20261107T133112433299Z.json

| Indicator | Role | Pages | Response rows | API last updated |
|---|---|---:|---:|---|
| NY.GDP.MKTP.CD | primary | 1 | 2926 | 2026-10-08 |
| NY.GDP.PCAP.CD | primary | 1 | 2926 | 2026-10-08 |
| NY.GDP.MKTP.PP.CD | primary | 1 | 2926 | 2026-10-08 |
| FP.CPI.TOTL.ZG | primary | 1 | 2926 | 2026-10-08 |
| SL.UEM.TOTL.ZS | primary | 1 | 2926 | 2026-10-08 |
| SL.UEM.TOTL.NE.ZS | diagnostic | 1 | 2926 | 2026-10-08 |

## Integrity and limitations

- Raw response bytes are preserved with request URL, headers, retrieval time, byte count and SHA-256.
- Pagination is followed to completion; malformed or changing pagination aborts the capture.
- Country and indicator metadata are retained alongside observation responses.
- Observation status is preserved verbatim and not interpreted.
- This is a rolling API capture, not a provider-declared WDI release vintage.
- World Bank dataset terms default to CC BY 4.0 for World Bank-produced datasets; third-party exceptions require review.
- Acquisition registration records provenance only; it is not semantic validation or approval.

## Side effects

- Raw snapshot, manifest and report written.
- No SQLite database, policy, approval or retention changes.
