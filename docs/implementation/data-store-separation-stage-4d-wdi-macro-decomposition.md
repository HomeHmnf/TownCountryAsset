# Stage 4D — WDI macro-series decomposition

**Status:** implementation, owner-run tests, expanded snapshot acquisition, manifest audit, Project DB registration and diagnostic assessment completed; semantic disposition remains diagnostic only  
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

The six original comparison/diagnostic indicators remain the required base set. The snapshot loader accepts both the historical six-indicator capture and the expanded profile; when any supporting indicator is present, its metadata and complete observation bundle must both be present. Existing snapshots are not rewritten. This batch adds no new unemployment series and does not resolve field 21's IMF unit, population or methodology gate.

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

## HTTP retry hardening

The first owner acquisition attempt encountered a read timeout on an observation response; the proxychains attempt then encountered a TLS EOF while fetching indicator metadata. These are transport failures, not malformed-response or semantic-validation failures. The acquisition client now uses a 120-second per-request timeout and up to five retries for transient transport errors and HTTP 408/425/429/5xx responses, with exponential backoff starting at two seconds. Non-transient 4xx responses fail immediately; terminal errors report the actual number of requests made rather than the configured retry ceiling. A regression test checks that a 404 stops after one request and reports one attempt. Retry controls are exposed as `--timeout`, `--retries` and `--retry-delay`. Failed attempts can leave partial raw directories without manifests; they are not valid acquisitions and must not be registered.

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

