# IMF WEO and World Bank WDI country-year comparison

- Checked: 2026-11-05T10:32:20.288753+00:00
- Period: 2015–2025
- Read-only; IMF snapshot fixed, WDI API live/rolling; no policy or database changes

| Field | IMF | WDI | Matched countries | Matched country-years | IMF-only years | WDI-only years | Median absolute difference |
|---:|---|---|---:|---:|---:|---:|---:|
| 15 | NGDPD | NY.GDP.MKTP.CD | 192 | 2087 | 52 | 168 | 0.05% |
| 16 | NGDPDPC | NY.GDP.PCAP.CD | 192 | 2080 | 52 | 175 | 1.00% |
| 18 | PPPGDP | NY.GDP.MKTP.PP.CD | 189 | 2062 | 77 | 95 | 0.19% |
| 20 | PCPIPCH | FP.CPI.TOTL.ZG | 183 | 1951 | 186 | 28 | 0.27% |
| 21 | LUR | SL.UEM.TOTL.ZS | 108 | 1144 | 83 | 888 | 2.73% |

## Field 15: NGDPD vs NY.GDP.MKTP.CD

- Definition: nominal GDP at current prices
- WDI originating organization: Country official statistics, National Statistical Organizations and/or Central Banks;
National Accounts data files, Organisation for Economic Co-operation and Development (OECD);
Staff estimates, World Bank (WB)
- WDI source note: Gross domestic product is the total income earned through the production of goods and services in an economic territory during an accounting period. It can be measured in three different ways: using either the expenditure approach, the income approach, or the production approach. This indicator is expressed in current prices, meaning no adjustment has been made to account for price changes over time. This indicator is expressed in United States dollars.
- WDI API last updated: not supplied
- WDI national-estimate metadata: not applicable
- WDI national-estimate matched country-years: 0
- Mean absolute relative difference: 2.4843642809996314
- Median absolute relative difference: 0.045480664486207696
- 95th percentile absolute relative difference: 10.870480798718637
- Country-years with >5% absolute relative difference: 170
- Country-years with >20% absolute relative difference: 77
- Mean absolute difference (percentage points, fields 20/21): None
- IMF reporting-period counts: {'calendar_year': 1879, 'non_calendar_fiscal_year': 208, 'unknown': 0}
- Calendar-year-only sensitivity (January/December only): {'matched_country_year_count': 1879, 'relative_difference_observation_count': 1879, 'mean_absolute_relative_difference_percent': 2.5132547118480497, 'median_absolute_relative_difference_percent': 0.03998278603755004, 'p95_absolute_relative_difference_percent': 11.196914912231968, 'country_years_over_5_percent_difference': 145, 'country_years_over_20_percent_difference': 72, 'period_rule': 'Only IMF January/December observations are included; year labels are not shifted.', 'excluded_non_calendar_fiscal_year_count': 208, 'excluded_unknown_reporting_period_count': 0}
- Vintage caveat: IMF October 2026 fixed CSV versus live rolling WDI API response; not vintage-aligned

## Field 16: NGDPDPC vs NY.GDP.PCAP.CD

- Definition: GDP per capita at current prices
- WDI originating organization: Country official statistics, National Statistical Organizations and/or Central Banks;
National Accounts data files, Organisation for Economic Co-operation and Development (OECD);
Staff estimates, World Bank (WB)
- WDI source note: Gross domestic product is the total income earned through the production of goods and services in an economic territory during an accounting period. It can be measured in three different ways: using either the expenditure approach, the income approach, or the production approach. The core indicator has been divided by the general population to achieve a per capita estimate.This indicator is expressed in current prices, meaning no adjustment has been made to account for price changes over time. This indicator is expressed in United States dollars.
- WDI API last updated: not supplied
- WDI national-estimate metadata: not applicable
- WDI national-estimate matched country-years: 0
- Mean absolute relative difference: 4.58070428502279
- Median absolute relative difference: 1.0033473307587037
- 95th percentile absolute relative difference: 22.23389548493055
- Country-years with >5% absolute relative difference: 445
- Country-years with >20% absolute relative difference: 116
- Mean absolute difference (percentage points, fields 20/21): None
- IMF reporting-period counts: {'calendar_year': 1872, 'non_calendar_fiscal_year': 208, 'unknown': 0}
- Calendar-year-only sensitivity (January/December only): {'matched_country_year_count': 1872, 'relative_difference_observation_count': 1872, 'mean_absolute_relative_difference_percent': 4.333399871540333, 'median_absolute_relative_difference_percent': 0.9242369227204681, 'p95_absolute_relative_difference_percent': 19.467530569485636, 'country_years_over_5_percent_difference': 373, 'country_years_over_20_percent_difference': 92, 'period_rule': 'Only IMF January/December observations are included; year labels are not shifted.', 'excluded_non_calendar_fiscal_year_count': 208, 'excluded_unknown_reporting_period_count': 0}
- Vintage caveat: IMF October 2026 fixed CSV versus live rolling WDI API response; not vintage-aligned

