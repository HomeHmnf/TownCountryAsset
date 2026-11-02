# IMF WEO and World Bank WDI country-year comparison

- Checked: 2026-11-02T09:01:06.810407+00:00
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
- Mean absolute relative difference: 2.4843642809996314
- Median absolute relative difference: 0.045480664486207696
- 95th percentile absolute relative difference: 10.870480798718637
- Country-years with >5% relative difference: 170
- Mean absolute difference (percentage points, fields 20/21): None
- Vintage caveat: IMF October 2026 fixed CSV versus live rolling WDI API response; not vintage-aligned

## Field 16: NGDPDPC vs NY.GDP.PCAP.CD

- Definition: GDP per capita at current prices
- WDI originating organization: Country official statistics, National Statistical Organizations and/or Central Banks;
National Accounts data files, Organisation for Economic Co-operation and Development (OECD);
Staff estimates, World Bank (WB)
- WDI source note: Gross domestic product is the total income earned through the production of goods and services in an economic territory during an accounting period. It can be measured in three different ways: using either the expenditure approach, the income approach, or the production approach. The core indicator has been divided by the general population to achieve a per capita estimate.This indicator is expressed in current prices, meaning no adjustment has been made to account for price changes over time. This indicator is expressed in United States dollars.
- WDI API last updated: not supplied
- Mean absolute relative difference: 4.58070428502279
- Median absolute relative difference: 1.0033473307587037
- 95th percentile absolute relative difference: 22.23389548493055
- Country-years with >5% relative difference: 445
- Mean absolute difference (percentage points, fields 20/21): None
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
- Mean absolute relative difference: 2.8555408952726196
- Median absolute relative difference: 0.18898207444304177
- 95th percentile absolute relative difference: 13.044639153342215
- Country-years with >5% relative difference: 315
- Mean absolute difference (percentage points, fields 20/21): None
- Vintage caveat: IMF October 2026 fixed CSV versus live rolling WDI API response; not vintage-aligned

## Field 20: PCPIPCH vs FP.CPI.TOTL.ZG

- Definition: annual CPI inflation; period-average convention requires review
- WDI originating organization: International Financial Statistics database, International Monetary Fund (IMF)
- WDI source note: Inflation as measured by the consumer price index reflects the annual percentage change in the cost to the average consumer of acquiring a basket of goods and services that may be fixed or changed at specified intervals, such as yearly.
- WDI API last updated: not supplied
- Mean absolute relative difference: 18.674269717095044
- Median absolute relative difference: 0.2728997555010045
- 95th percentile absolute relative difference: 64.13292500000038
- Country-years with >5% relative difference: 529
- Mean absolute difference (percentage points, fields 20/21): 0.42366428734192674
- Vintage caveat: IMF October 2026 fixed CSV versus live rolling WDI API response; not vintage-aligned

## Field 21: LUR vs SL.UEM.TOTL.ZS

- Definition: unemployment rate; methodology and IMF unit require review
- WDI originating organization: ILO Modelled Estimates database (ILOEST), International Labour Organization (ILO), uri: https://ilostat.ilo.org/data/bulk/, publisher: ILOSTAT, type: external database, date accessed: January 17, 2026
- WDI source note: Unemployment refers to the share of the labor force that is without work but available for and seeking employment.
- WDI API last updated: not supplied
- Mean absolute relative difference: 19.027275283818053
- Median absolute relative difference: 2.725964948067257
- 95th percentile absolute relative difference: 79.43698732289337
- Country-years with >5% relative difference: 463
- Mean absolute difference (percentage points, fields 20/21): 0.883020104895105
- Vintage caveat: IMF October 2026 fixed CSV versus live rolling WDI API response; not vintage-aligned

## Interpretation limits

- A shared country-year is a numerical comparison, not proof of semantic equivalence.
- IMF values in Billions are converted to absolute dollars; GDP per capita and percentage series are not rescaled.
- IMF actual/estimate classification is only a hint from LATEST_ACTUAL_ANNUAL_DATA; fiscal-year labels and PPPGDP are unclassified.
- WDI observation status is not inferred. WDI is retrieved live and may change between runs.
- Fields 18, 20 and 21 require explicit definition review before a policy decision; PPP benchmark, CPI period convention and unemployment methodology/unit remain material caveats.
- No source-selection, release, approval, or database action is performed.