- World Bank, [GDP (current LCU), NY.GDP.MKTP.CN](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/NY.GDP.MKTP.CN).
- World Bank, [DEC alternative conversion factor, PA.NUS.ATLS](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/PA.NUS.ATLS).
- World Bank, [GDP PPP conversion factor, PA.NUS.PPP](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/PA.NUS.PPP).
- World Bank, [Consumer price index, FP.CPI.TOTL](https://databank.worldbank.org/metadataglossary/world-development-indicators/series/FP.CPI.TOTL).
- World Bank, [WDI API response metadata and observation status](https://datahelpdesk.worldbank.org/knowledgebase/articles/1886674-new-features-and-enhancements-in-the-v2-api).


## Owner-run acquisition and assessment record (2026-11-07)

The expanded 2014–2025 WDI capture and 2015–2025 decomposition completed successfully.

| Property | Result |
|---|---|
| Snapshot ID | `api_snapshot_20261107T161129160851Z` |
| Retrieved at | `2026-11-07T16:12:07.812622+00:00` |
| Manifest | `data_manifests/sources/world_bank_wdi/wdi_selected_macro_indicators/api_snapshot_20261107T161129160851Z.json` |
| Manifest SHA-256 | `8e91b8ce5269bb387374e3b653038af6a5fc7d65fb98a7f570f6e05f536e8bf5` |
| Raw response artifacts | 26 |
| Raw response bytes | 8,885,684 |
| Country/region catalogue records | 296 |
| Indicators | 12 (six comparison/diagnostic base indicators plus six supporting indicators) |
| Observation rows | 3,192 per indicator for 2014–2025 |
| Decomposition period | 2015–2025 |
| Decomposition rows | 2,662 (242 identities × 11 years) |

The read-only manifest audit examined both WDI manifests: two valid manifests, 40 artifacts, zero errors. The new snapshot was registered in the Project DB as acquisition ID 7 with 26 artifacts, status `acquired` and integrity status `verified`. The acquisition key is the manifest path; its stored manifest SHA-256 matches the value above. Project DB integrity returned `ok`; the foreign-key check returned no violations. The earlier six-indicator acquisition ID 6 was not overwritten.

The decomposition report is `reports/sources/wdi-macro-decomposition/20261107T161349Z/`, containing `assessment.json`, `assessment.md` and `decomposition_matrix.csv`. It records the snapshot ID, retrieval timestamp and manifest hash. All 2,662 rows remain blocked by the separate identity-governance gate. This is not a calculation-failure count. The assessment fetched no additional source responses and wrote no database, approval, source-selection, release or Game DB state. The owner confirmed the focused tests and compilation passed after the retry-hardening correction; no aggregate test count is recorded here.

### Arithmetic consistency findings

Across the selected country-case rows, the WDI published values are reproduced by the corresponding captured inputs to floating-point precision where the inputs exist:

- current-USD GDP aligns with current-LCU GDP divided by the DEC alternative conversion factor;
- PPP GDP aligns with current-LCU GDP divided by the GDP PPP conversion factor;
- GDP per capita aligns with current-USD GDP divided by total population;
- WDI inflation aligns with CPI-index year-on-year growth where both years are present.

Turkmenistan has no official exchange-rate observations in this capture; its current-USD arithmetic is reproduced using the DEC alternative factor. These identities demonstrate internal arithmetic consistency in the captured series, not proof of the provider's internal construction pipeline.

### Country-case comparison against October 2026 IMF WEO

The following differences are medians over the 11-year 2015–2025 comparison window. A negative value means WDI is below IMF WEO; a positive value means WDI is above it.

| Country | WDI vs IMF nominal GDP | WDI vs IMF PPP GDP | WDI vs IMF GDP per capita | Additional finding |
|---|---:|---:|---:|---|
| Central African Republic | -34.07% | -34.98% | -34.65% | CPI median difference is 0.00 percentage points; common GDP-level gap persists across nominal and PPP measures. |
| Guinea | -34.44% | -36.38% | -31.46% | CPI differences are close in much of 2016–2022 but widen in 2015 and 2023–2025; national-accounts vintage/rebasing remains a material gate. |
| Turkmenistan | -35.57% | +0.95% | -41.79% | Official-rate series is absent; alternative conversion factor rises from 3.5 in 2015 to 5.48 in 2018, while the nominal USD gap widens. This is consistent with a conversion-factor issue but does not establish the WEO conversion method. |
| Zimbabwe | -19.16% | -19.98% | -17.76% | Highly non-uniform: 2017 WDI is 64.54% above IMF nominal GDP and 151.39% above IMF PPP GDP; CPI comparison diverges sharply in 2022 and WDI inflation/index observations are absent for 2023–2025. |
| Samoa | -0.01% | +14.45% | -3.99% | Nominal GDP aligns closely; PPP has a stable positive difference. CPI differences vary materially by year. |
| Tonga | -0.08% | +12.76% | -4.64% | Nominal GDP aligns closely; PPP has a stable positive difference. CPI differences vary materially by year. |
| Palau | +0.08% | +19.87% | -0.94% | Nominal GDP and GDP per capita align closely; PPP has a stable positive difference. |

These case comparisons do not establish that the two providers use identical national-accounts vintages, population denominators, reporting periods or PPP benchmarks. In particular:

- CAR and Guinea retain a large common nominal/PPP level gap; the arithmetic decomposition does not explain the underlying national-accounts level difference.
- Turkmenistan's PPP comparison is much closer than its nominal USD comparison, making exchange-rate conversion a priority for further source-level investigation. The missing official-rate observations and alternative-factor series are evidence inputs, not proof of WEO's conversion.
- Zimbabwe's 2017 outlier and later currency/conversion-factor changes require year-specific treatment; a single median conceals material breaks.
- Samoa, Tonga and Palau show close nominal GDP but stable PPP-level differences, indicating that nominal USD conversion alone does not account for their PPP gaps.
- CPI-index growth verifies the WDI inflation arithmetic where present, but differences from IMF WEO remain subject to period convention and vintage alignment.

### Stage 4D disposition

The decomposition narrows the remaining research questions but does not close the Stage 4 field gates. Keep IMF WEO source priority unchanged for fields 15, 16, 18 and 20. Field 21 remains outside this macro-series decomposition and its existing unit, population, reference-period and methodology gates remain open. No country identity was promoted; all identities remain review-required. No semantic approval, release promotion, retention action or Game DB write occurred.


## 12. CAR and Guinea source-vintage findings (2026-11-07)

The country-level decomposition has now been reconciled with existing CAR primary-source files and official Guinea INS/UNSD publications.

### Guinea

WDI current-LCU GDP `NY.GDP.MKTP.CN` matches the legacy INS/1993 SNA series at published rounding precision for 2018–2022 (106,845; 123,458; 134,760; 159,337; 170,314 billion GNF). It remains 30.76–39.66% below the new INS 2018-base SNA 2008 series through 2024. The June 2025 INS note classifies 2018–2020 as definitive and 2021–2024 as rapid estimates. A separate October 2025 MPCI publication reports a slightly different 2018 base-year GDP; the two official publication values are retained as separate vintages. UNSD's January 2026 GDP metadata explicitly identifies INS as the source for nominal GDP values in 2018–2024.

For 2024, WDI and UNSD population are identical (14,754,785), while GDP per capita is US$1,694.95 in WDI versus US$2,473 in UNSD and US$2,487.36 in WEO. The 2024 per-capita gap is principally numerator vintage, not a population-denominator mismatch. This finding is not generalized to every year.

### Central African Republic

WDI current-LCU GDP is 33.36%, 34.86% and 35.08% below definitive ICASEES 2019-base SNA 2008 accounts in 2019–2021. ICASEES revised GDP matches IMF WEO `CAF.NGDP.A` exactly at published precision. WDI official and DEC alternative conversion factors are effectively identical in these years, so the gap is already in the local-currency GDP numerator. WDI is not exactly equal to ICASEES's separate historical 2019 workbook value; do not describe it as a match to that old series.

CAR population also differs: ICASEES reports 5,360,271 / 5,464,907 / 6,091,097 in 2019–2021, versus WDI 4,944,703 / 5,026,628 / 5,112,100. Field 16 therefore contains both GDP-numerator and population-denominator differences.

### Interpretation

These findings strongly identify national-accounts vintage/compilation differences as a major component of CAR and Guinea field 15 gaps. They do not establish the exact WDI ingestion history, prove the independent compilation lineage of WEO, resolve all population years or close the PPP benchmark/factor gate. IMF priority remains unchanged. Guinea's INS PDF and legacy yearbook have since been captured as separate immutable Project DB acquisition events (IDs 8 and 9; see the [acquisition record](../data-sources/guinea-ins-national-accounts-acquisition.md)). Both manifest artifacts passed byte-integrity audit and registration. Their original manual-download timestamps are explicitly labelled filesystem-mtime based. This establishes provenance capture, not statistical validation or source approval.

See [Guinea national-accounts vintage reconciliation](../data-sources/guinea-national-accounts-vintage-reconciliation.md), [field 15/16 assessment](../data-sources/field-15-16-gdp-comparability-assessment.md) and [ICASEES GDP reconciliation](../data-sources/icasees/gdp-scale-and-weo-reconciliation.md).


## Turkmenistan evidence acquisition scope (2026-11-07)

The Turkmenistan follow-up is scoped to five dated publications: IMF Working Paper 2023/207; TurkmenStat notices of 17 January 2025 and 23 June 2026; and IMF Article IV mission statements of 10 June 2025 and 22 June 2026. The WDI snapshot confirms that current-USD GDP equals current-LCU GDP divided by the DEC alternative conversion factor for 2015–2025, while the official FX indicator is missing. The factor rises from 3.98 in 2017 to 5.48 in 2018; the WDI/WEO GDP gap widens to 36.13% in 2018 and 46.77% in 2021. This is an arithmetic and temporal association, not proof that DEC represents the parallel-market rate. Automated acquisition, source/dataset registration and owner validation are tracked in the dedicated acquisition document.


### Turkmenistan primary-evidence capture status (2026-11-07)

Three of the five scoped publications have now been captured and passed owner-run manifest integrity audit: IMF Working Paper 2023/207 (XML), TurkmenStat's January 2025 notice (HTML), and TurkmenStat's June 2026 notice (HTML). Both IMF Article IV mission-statement endpoints returned HTTP 403; no raw files or manifests were created for those two publications. The source catalogue now contains 34 sources/106 URLs and the dataset catalogue 13 datasets/11 streams. These syncs created no acquisition rows. The guarded processing orchestrator and remaining Project DB registration gate are documented in [Turkmenistan evidence acquisition](../data-sources/turkmenistan-macroeconomic-evidence-acquisition.md). This is evidence capture/provenance work only; it does not resolve the conversion-factor interpretation or change the Stage 4 field dispositions.


### Turkmenistan evidence provenance registration (2026-11-08)

The guarded Turkmenistan processing workflow passed its owner-run tests (15 passed across the acquisition and orchestration suites), both manifest audits, and the three-event registration preflight. The explicit registration run created Project DB acquisition IDs 10–12:

- ID 10: `national_accounts_methodology_2025`, one artifact, status `acquired`.
- ID 11: `statistical_system_reform_2026`, one artifact, status `acquired`.
- ID 12: `gdp_statistical_shortcomings_wp_2023_207`, one artifact, status `acquired`.

The workflow reported Project DB written and Game DB not written. This is provenance registration only; the Turkmenistan conversion-factor interpretation remains unresolved, and no identity, semantic or source-policy gate is approved. The two IMF Article IV statements remain acquisition gaps after HTTP 403 responses. See [Turkmenistan acquisition and provenance workflow](../data-sources/turkmenistan-macroeconomic-evidence-acquisition.md).


### Turkmenistan nominal-GDP conversion reconciliation (2026-11-08)

The country-specific analysis materially narrows the Turkmenistan field 15 gap. WDI current-USD GDP is reconstructed from WDI current-LCU GDP and the DEC alternative conversion factor in all 11 years. WDI current-LCU GDP divided by 3.5 TMT/USD reconstructs October 2026 WEO current-USD GDP to displayed precision in 2015–2021 and 2024–2025. The implied factor differs in 2022 (3.5984) and 2023 (3.3703), leaving residuals of +2.81% and -3.70% relative to WEO when the WDI LCU numerator is converted at 3.5. The displayed ratios use rounded values; the decomposition tool now emits an exact-value IMF-implied conversion-factor column for the next owner-run report.

The IMF 2023 working paper states that the official rate remained 3.5 from 2015 and describes a parallel-market rate reaching about 38 in April 2021. The WDI DEC factor peaked at 6.5759 in 2021; it is not the official rate or the paper's cited parallel-market rate. The DEC factor's provider-specific construction remains unknown. The paper's combined deflator concerns real-GDP estimation and is not proof of the WEO nominal-USD conversion procedure.

TurkmenStat's January 2025 notice establishes phased modernization of national-accounts methods/software, while the June 2026 notice describes 2026–2027 planned assistance for ICP, 2025 SNA national accounts and digital surveys. Neither notice gives a numerical historical GDP bridge. Field 16 population and field 18 PPP/ICP remain separate gates. See [Turkmenistan GDP conversion-basis reconciliation](../data-sources/turkmenistan-gdp-conversion-reconciliation.md).
