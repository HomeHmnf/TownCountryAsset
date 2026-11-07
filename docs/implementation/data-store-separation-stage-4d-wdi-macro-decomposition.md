# Stage 4D — WDI macro-series decomposition

**Status:** implementation committed; owner-run tests and new acquisition pending  
**Branch:** `work/compiler-hardening`  
**Purpose:** add supporting WDI series and arithmetic diagnostics to isolate candidate GDP, PPP, population and CPI relationships without treating those relationships as proof of provider methodology.

## Scope

The original frozen comparison remains unchanged. Stage 4D extends future WDI snapshots with six supporting series:

| Indicator | Role in assessment |
|---|---|
| `NY.GDP.MKTP.CN` | Current-price GDP in local currency |
| `PA.NUS.FCRF` | Official exchange rate, LCU per US$ |
| `PA.NUS.ATLS` | DEC alternative conversion factor, LCU per US$ |
| `PA.NUS.PPP` | GDP PPP conversion factor, LCU per international dollar |
| `SP.POP.TOTL` | Total population |
| `FP.CPI.TOTL` | Consumer price index |

The six original comparison/diagnostic indicators remain the required base set. The snapshot loader accepts both the historical six-indicator capture and the expanded profile; when any supporting indicator is present, its metadata and complete observation bundle must both be present. Existing snapshots are not rewritten.

The expanded capture stores all 12 indicator metadata and observation responses, raw-byte fingerprints, request metadata, pagination, retrieval timestamps and country metadata. Country metadata now also exposes the provider's special notes, income level, lending type and capital city to the diagnostic assessment while retaining the original raw response.

## Diagnostic calculations

For each project identity and year, the assessment attempts:

1. `GDP current LCU / official exchange rate` — official-rate arithmetic cross-check against WDI current-USD GDP.
2. `GDP current LCU / DEC alternative conversion factor` — alternative-factor sensitivity diagnostic.
3. `GDP current LCU / GDP PPP conversion factor` — implied current international-dollar GDP.
4. `WDI GDP current US$ / WDI population total` — GDP-per-capita arithmetic cross-check.
5. `(CPI index[t] / CPI index[t-1] - 1) × 100` — annual CPI-index growth diagnostic.

The CSV retains the source inputs, derived values, relative/percentage-point differences, IMF WEO comparison values, supporting-series observation-status strings and country special notes. Missing observations and zero denominators remain null. A full country × year grid is emitted for the requested identity universe.

## Interpretation constraints

- These are arithmetic checks, not proof of the exact construction used by WDI or IMF.
- `PA.NUS.ATLS` is the DEC alternative conversion factor used in the Atlas method. It must not be assumed to convert `NY.GDP.MKTP.CD`.
- Official exchange rates, alternative conversion factors, national accounts and PPP factors can have different reference periods, source vintages and compilation methods.
- GDP per capita depends on a population denominator whose reference date and universe may not match the denominator used by the published series.
- CPI index growth may differ from the inflation series because of index conventions, annual averaging and source-vintage revisions.
- The WDI snapshot remains a timestamped capture of a rolling API, not a provider-declared vintage aligned with the October 2026 WEO export.
- WDI observation status is preserved but not interpreted; blank status is not actual status.
- Every country identity remains subject to the separate identity-governance gate.
- No source priority, country override, approval, release state or Game DB value is changed.

## Owner-run validation

Focused tests and compilation:

```fish
uv run --extra dev python -m pytest -v \
    tests/test_world_bank_wdi_snapshot.py \
    tests/test_wdi_macro_decomposition.py \
    tests/test_project_dataset_catalogue.py \
    tests/test_imf_weo_wdi_comparison.py

uv run python -m compileall -q \
    tools/acquire_world_bank_wdi_snapshot.py \
    tools/assess_wdi_macro_decomposition.py
```

Acquire a fresh capture with one prior year for the CPI index growth calculation:

```fish
uv run python -m tools.acquire_world_bank_wdi_snapshot \
    --start-year 2014 \
    --end-year 2025
```

Then audit, synchronize and register the new manifest:

```fish
set manifest (find data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators -type f -name '*.json' | sort | tail -n 1)

uv run python -m tools.audit_acquisition_manifests \
    --manifest-dir data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators \
    --format json

uv run python -m tools.sync_project_dataset_catalogue

uv run python -m tools.register_project_acquisitions \
    --manifest-dir data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators
```

Only if the manifest audit is clean, run the read-only decomposition:

```fish
uv run python -m tools.assess_wdi_macro_decomposition \
    --snapshot-manifest $manifest \
    --start-year 2015 \
    --end-year 2025
```

The assessment writes a timestamped report under `reports/sources/wdi-macro-decomposition/` containing `decomposition_matrix.csv`, `assessment.json` and `assessment.md`.

## Acceptance criteria

- All historical six-indicator snapshots still load and remain immutable.
- New captures include all six base and six supporting indicator bundles, with metadata and pagination verified.
- A missing half of an optional supporting bundle is rejected.
- Derived values are computed only with finite numeric inputs and non-zero denominators.
- CPI growth uses the prior-year index, requiring a capture that begins one year before the assessment period.
- Raw WDI status strings, country special notes and IMF observations are retained.
- All project identities remain review-required unless already verified by the identity registry.
- The report is diagnostic only and records no database, policy, approval or Game DB side effects.

## Source metadata references

- World Bank, [GDP (current LCU), NY.GDP.MKTP.CN](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/viewall).
- World Bank, [DEC alternative conversion factor, PA.NUS.ATLS](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/PA.NUS.ATLS).
- World Bank, [GDP PPP conversion factor, PA.NUS.PPP](https://databank.worldbank.org/metadataglossary/World-Development-Indicators/series/PA.NUS.PPPC.RF).
- World Bank, [Consumer price index, FP.CPI.TOTL](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/FP.CPI.TOTL).
- World Bank, [WDI API response metadata and observation status](https://datahelpdesk.worldbank.org/knowledgebase/articles/1886674-new-features-and-enhancements-in-the-v2-api).
