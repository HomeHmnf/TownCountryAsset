# Project-wide data source management

## Purpose and authority

`config/data_sources.json` is the authoritative project-wide registry for external and local source records. It includes WP1.5 providers and the sources used by identity, geography, localization, flags, and asset refresh workflows. Domain contracts (for example, the WP1.5 field contract and resource catalogue) describe what the project needs and reference stable source IDs; they must not become competing source catalogues.

The registry records source identity, homepage, domains, acquisition mode, download definitions, format, release, applicable WP1.5 fields, terms URL, attribution, and license classification. Sources that require manual retrieval, an API, Git checkout, subscription, or case-by-case evidence remain registered even when no unattended download is defined.

## Storage conventions

- Raw snapshots: `raw_data/sources/<source-id>/<download-id>/<release>/<filename>` (local only; never commit raw source bytes).
- Provenance manifests: `data_manifests/sources/<source-id>/<download-id>/<release>.json` (tracked).
- Operational reports: `reports/sources/`.
- Registry and domain contracts: tracked in Git.

A snapshot is immutable. The manager refuses to overwrite either an existing raw file or its manifest. A new upstream release or intentional re-capture uses a new release identifier. Manifests record original/final URL, retrieval timestamp, source and download IDs, release, license/terms metadata, content type, byte count, and SHA-256.

## Commands

Run from the repository root:

```sh
uv run python -m tools.manage_sources list
uv run python -m tools.manage_sources show un_wpp_2024
uv run python -m tools.manage_sources check
uv run python -m tools.manage_sources check --online
uv run python -m tools.manage_sources acquire --source un_wpp_2024
uv run python -m tools.manage_sources acquire --all
uv run python -m tools.manage_sources status
uv run python -m tools.manage_sources licenses
```

- `list` lists registered sources and acquisition modes.
- `show` prints one complete source record.
- `check` verifies local snapshot/manifest presence, identity, size, and checksum.
- `check --online` additionally probes configured HTTPS download endpoints. Endpoint reachability is not proof that a dataset is valid or current.
- `acquire --source ID` captures every configured download for one source; `acquire --all` attempts every configured download. Batch runs continue after individual failures and return a non-zero exit status if any item fails.
- `status` reports local snapshot status.
- `licenses` reports recorded license classifications and terms links.

Acquisition is limited to explicitly configured direct HTTPS downloads. API, Git, manual, subscription, and per-country evidence sources are visible in the registry but are not guessed or silently downloaded. Their adapters/download definitions are added only when their protocol and validation contract are known.

## Safety and data governance

Acquisition does not parse/import data into SQLite, alter country identity, approve review proposals, or publish game assets. Those remain separate, explicit pipeline steps. A successful HTTP response is not dataset validation; provider-specific format, schema, coverage, identity crosswalk, and release checks are required before import.

License status is informational and does not block acquisition. Record whether terms are open, attribution-required, non-commercial, require commercial authorization, restrict redistribution, are proprietary/subscription, or remain unclear. Do not describe restricted or unverified material as open. License reporting does not grant rights; users must comply with the recorded source terms.

Natural Earth is registered for geography/cartography only and is not an accepted source for WP1.5 statistics or classifications. Raw snapshots remain outside Git; manifests and source metadata are versioned.

## Current migration boundary

The registry establishes the project-wide source catalogue and shared immutable HTTPS acquisition/checking service. Existing WP1.5 contracts and legacy refresh scripts remain compatibility consumers during the staged migration; they must be moved to source IDs and the shared service without changing candidate-generation, review-only, approval, or publication semantics. A source appearing in this registry is not evidence that its download URL, data coverage, or licensing has been independently validated.