## Field 18: PPPGDP vs NY.GDP.MKTP.PP.CD

- Definition: GDP at current PPP prices; benchmark compatibility requires review
- WDI originating organization: International Comparison Program (ICP), World Bank (WB), uri: https://www.worldbank.org/en/programs/icp/data, note: This information is for ICP’s PPPs utilized in WDI, publisher: International Comparison Program (ICP), date accessed: May 30, 2024, date published: May 30, 2024;
The Eurostat PPP Programme, Eurostat (ESTAT), uri: https://ec.europa.eu/eurostat/databrowser/explore/all/all_themes, publisher: Eurostat, date accessed: Periodical update;
The OECD PPP Programme, Organisation for Economic Co-operation and Development (OECD), uri: https://data-https://data-explorer.oecd.org/, publisher: OECD, date accessed: Periodical update;
Staff estimates, World Bank (WB);
National Accounts data files, Organisation for Economic Co-operation and Development (OECD);
World Economic Outlook database, International Monetary Fund (IMF)
- WDI source note: This indicator provides values for gross domestic product (GDP) expressed in current international dollars, converted by purchasing power parities (PPPs). PPPs account for the different price levels across countries and thus PPP-based comparisons of economic output are more appropriate for comparing the output of economies and the average material well-being of their inhabitants than exchange-rate based comparisons.  

Gross domestic product is the total income earned through the production of goods and services in an economic territory during an accounting period. It can be measured in three different ways: using either the expenditure approach, the income approach, or the production approach. This series has been linked to produce a consistent time series to counteract breaks in series over time due to changes in base years, source data and methodologies. Thus, it may not be comparable with other national accounts series in the database for historical years. This indicator is expressed in current prices, meaning no adjustment has been made to account for price changes over time. The PPP conversion factor is a currency conversion factor and a spatial price deflator. PPPs convert different currencies to a common currency and, in the process of conversion, equalize their purchasing power by eliminating the differences in price levels between countries, thereby allowing volume or output comparisons of GDP and its expenditure components.
- WDI API last updated: not supplied
- WDI national-estimate metadata: not applicable
- WDI national-estimate matched country-years: 0
- Mean absolute relative difference: 2.8555408952726196
- Median absolute relative difference: 0.18898207444304177
- 95th percentile absolute relative difference: 13.044639153342215
- Country-years with >5% absolute relative difference: 315
- Country-years with >20% absolute relative difference: 37
- Mean absolute difference (percentage points, fields 20/21): None
- IMF reporting-period counts: {'calendar_year': 0, 'non_calendar_fiscal_year': 0, 'unknown': 2062}
- Calendar-year-only sensitivity (January/December only): {'matched_country_year_count': 0, 'relative_difference_observation_count': 0, 'mean_absolute_relative_difference_percent': None, 'median_absolute_relative_difference_percent': None, 'p95_absolute_relative_difference_percent': None, 'country_years_over_5_percent_difference': 0, 'country_years_over_20_percent_difference': 0, 'period_rule': 'Only IMF January/December observations are included; year labels are not shifted.', 'excluded_non_calendar_fiscal_year_count': 0, 'excluded_unknown_reporting_period_count': 2062}
- Vintage caveat: IMF October 2026 fixed CSV versus live rolling WDI API response; not vintage-aligned

## Field 20: PCPIPCH vs FP.CPI.TOTL.ZG

- Definition: annual CPI inflation; period-average convention requires review
- WDI originating organization: International Financial Statistics database, International Monetary Fund (IMF)
- WDI source note: Inflation as measured by the consumer price index reflects the annual percentage change in the cost to the average consumer of acquiring a basket of goods and services that may be fixed or changed at specified intervals, such as yearly.
- WDI API last updated: not supplied
- WDI national-estimate metadata: not applicable
- WDI national-estimate matched country-years: 0
- Mean absolute relative difference: 18.674269717095044
- Median absolute relative difference: 0.2728997555010045
- 95th percentile absolute relative difference: 64.13292500000038
- Country-years with >5% absolute relative difference: 529
- Country-years with >20% absolute relative difference: 261
- Mean absolute difference (percentage points, fields 20/21): 0.42366428734192674
- IMF reporting-period counts: {'calendar_year': 0, 'non_calendar_fiscal_year': 0, 'unknown': 1951}
- Calendar-year-only sensitivity (January/December only): {'matched_country_year_count': 0, 'relative_difference_observation_count': 0, 'mean_absolute_relative_difference_percent': None, 'median_absolute_relative_difference_percent': None, 'p95_absolute_relative_difference_percent': None, 'country_years_over_5_percent_difference': 0, 'country_years_over_20_percent_difference': 0, 'period_rule': 'Only IMF January/December observations are included; year labels are not shifted.', 'excluded_non_calendar_fiscal_year_count': 0, 'excluded_unknown_reporting_period_count': 1951}
- Vintage caveat: IMF October 2026 fixed CSV versus live rolling WDI API response; not vintage-aligned

