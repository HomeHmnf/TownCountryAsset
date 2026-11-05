# Project source catalogue registration audit

**Status:** Read-only mapping audit; no source rows have been seeded.  
**Registry inspected:** `config/data_sources.json`, Git blob `aad2ab57ed4b276ef19566515ad9463cf7a93d19` on `work/compiler-hardening`.  
**Related design:** [Stage 1 project database foundation](data-store-separation-stage-1-design.md).

## 1. Scope and counts

The current registry contains **31 stable source keys**. It exposes homepage and terms/licence URLs for most sources, and configured file-download definitions for **8 download entries** across 4 sources.

The registry is not a complete catalogue of every acquisition mechanism. In particular, API and manual sources may have no `downloads` entries. The Bahrain API dataset and ICASEES/IMF manually acquired materials therefore must not be omitted merely because their download arrays are empty.

## 2. Source-key and URL inventory

| Stable source key | Acquisition mode | Homepage URL | Terms URL | Configured download IDs/releases |
|---|---|---:|---:|---|
| `un_wpp` | https_download | yes | yes | demographic_indicators_medium (2024-main-demographic), population_by_age_5_group_sex_medium (2024-main-age-sex), demographic_indicator_notes (2024-demographic-notes), location_notes (2024-location-notes), interim_update_togo (2026-01-19-togo-update) |
| `imf_weo` | manual_or_api | yes | yes | — |
| `world_bank_wdi` | manual_or_api | yes | yes | — |
| `ilostat` | manual_or_api | yes | yes | — |
| `faostat` | manual_or_api | yes | yes | — |
| `koppen_beck` | manual_or_api | yes | yes | — |
| `fao_fra` | manual_or_api | yes | yes | — |
| `usgs_mcs` | manual_or_api | yes | yes | — |
| `pew_religion` | manual_or_api | yes | yes | — |
| `undp_hdr` | manual_or_api | yes | yes | — |
| `itu` | manual_or_api | yes | yes | — |
| `who_ghed` | manual_or_api | yes | yes | — |
| `world_bank_pip` | manual_or_api | yes | yes | — |
| `world_bank_wgi` | manual_or_api | yes | yes | — |
| `official_government_sources` | manual_or_api | no | no | — |
| `official_organization_registers` | manual_or_api | no | no | — |
| `iiss_military_balance` | manual_or_api | yes | yes | — |
| `sipri_milex` | manual_or_api | yes | yes | — |
| `global_carbon_project` | manual_or_api | yes | yes | — |
| `energy_institute` | manual_or_api | yes | yes | — |
| `protected_planet` | manual_or_api | yes | yes | — |
| `fao_aquastat` | manual_or_api | yes | yes | — |
| `natural_earth_admin0` | https_download | yes | yes | admin0_50m (rolling) |
| `iso_reference_mirror` | https_download | yes | yes | country_reference_csv (rolling) |
| `wikidata_sparql` | api | yes | yes | — |
| `lipis_flag_icons` | git | yes | yes | — |
| `iso_3166_official` | manual | yes | yes | — |
| `flag_evidence_official_sources` | manual | no | no | — |
| `un_m49` | https_download | yes | yes | country_area_overview_html (2026-10-current) |
| `bahrain_open_data` | api | yes | yes | — |
| `icasees_national_accounts` | manual | yes | yes | — |

The three source entries without a homepage or terms URL are retained as source identities; URLs must not be fabricated to fill those fields. Terms URLs are metadata, not proof that a licence was verified.

## 3. Mapping rules for database registration

1. Preserve every registry source key verbatim as `sources.source_key`; do not replace it with a provider display name.
2. Do not merge distinct source keys solely because the publisher is the same. Organisation identity is a separate, reviewable relationship.
3. Do not invent organisation keys or publisher relationships where the registry does not establish them. The nullable organisation foreign key permits source registration before that mapping is confirmed.
4. Map homepage and terms URLs to typed `source_urls` records. A terms URL is a URL role, not a licence conclusion.
5. Map each configured download definition to a dataset candidate and stream candidate only when its independent acquisition/retention boundary is established. Preserve the configured download ID and release label.
6. API sources without configured downloads require explicit dataset/API endpoint mapping. The Bahrain dataset identity is `03-unemployment-yearly`; use the existing Bahrain documentation and assessment evidence for its established validation disposition.
7. Manual sources with acquired artifacts must be represented using their actual dataset/release evidence, not an invented URL or download definition.
8. Keep WPP and ICASEES stream grouping unresolved as specified in the Stage 0 findings. This audit does not decide whether WPP supplements/notes share a retained-version stream or whether ICASEES publications form one or multiple streams.
9. Preserve the IMF October 2026 WEO CSV and Appendix PDF as distinct artifact roles within their documented release bundle; do not model the appendix as a second statistical dataset.
10. Preserve the UN M49 manifest's alternate representation pending a manifest adapter; catalogue registration must not rewrite its historical manifest.

## 4. Gaps and implementation implications

- The registry has source-level `name`, `domains`, `license_status`, `terms_url`, `attribution`, `notes`, `acquisition_mode`, and `release_discovery` metadata. The initial SQL currently has a generic `metadata_json` field for source-specific metadata; registration must preserve these fields losslessly, or a later schema revision should promote frequently queried fields to explicit columns.
- Organisation identity is not a mandatory registry field. Keep `organisation_key` nullable until a separate publisher-identity mapping is evidenced.
- Source URL roles can overlap in the registry (for example, homepage and terms URL may be identical). Preserve both semantic roles; do not deduplicate across roles.
- `config/data_sources.json` currently says raw data is local-only/untracked while Stage 0 established that source artifacts are tracked in Git. This is a known policy/configuration mismatch and is outside this registration audit.
- Registry release-discovery fields are policy/cache metadata. The authoritative release lifecycle must move to the project DB in the later lifecycle stage; do not seed null `latest_*` values as actual release records.

## 5. Disposition

The stable source keys and existing URL metadata are sufficiently defined to register source identities without guessing publisher organisations. Dataset/stream registration requires the source-specific boundaries noted above. No database seeding, source-selection change, acquisition, validation, approval or retention operation was performed by this audit.
