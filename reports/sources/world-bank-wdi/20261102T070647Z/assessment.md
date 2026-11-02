# World Bank WDI coverage assessment

- Checked: 2026-11-02T07:06:47.849334+00:00
- Period: 2015–2025
- Indicators: 8
- Scope: read-only API assessment; no snapshots, policy changes, or database writes

| Field | Indicator | Name | Unit | Source organization | Countries with observations | Latest year range |
|---:|---|---|---|---|---:|---|
| 15 | NY.GDP.MKTP.CD | GDP (current US$) |  | Country official statistics, National Statistical Organizations and/or Central Banks;
National Accounts data files, Organisation for Economic Co-operation and Development (OECD);
Staff estimates, World Bank (WB) | 0 | none |
| 16 | NY.GDP.PCAP.CD | GDP per capita (current US$) |  | Country official statistics, National Statistical Organizations and/or Central Banks;
National Accounts data files, Organisation for Economic Co-operation and Development (OECD);
Staff estimates, World Bank (WB) | 0 | none |
| 18 | NY.GDP.MKTP.PP.CD | GDP, PPP (current international $) |  | International Comparison Program (ICP), World Bank (WB), uri: https://www.worldbank.org/en/programs/icp/data, note: This information is for ICP’s PPPs utilized in WDI, publisher: International Comparison Program (ICP), date accessed: May 30, 2024, date published: May 30, 2024;
The Eurostat PPP Programme, Eurostat (ESTAT), uri: https://ec.europa.eu/eurostat/databrowser/explore/all/all_themes, publisher: Eurostat, date accessed: Periodical update;
The OECD PPP Programme, Organisation for Economic Co-operation and Development (OECD), uri: https://data-https://data-explorer.oecd.org/, publisher: OECD, date accessed: Periodical update;
Staff estimates, World Bank (WB);
National Accounts data files, Organisation for Economic Co-operation and Development (OECD);
World Economic Outlook database, International Monetary Fund (IMF) | 0 | none |
| 20 | FP.CPI.TOTL.ZG | Inflation, consumer prices (annual %) |  | International Financial Statistics database, International Monetary Fund (IMF) | 0 | none |
| 21 | SL.UEM.TOTL.ZS | Unemployment, total (% of total labor force) (modeled ILO estimate) |  | ILO Modelled Estimates database (ILOEST), International Labour Organization (ILO), uri: https://ilostat.ilo.org/data/bulk/, publisher: ILOSTAT, type: external database, date accessed: January 17, 2026 | 0 | none |
| 3 | EN.POP.DNST | Population density (people per sq. km of land area) |  | FAO population estimates, Food and Agriculture Organization of the United Nations (FAO), publisher: Food and Agriculture Organization of the United Nations (FAO);
World Bank population estimates, World Bank (WB), publisher: World Bank (WB) | 0 | none |
| 33 | AG.SRF.TOTL.K2 | Surface area (sq. km) |  | FAO electronic files and web site, Food and Agriculture Organization of the United Nations (FAO), publisher: Food and Agriculture Organization of the United Nations (FAO) | 0 | none |
| 34 | AG.LND.TOTL.K2 | Land area (sq. km) |  | FAOSTAT, Food and Agriculture Organization of the United Nations (FAO), uri: https://www.fao.org/faostat/en/#data/RL, publisher: Food and Agriculture Organization of the United Nations (FAO) | 0 | none |

## Comparability boundary

IMF WEO comparability was not assessed because no immutable IMF WEO comparison snapshot or normalized IMF observations are configured. Do not infer equivalence from indicator labels.

## Identity boundary

Coverage is reported by provider ISO3 only. No game identity is inferred; a reviewed source crosswalk is required.

## Indicator metadata notes

### NY.GDP.MKTP.CD — GDP (current US$)

- Unit: not supplied
- Source organization: Country official statistics, National Statistical Organizations and/or Central Banks;
National Accounts data files, Organisation for Economic Co-operation and Development (OECD);
Staff estimates, World Bank (WB)
- Source note: Gross domestic product is the total income earned through the production of goods and services in an economic territory during an accounting period. It can be measured in three different ways: using either the expenditure approach, the income approach, or the production approach. This indicator is expressed in current prices, meaning no adjustment has been made to account for price changes over time. This indicator is expressed in United States dollars.
- Metadata endpoint: https://api.worldbank.org/v2/indicator/NY.GDP.MKTP.CD?format=json

### NY.GDP.PCAP.CD — GDP per capita (current US$)

- Unit: not supplied
- Source organization: Country official statistics, National Statistical Organizations and/or Central Banks;
National Accounts data files, Organisation for Economic Co-operation and Development (OECD);
Staff estimates, World Bank (WB)
- Source note: Gross domestic product is the total income earned through the production of goods and services in an economic territory during an accounting period. It can be measured in three different ways: using either the expenditure approach, the income approach, or the production approach. The core indicator has been divided by the general population to achieve a per capita estimate.This indicator is expressed in current prices, meaning no adjustment has been made to account for price changes over time. This indicator is expressed in United States dollars.
- Metadata endpoint: https://api.worldbank.org/v2/indicator/NY.GDP.PCAP.CD?format=json