## Field 21: LUR vs SL.UEM.TOTL.ZS

- Definition: unemployment rate; methodology and IMF unit require review
- WDI originating organization: ILO Modelled Estimates database (ILOEST), International Labour Organization (ILO), uri: https://ilostat.ilo.org/data/bulk/, publisher: ILOSTAT, type: external database, date accessed: January 17, 2026
- WDI source note: Unemployment refers to the share of the labor force that is without work but available for and seeking employment.
- WDI API last updated: not supplied
- WDI national-estimate metadata: {'indicator_code': 'SL.UEM.TOTL.NE.ZS', 'api_last_updated': None, 'name': 'Unemployment, total (% of total labor force) (national estimate)', 'unit': '', 'source_note': 'Unemployment refers to the share of the labor force that is without work but available for and seeking employment. Definitions of labor force and unemployment differ by country.', 'source_organization': 'Labour Force Statistics database (LFS), International Labour Organization (ILO), uri: https://ilostat.ilo.org/data/bulk/, publisher: ILOSTAT, type: external database, date accessed: September 28, 2026', 'source_id': '2', 'source_name': 'World Development Indicators', 'topics': ['Social Protection & Labor'], 'metadata_url': 'https://api.worldbank.org/v2/indicator/SL.UEM.TOTL.NE.ZS?format=json'}
- WDI national-estimate matched country-years: 1001
- Mean absolute relative difference: 19.027275283818053
- Median absolute relative difference: 2.725964948067257
- 95th percentile absolute relative difference: 79.43698732289337
- Country-years with >5% absolute relative difference: 463
- Country-years with >20% absolute relative difference: 279
- Mean absolute difference (percentage points, fields 20/21): 0.883020104895105
- IMF reporting-period counts: {'calendar_year': 0, 'non_calendar_fiscal_year': 0, 'unknown': 1144}
- Calendar-year-only sensitivity (January/December only): {'matched_country_year_count': 0, 'relative_difference_observation_count': 0, 'mean_absolute_relative_difference_percent': None, 'median_absolute_relative_difference_percent': None, 'p95_absolute_relative_difference_percent': None, 'country_years_over_5_percent_difference': 0, 'country_years_over_20_percent_difference': 0, 'period_rule': 'Only IMF January/December observations are included; year labels are not shifted.', 'excluded_non_calendar_fiscal_year_count': 0, 'excluded_unknown_reporting_period_count': 1144}
- Vintage caveat: IMF October 2026 fixed CSV versus live rolling WDI API response; not vintage-aligned

## Interpretation limits

- A shared country-year is a numerical comparison, not proof of semantic equivalence.
- IMF values in Billions are converted to absolute dollars; GDP per capita and percentage series are not rescaled.
- IMF actual/estimate classification is only a hint from LATEST_ACTUAL_ANNUAL_DATA; fiscal-year labels and PPPGDP are unclassified.
- The CSV reports signed_difference (IMF minus WDI), absolute_difference, signed relative_difference_percent, and absolute_relative_difference_percent separately.
- Calendar-year sensitivity includes only IMF January/December reporting periods; fiscal-year and unknown-period observations are excluded without shifting year labels.
- WDI observation status is not inferred. WDI is retrieved live and may change between runs.
- For field 21, SL.UEM.TOTL.NE.ZS is included as a separate national-estimate diagnostic; it is not treated as interchangeable with the ILO-modelled SL.UEM.TOTL.ZS series.
- Field 21 retains country-specific IMF WEO unit, source, employment-definition, methodology-note, latest-actual and update-date metadata. Blank metadata remains unknown, not inferred.
- Fields 18, 20 and 21 require explicit definition review before a policy decision; PPP benchmark, CPI period convention and unemployment methodology/unit remain material caveats.
- `candidate_matrix.csv` is a rectangular project-identity × field × year grid; missing observations are explicit, and identity verification remains separately flagged.
- Identity rows are not considered approved unless both the identity record and ISO assignment are approved/verified; current proposals remain review-required.
- No source-selection, release, approval, or database action is performed.

## Complete candidate matrix

- Rows: 13310
- Project identities: 242
- Fields: 5
- Years per identity/field: 11
- Coverage states: {'both_sources_present': 9324, 'imf_only': 450, 'wdi_only': 1354, 'neither_source_present': 2182}
- Identity mapping states: {'mapped_review_required': 242}
