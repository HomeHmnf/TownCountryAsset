# Zimbabwe national-accounts and macro-series reconciliation

## Scope and evidence

This assessment compares the two acquired ZIMSTAT national-accounts workbooks with the October 2026 IMF WEO and the frozen World Bank WDI snapshot used by the project. It is a diagnostic reconciliation only. It does not approve a source, change source-selection policy, or apply values to the Game DB.

The two ZIMSTAT publications are distinct:
- GDP Trends 2009–2018 (legacy XLS).
- GDP tables 2019–2024 (June 2025 XLSX; revised national accounts).

The newer workbook contains current-price ZWL tables for 2019–2023, explicitly marked as after Economic Census adjustment; constant-price ZWL tables for 2019–2023 with 2023=100; and current- and constant-price ZWG tables for 2023–2024. Its ZWG constant-price tables also use 2023=100. Currency labels and price bases must be retained separately.

## 2023 revision

The workbook's 2023 comparison reports:
- GDP at basic prices: ZWL 124.104tn old estimate and ZWL 159.188tn revised estimate (+28.27%).
- Net taxes on products: ZWL 9.600tn in both estimates.
- GDP at market prices: ZWL 133.703tn old estimate and ZWL 168.788tn revised estimate (+26.24%).

The revised 2019–2023 current-price production table reports 2023 GDP at market prices of ZWL 168.788tn. This is the revised series, not the old estimate.

## Historical nominal LCU reconciliation, 2019–2024

The IMF WEO October 2026 country metadata describes redenomination of historical ZWL national-accounts data into ZiG/ZWG using 2,498.7242 ZWL per ZiG. Applying that factor to the revised ZIMSTAT current-price ZWL GDP observations reproduces the WDI current-LCU GDP series to the published precision for 2019–2023.

**Unit caution:** the converted amounts are not all billions. The converted figures are approximately:
- 2019: ZWG 129.740 million.
- 2020: ZWG 820.409 million.
- 2021: ZWG 1.858 billion.
- 2022: ZWG 7.384 billion.
- 2023: ZWG 67.559 billion.

These align with WDI current-LCU observations of approximately 129,739,500; 820,408,600; 1,857,829,500; 7,383,888,700; and 67,558,760,600 respectively. WEO current-LCU GDP, reported in billions, is consistent at its published precision.

For 2023, the newer workbook's current-price ZWG GDP is ZWG 67.558759bn, agreeing with WDI's approximately ZWG 67.558761bn. For 2024, ZIMSTAT reports ZWG 822.938289bn and WDI reports approximately ZWG 822.592860bn, a difference of about -0.042% relative to ZIMSTAT. The WEO current-LCU observation is also close at its published precision.

This is strong evidence that the 2019–2023 nominal LCU discrepancy is explained by the historical redenomination treatment. It is not a claim that ZWL and ZWG values can be concatenated without conversion, nor does it validate every earlier historical observation.

## Real GDP and cross-approach consistency

The revised constant-price ZWL production and expenditure tables both use 2023=100 and agree on market-price real GDP growth:
- 2020: -7.81695%.
- 2021: +8.46802%.
- 2022: +6.13926%.
- 2023: +5.33673%.

For 2024, the ZWG constant-price production and expenditure tables use 2023=100. Market-price GDP growth is 1.742381% in the production and expenditure tables. The income approach reports 1.742395%. Basic-price GDP growth is approximately 1.65055% in both production and income approaches. The tiny market-price difference is consistent with rounding in the published tables.

These tables support continuity of the real-volume reference base across the ZWL and ZWG table presentations at 2023=100. They do not establish a nominal exchange-rate bridge by themselves.

## Earlier 2009–2018 USD presentation

The legacy ZIMSTAT workbook labels its main GDP-at-current-prices series in US dollars and separately presents RTGS-dollar columns for 2017–2018. Its note describes use of a parallel exchange rate after the official exchange rate was introduced in February 2019.

The main USD values for 2015–2016 are close to WDI current-USD GDP (about 0.05% difference). For 2017–2018, WDI current-USD GDP differs materially from the legacy ZIMSTAT main USD figures and does not simply match the separate RTGS columns. Exact WDI lineage for those years remains unresolved. Do not infer that the ZIMSTAT USD, RTGS and WDI series are interchangeable.

## PPP discrepancy remains unresolved

The nominal LCU reconciliation does not resolve PPP GDP differences:
- WDI PPP GDP has a pronounced 2017 spike (about USD 159.33bn), while WEO reports about USD 63.379bn.
- For 2019–2025, WDI PPP GDP is materially below WEO; the gap is around 21% for 2021–2025.
- The WEO PPP methodology uses ICP 2017–2021 benchmark information and extrapolation. The WDI PPP factor series and the WEO PPP factor are not demonstrated to be vintage- or methodology-equivalent for Zimbabwe.

The constant-price national-accounts tables are not a substitute for an ICP benchmark or PPP conversion-factor lineage. Retain this as an open field-18 comparability issue.

## Disposition

1. Treat the revised ZIMSTAT 2019–2023 nominal ZWL series, the redenomination factor, and the WDI/WEO current-LCU series as reconciled at published precision, with explicit unit scaling.
2. Treat the 2023–2024 ZWG current-price series as independently corroborating WDI/WEO nominal LCU GDP.
3. Use ZIMSTAT constant-price tables as country-specific evidence for real GDP growth, retaining their 2023=100 base and approach labels.
4. Keep 2015–2018 USD/RTGS lineage unresolved.
5. Keep PPP GDP and PPP-factor comparability unresolved.
6. Make no source-selection, approval, release-promotion, canonical-database, or Game DB changes on the basis of this diagnostic alone.

## Provenance

The two ZIMSTAT workbook acquisitions are registered in the Project DB:
- Acquisition 13: `gdp_tables_2019_2024`, acquired, integrity verified, one artifact.
- Acquisition 14: `gdp_trends_2009_2018`, acquired, integrity verified, one artifact.

The owner reported Project DB integrity `ok` and no foreign-key violations. Raw workbook files remain local-only; timestamped acquisition manifests are tracked. See [ZIMSTAT workbook acquisition](zimbabwe-national-accounts-acquisition.md) for the repeatable acquisition and registration workflow.
