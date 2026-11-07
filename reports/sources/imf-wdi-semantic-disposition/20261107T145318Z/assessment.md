# IMF WEO–WDI semantic disposition matrix

- Rows: 13310
- Project identities: 242
- All rows remain diagnostic and not approved.
- Identity review remains a separate gate.
- Unknown observation status is preserved; no estimate/projection inference is made.

## Field-level gates

| Field | Concept disposition | Required gate |
|---:|---|---|
| 15 | qualified_comparability_nominal_gdp_current_usd | reconcile_national_accounts_vintage_and_usd_conversion |
| 16 | qualified_comparability_nominal_gdp_per_capita | reconcile_gdp_numerator_population_denominator_and_population_universe |
| 18 | not_demonstrated_comparable_current_ppp_dollars | reconcile_icp_benchmark_ppp_factor_and_nominal_gdp_input |
| 20 | not_demonstrated_comparable_annual_cpi_inflation | confirm_provider_reference_period_and_annual_average_convention |
| 21 | non_equivalent_products_in_general_case | confirm_imf_unit_population_reference_period_and_method |

## Country evidence cases

| Country | Field | Case | Disposition |
|---|---:|---|---|
| Bahrain | 21 | bahrain_reference_period_settled | settled_likely_reference_period_mismatch_do_not_reopen |
| Central African Republic | 15 | car_national_accounts_rebasing | newer_2019_base_sna2008_accounts_require_vintage_alignment |
| Central African Republic | 16 | car_gdp_population_denominator | field_15_national_accounts_and_population_vintage_reconciliation_required |
| Central African Republic | 18 | car_ppp_decomposition | nominal_gdp_and_ppp_factor_decomposition_open |
| Guinea | 15 | guinea_sna2008_2018_base_rebasing | rebased_national_accounts_support_woe_direction_but_vintage_alignment_open |
| Guinea | 16 | guinea_gdp_population_denominator | field_15_rebasing_and_population_denominator_vintage_review_required |
| Guinea | 18 | guinea_ppp_decomposition | nominal_gdp_and_ppp_factor_decomposition_open |
| Moldova | 21 | moldova_2025_lfs_redesign | national_lfs_corroborates_2024_2025_preserve_2025_break_in_series |
| Palau | 20 | palau_fiscal_year_september_end | fiscal_year_correspondence_supported_2023_2025_earlier_years_open |
| Philippines | 21 | philippines_annualized_lfs | psa_annual_lfs_corroborates_2023_2025_preserve_2025_preliminary_status |
| Samoa | 20 | samoa_fiscal_year_july_june | fiscal_year_ending_year_correspondence_supported_2021_2024_2025_residual_open |
| Tonga | 20 | tonga_fiscal_year_july_start_and_cpi_rebase | fiscal_year_correspondence_supported_2022_2025_historical_vintage_open |
| Turkmenistan | 15 | turkmenistan_exchange_rate_regime | dual_exchange_rate_and_conversion_factor_require_reconciliation |
| Turkmenistan | 16 | turkmenistan_gdp_population_denominator | exchange_rate_conversion_and_population_denominator_review_required |
| Zimbabwe | 18 | zimbabwe_icp_2017_benchmark | 2017_ppp_benchmark_and_woe_special_conversion_need_reconciliation |

## Coverage and interpretation

This artifact enriches the supplied candidate matrix; it does not recompute observations or differences. Country cases are bounded to the evidence recorded in the linked assessment documents. A case disposition does not automatically validate every year in that country-field series.

The IMF latest-actual metadata remains a hint; years after that boundary are not automatically separated into estimates and projections. WDI blank observation status remains unclassified. Missing WDI observations are labelled missing, not estimated.

No identity was promoted, no source policy changed, no approval was created, no release was promoted, and neither database was written.