### NY.GDP.MKTP.PP.CD — GDP, PPP (current international $)

- Unit: not supplied
- Source organization: International Comparison Program (ICP), World Bank (WB), uri: https://www.worldbank.org/en/programs/icp/data, note: This information is for ICP’s PPPs utilized in WDI, publisher: International Comparison Program (ICP), date accessed: May 30, 2024, date published: May 30, 2024;
The Eurostat PPP Programme, Eurostat (ESTAT), uri: https://ec.europa.eu/eurostat/databrowser/explore/all/all_themes, publisher: Eurostat, date accessed: Periodical update;
The OECD PPP Programme, Organisation for Economic Co-operation and Development (OECD), uri: https://data-https://data-explorer.oecd.org/, publisher: OECD, date accessed: Periodical update;
Staff estimates, World Bank (WB);
National Accounts data files, Organisation for Economic Co-operation and Development (OECD);
World Economic Outlook database, International Monetary Fund (IMF)
- Source note: This indicator provides values for gross domestic product (GDP) expressed in current international dollars, converted by purchasing power parities (PPPs). PPPs account for the different price levels across countries and thus PPP-based comparisons of economic output are more appropriate for comparing the output of economies and the average material well-being of their inhabitants than exchange-rate based comparisons.  

Gross domestic product is the total income earned through the production of goods and services in an economic territory during an accounting period. It can be measured in three different ways: using either the expenditure approach, the income approach, or the production approach. This series has been linked to produce a consistent time series to counteract breaks in series over time due to changes in base years, source data and methodologies. Thus, it may not be comparable with other national accounts series in the database for historical years. This indicator is expressed in current prices, meaning no adjustment has been made to account for price changes over time. The PPP conversion factor is a currency conversion factor and a spatial price deflator. PPPs convert different currencies to a common currency and, in the process of conversion, equalize their purchasing power by eliminating the differences in price levels between countries, thereby allowing volume or output comparisons of GDP and its expenditure components.
- Metadata endpoint: https://api.worldbank.org/v2/indicator/NY.GDP.MKTP.PP.CD?format=json

### FP.CPI.TOTL.ZG — Inflation, consumer prices (annual %)

- Unit: not supplied
- Source organization: International Financial Statistics database, International Monetary Fund (IMF)
- Source note: Inflation as measured by the consumer price index reflects the annual percentage change in the cost to the average consumer of acquiring a basket of goods and services that may be fixed or changed at specified intervals, such as yearly.
- Metadata endpoint: https://api.worldbank.org/v2/indicator/FP.CPI.TOTL.ZG?format=json

### SL.UEM.TOTL.ZS — Unemployment, total (% of total labor force) (modeled ILO estimate)

- Unit: not supplied
- Source organization: ILO Modelled Estimates database (ILOEST), International Labour Organization (ILO), uri: https://ilostat.ilo.org/data/bulk/, publisher: ILOSTAT, type: external database, date accessed: January 17, 2026
- Source note: Unemployment refers to the share of the labor force that is without work but available for and seeking employment.
- Metadata endpoint: https://api.worldbank.org/v2/indicator/SL.UEM.TOTL.ZS?format=json

### EN.POP.DNST — Population density (people per sq. km of land area)

- Unit: not supplied
- Source organization: FAO population estimates, Food and Agriculture Organization of the United Nations (FAO), publisher: Food and Agriculture Organization of the United Nations (FAO);
World Bank population estimates, World Bank (WB), publisher: World Bank (WB)
- Source note: Population density is midyear population divided by land area in square kilometers. Population is based on the de facto definition of population, which counts all residents regardless of legal status or citizenship--except for refugees not permanently settled in the country of asylum, who are generally considered part of the population of their country of origin. Land area is a country's total area, excluding area under inland water bodies, national claims to continental shelf, and exclusive economic zones. In most cases the definition of inland water bodies includes major rivers and lakes.
- Metadata endpoint: https://api.worldbank.org/v2/indicator/EN.POP.DNST?format=json

### AG.SRF.TOTL.K2 — Surface area (sq. km)

- Unit: not supplied
- Source organization: FAO electronic files and web site, Food and Agriculture Organization of the United Nations (FAO), publisher: Food and Agriculture Organization of the United Nations (FAO)
- Source note: Surface area is a country's total area, including areas under inland bodies of water and some coastal waterways.
- Metadata endpoint: https://api.worldbank.org/v2/indicator/AG.SRF.TOTL.K2?format=json

### AG.LND.TOTL.K2 — Land area (sq. km)

- Unit: not supplied
- Source organization: FAOSTAT, Food and Agriculture Organization of the United Nations (FAO), uri: https://www.fao.org/faostat/en/#data/RL, publisher: Food and Agriculture Organization of the United Nations (FAO)
- Source note: Land area is a country's total area, excluding area under inland water bodies, national claims to continental shelf, and exclusive economic zones. In most cases the definition of inland water bodies includes major rivers and lakes.
- Metadata endpoint: https://api.worldbank.org/v2/indicator/AG.LND.TOTL.K2?format=json

