# WDI WP1.5 area and population-density acquisition

**Status:** acquisition and read-only candidate-validation workflow implemented; no live acquisition or semantic approval implied.  
**Dataset:** `wdi_wp1_5_area` (separate from `wdi_selected_macro_indicators`)  
**Fields:** 3, 33 and 34.

## Scope and definitions

| WP1.5 field | WDI indicator | Canonical unit | Definition boundary |
|---:|---|---|---|
| 3 | `EN.POP.DNST` | people/km² | Population density per square kilometre of land area |
| 33 | `AG.SRF.TOTL.K2` | km² | Surface area, including inland water and some coastal waterways |
| 34 | `AG.LND.TOTL.K2` | km² | Land area, excluding inland water |

Do not substitute surface area for land area. Population density is a published WDI measure and is not recomputed from the project's population and area values.

This is a separate rolling API snapshot. It must not be added to or overwrite the historical macro-comparison snapshot. Raw provider responses are local-only; manifests and reports are tracked.

## 1. Capture

Run from the repository root:

```fish
uv run python -m tools.acquire_world_bank_wdi_wp1_5_area capture --start-year 2015 --end-year 2025
```

If the network requires the already configured proxy:

```fish
proxychains uv run python -m tools.acquire_world_bank_wdi_wp1_5_area capture --start-year 2015 --end-year 2025
```

The capture stores WDI source metadata, every page of the country catalogue, metadata for all three indicators, and every observation page. Each response is preserved byte-for-byte with request/final URL, parameters, headers, retrieval timestamp, HTTP status, byte count and SHA-256. Pagination changes, malformed responses, and non-WDI indicator metadata abort capture. Existing timestamped paths are never overwritten.

Output roots:

- Raw: `raw_data/sources/world_bank_wdi/wdi_wp1_5_area/<snapshot_id>/`
- Manifest: `data_manifests/sources/world_bank_wdi/wdi_wp1_5_area/<snapshot_id>.json`
- Acquisition report: `reports/sources/world-bank-wdi-wp1-5-area/<snapshot_id>/`

## 2. Prepare an explicit identity crosswalk

Candidate validation requires a separately reviewed JSON crosswalk. The dataset identifier must be `world_bank_wdi_wp1_5_area`; each mapping's `source_id` is the WDI ISO3 code, and `game_id` is the persistent project identity.

Example shape (illustrative only; not a real mapping):

```json
{
  "schema_version": 1,
  "dataset": "world_bank_wdi_wp1_5_area",
  "source_key": "world_bank_wdi",
  "mappings": [
    {
      "game_id": "tc_00000000000000000000000000000000",
      "source_id": "AAA",
      "match_method": "reviewed_manual",
      "evidence_url": "https://example.org/identity-evidence"
    }
  ]
}
```

Use only explicit authoritative or reviewed mappings. Do not generate mappings by matching country names, by assuming ISO3 equals the registry's ISO field, or by silently dropping territories and disputed entities. Partial crosswalks are permitted; unmapped provider observations remain visible in the candidate CSV and report. The validator checks mapped `game_id` values against `config/country_identity_registry.json`.

## 3. Validate and produce candidates

After capture and crosswalk review, set the exact manifest path:

```fish
set manifest data_manifests/sources/world_bank_wdi/wdi_wp1_5_area/api_snapshot_YYYYMMDDTHHMMSSffffffZ.json
uv run python -m tools.acquire_world_bank_wdi_wp1_5_area validate --manifest $manifest --crosswalk data/manual/source_crosswalks/world_bank_wdi_wp1_5_area.json
```

The validator first verifies every raw artifact's SHA-256 and byte count, source identity, all three indicator bundles, and complete country/observation pagination. It then:

- excludes WDI aggregates using the captured country catalogue's region classification;
- rejects duplicate ISO3/year observation keys and flags invalid, non-finite or out-of-range values;
- retains null-row counts and missing coverage rather than filling values;
- selects the latest non-null observation independently for each indicator and ISO3, retaining the reference year and raw `obs_status`;
- maps ISO3 to `game_id` only through the supplied crosswalk;
- checks surface area against land area only when both selected observations have the same reference year.

Candidate output is written under `reports/sources/world-bank-wdi-wp1-5-area/<snapshot_id>/candidate_validation/`, including `assessment.json`, `assessment.md` and `wdi_wp1_5_area_candidates.csv`.

A blank `obs_status` is not interpreted as actual. Different indicators can have different latest reference years. The same-year surface/land check is a consistency diagnostic, not an assertion that all country areas must match an external geometry dataset.

## 4. Review and approval boundary

This workflow does **not**:

- register the acquisition in the Project DB;
- write to the canonical Game DB;
- create or apply an approval;
- change field-source selection or source priority;
- infer missing values, periods, status, or identities;
- establish third-party licensing permission.

Review the captured indicator metadata, originating organisations, source notes, reference years, coverage, missingness, anomalies, crosswalk coverage, and the indicator-level licensing terms before preparing any import/review artifact. The WDI dataset's default CC BY terms do not by themselves establish redistribution rights for third-party-originated series.

## 5. Tests

```fish
uv run python -m pytest -q tests/test_world_bank_wdi_wp1_5_area.py tests/test_world_bank_wdi_snapshot.py
```

The new tests use mocked provider responses. They verify snapshot separation, immutable raw-byte integrity, refusal to overwrite, explicit crosswalk use, and rejection of crosswalk dataset mismatch. They do not replace a live owner-run acquisition or provider/licensing review.
