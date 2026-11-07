# WDI macro-series decomposition assessment

- Snapshot: api_snapshot_20261107T161129160851Z
- Retrieval time: 2026-11-07T16:12:07.812622+00:00
- Countries: 242; country-year rows: 2662
- Decision boundary: diagnostic only; no source policy or database change.

## Supporting indicators

| Code | Name | Unit | Source organization | API last updated |
|---|---|---|---|---|
| NY.GDP.MKTP.CN | GDP (current LCU) |  | Country official statistics, National Statistical Organizations and/or Central Banks;
National Accounts data files, Organisation for Economic Co-operation and Development (OECD);
Staff estimates, World Bank (WB) | None |
| PA.NUS.FCRF | Official exchange rate (LCU per US$, period average) |  | International Financial Statistics database, International Monetary Fund (IMF) | None |
| PA.NUS.ATLS | DEC alternative conversion factor (LCU per US$) |  | International Financial Statistics database, International Monetary Fund (IMF);
Staff estimates, World Bank (WB) | None |
| PA.NUS.PPP | PPP conversion factor, GDP (LCU per international $) |  | International Comparison Program (ICP), World Bank (WB), uri: https://www.worldbank.org/en/programs/icp/data, publisher: International Comparison Program, type: International statistical program, date accessed: May 30, 2024, date published: May 30, 2024;
The Eurostat PPP Programme, Eurostat (ESTAT), uri: https://ec.europa.eu/eurostat/databrowser/explore/all/all_themes, publisher: Eurostat, type: International statistical program;
The OECD PPP Programme, Organisation for Economic Co-operation and Development (OECD), uri: https://data-https://data-explorer.oecd.org/, publisher: OECD | None |
| SP.POP.TOTL | Population, total |  | World Population Prospects, United Nations (UN), uri: https://population.un.org/wpp/, publisher: UN Population Division;
Statistical databases and publications from national statistical offices, National Statistical Offices (NSOs), uri: https://unstats.un.org/home/nso_sites/, publisher: National Statistical Offices;
Eurostat: Demographic Statistics, Eurostat (ESTAT), uri: https://ec.europa.eu/eurostat/data/database?node_code=earn_ses_monthly, publisher: Eurostat;
Population and Vital Statistics Report (various years), United Nations (UN), uri: https://unstats.un.org, publisher: UN Statistics Division | None |
| FP.CPI.TOTL | Consumer price index (2010 = 100) |  | International Financial Statistics database, International Monetary Fund (IMF) | None |

## Interpretation limits

- WDI arithmetic relationships are diagnostics, not proof of the provider's internal construction pipeline.
- PA.NUS.ATLS is the DEC alternative conversion factor used in the Atlas method; its presence does not prove it converts NY.GDP.MKTP.CD.
- Official exchange rates, alternative conversion factors and PPP factors may use different reference periods and vintages from national accounts.
- Population division is an arithmetic check; the reference date and population universe may differ from the GDP-per-capita denominator.
- CPI-index year-on-year growth is a diagnostic only; the annual index convention and inflation-series source vintage require confirmation.
- All identity mappings remain subject to the separate country-identity governance gate.
- The WDI capture is a rolling API snapshot, not a provider-declared vintage aligned to the October 2026 IMF WEO export.
- Observation status is preserved verbatim and not interpreted as actual, estimate or projection.

## Side effects

- No new source responses fetched by this assessment.
- No SQLite database, source-selection policy, approval, release or Game DB state changed.
