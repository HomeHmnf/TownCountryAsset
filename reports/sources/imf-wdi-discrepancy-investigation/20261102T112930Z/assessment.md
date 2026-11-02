# Targeted IMF WEO/WDI country discrepancy investigation

- Checked: 2026-11-02T11:29:30.688467+00:00
- Input comparison rows: 9324
- Selected country-field groups: 15
- Selected country-year observations: 165
- Read-only analysis of the existing comparison CSV; no new source retrieval

| Field | Country | Years | Median absolute relative difference | Direction |
|---:|---|---:|---:|---|
| 15 | Central African Republic | 11 | 51.670% | IMF consistently higher |
| 15 | Guinea | 11 | 52.534% | IMF consistently higher |
| 15 | Turkmenistan | 11 | 55.200% | IMF consistently higher |
| 16 | Central African Republic | 11 | 53.023% | IMF consistently higher |
| 16 | Guinea | 11 | 45.902% | IMF consistently higher |
| 16 | Turkmenistan | 11 | 71.800% | IMF consistently higher |
| 18 | Central African Republic | 11 | 53.792% | IMF consistently higher |
| 18 | Guinea | 11 | 57.176% | IMF consistently higher |
| 18 | Zimbabwe | 11 | 26.415% | mixed direction |
| 20 | Palau, Republic of | 11 | 64.133% | mixed direction |
| 20 | Samoa | 11 | 65.067% | mixed direction |
| 20 | Tonga | 11 | 97.666% | mixed direction |
| 21 | Bahrain, Kingdom of | 11 | 281.137% | IMF consistently higher |
| 21 | Moldova, Republic of | 11 | 182.145% | IMF consistently higher |
| 21 | Philippines | 11 | 107.852% | IMF consistently higher |

## Country-level observations

### Field 15: Central African Republic

- Indicators: IMF NGDPD; WDI NY.GDP.MKTP.CD
- Median signed relative difference: 51.669724934259186
- Median absolute relative difference: 51.669724934259186
- Maximum absolute relative difference: 55.44050181210305
- Direction: IMF consistently higher
- IMF status hints: {'actual_per_weo_metadata': 8, 'after_latest_actual': 3}
- IMF reporting periods: {'January/December': 11}

| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |
|---:|---:|---:|---:|---:|---:|---|---|
| 2015 | 2636000000.0 | 1695825714.19282 | 940174285.8071799 | 940174285.8071799 | 55.44050181210305 | actual_per_weo_metadata | January/December |
| 2016 | 2768000000.0 | 1825018144.65595 | 942981855.3440499 | 942981855.3440499 | 51.669724934259186 | actual_per_weo_metadata | January/December |
| 2017 | 3012000000.0 | 2072349972.6818 | 939650027.3182001 | 939650027.3182001 | 45.34224622794826 | actual_per_weo_metadata | January/December |
| 2018 | 3227000000.0 | 2220979146.11241 | 1006020853.8875899 | 1006020853.8875899 | 45.296276448544035 | actual_per_weo_metadata | January/December |
| 2019 | 3333000000.0 | 2221301351.43918 | 1111698648.56082 | 1111698648.56082 | 50.04717832817016 | actual_per_weo_metadata | January/December |
| 2020 | 3577000000.0 | 2326720900.38047 | 1250279099.6195302 | 1250279099.6195302 | 53.73567149438002 | actual_per_weo_metadata | January/December |
| 2021 | 3879000000.0 | 2516498412.46384 | 1362501587.53616 | 1362501587.53616 | 54.14275569529047 | actual_per_weo_metadata | January/December |
| 2022 | 3670000000.0 | 2382618615.01694 | 1287381384.98306 | 1287381384.98306 | 54.0322054427459 | actual_per_weo_metadata | January/December |
| 2023 | 3886000000.0 | 2555492085.94725 | 1330507914.05275 | 1330507914.05275 | 52.064646232687025 | after_latest_actual | January/December |
| 2024 | 4126000000.0000005 | 2751494281.06887 | 1374505718.9311304 | 1374505718.9311304 | 49.954881912281415 | after_latest_actual | January/December |
| 2025 | 4636000000.0 | 3066109226.40165 | 1569890773.59835 | 1569890773.59835 | 51.20139752623084 | after_latest_actual | January/December |

### Field 15: Guinea

- Indicators: IMF NGDPD; WDI NY.GDP.MKTP.CD
- Median signed relative difference: 52.534488326179584
- Median absolute relative difference: 52.534488326179584
- Maximum absolute relative difference: 66.50940412232971
- Direction: IMF consistently higher
- IMF status hints: {'actual_per_weo_metadata': 10, 'after_latest_actual': 1}
- IMF reporting periods: {'January/December': 11}

| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |
|---:|---:|---:|---:|---:|---:|---|---|
| 2015 | 13380000000.0 | 8794201742.84609 | 4585798257.15391 | 4585798257.15391 | 52.14570226211113 | actual_per_weo_metadata | January/December |
| 2016 | 13411000000.0 | 8595955222.49719 | 4815044777.50281 | 4815044777.50281 | 56.01523801451356 | actual_per_weo_metadata | January/December |
| 2017 | 16520000000.0 | 10324668271.1362 | 6195331728.8638 | 6195331728.8638 | 60.005140757728405 | actual_per_weo_metadata | January/December |
| 2018 | 17927000000.0 | 11857030366.7891 | 6069969633.210899 | 6069969633.210899 | 51.19300065396269 | actual_per_weo_metadata | January/December |
| 2019 | 20505000000.0 | 13442861496.4454 | 7062138503.5546 | 7062138503.5546 | 52.534488326179584 | actual_per_weo_metadata | January/December |
| 2020 | 23459000000.0 | 14088693742.9464 | 9370306257.0536 | 9370306257.0536 | 66.50940412232971 | actual_per_weo_metadata | January/December |
| 2021 | 25137000000.0 | 17069115737.8259 | 8067884262.174101 | 8067884262.174101 | 47.26597666858231 | actual_per_weo_metadata | January/December |
| 2022 | 30060000000.0 | 19910452541.9219 | 10149547458.078098 | 10149547458.078098 | 50.975975742932015 | actual_per_weo_metadata | January/December |
| 2023 | 35333000000.0 | 22407615556.0571 | 12925384443.942902 | 12925384443.942902 | 57.68299804862096 | actual_per_weo_metadata | January/December |
| 2024 | 38348000000.0 | 25008678293.4073 | 13339321706.592701 | 13339321706.592701 | 53.338771246096464 | actual_per_weo_metadata | January/December |
| 2025 | 42272000000.0 | 28346024753.2924 | 13925975246.7076 | 13925975246.7076 | 49.12849462283099 | after_latest_actual | January/December |

### Field 15: Turkmenistan

- Indicators: IMF NGDPD; WDI NY.GDP.MKTP.CD
- Median signed relative difference: 55.19967715496985
- Median absolute relative difference: 55.19967715496985
- Maximum absolute relative difference: 87.88128609343393
- Direction: IMF consistently higher
- IMF status hints: {'actual_per_weo_metadata': 11}
- IMF reporting periods: {'January/December': 11}

| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |
|---:|---:|---:|---:|---:|---:|---|---|
| 2015 | 35800000000.0 | 35799714285.7143 | 285714.285697937 | 285714.285697937 | 0.0007980909663626838 | actual_per_weo_metadata | January/December |
| 2016 | 36180000000.0 | 33313947368.4211 | 2866052631.5788994 | 2866052631.5788994 | 8.603161312236697 | actual_per_weo_metadata | January/December |
| 2017 | 37926000000.0 | 33352261306.5327 | 4573738693.4673 | 4573738693.4673 | 13.713429057871537 | actual_per_weo_metadata | January/December |
| 2018 | 40762000000.0 | 26036313868.6131 | 14725686131.386902 | 14725686131.386902 | 56.558260150407804 | actual_per_weo_metadata | January/December |
| 2019 | 44974000000.0 | 29700000000.0 | 15274000000.0 | 15274000000.0 | 51.42760942760943 | actual_per_weo_metadata | January/December |
| 2020 | 45455000000.0 | 27350527267.6636 | 18104472732.3364 | 18104472732.3364 | 66.19423660523441 | actual_per_weo_metadata | January/December |
| 2021 | 49477000000.0 | 26334182093.7903 | 23142817906.2097 | 23142817906.2097 | 87.88128609343393 | actual_per_weo_metadata | January/December |
| 2022 | 56677000000.0 | 37583913148.2791 | 19093086851.7209 | 19093086851.7209 | 50.80122119374134 | actual_per_weo_metadata | January/December |
| 2023 | 62814000000.0 | 39020211239.6728 | 23793788760.3272 | 23793788760.3272 | 60.97811366058284 | actual_per_weo_metadata | January/December |
| 2024 | 68675000000.0 | 44249447717.2312 | 24425552282.7688 | 24425552282.7688 | 55.19967715496985 | actual_per_weo_metadata | January/December |
| 2025 | 77398000000.0 | 49828621355.6516 | 27569378644.348396 | 27569378644.348396 | 55.32839941039519 | actual_per_weo_metadata | January/December |

### Field 16: Central African Republic

- Indicators: IMF NGDPDPC; WDI NY.GDP.PCAP.CD
- Median signed relative difference: 53.02320860802482
- Median absolute relative difference: 53.02320860802482
- Maximum absolute relative difference: 56.78628669370922
- Direction: IMF consistently higher
- IMF status hints: {'actual_per_weo_metadata': 8, 'after_latest_actual': 3}
- IMF reporting periods: {'January/December': 11}

| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |
|---:|---:|---:|---:|---:|---:|---|---|
| 2015 | 574.344 | 366.322853938121 | 208.02114606187905 | 208.02114606187905 | 56.78628669370922 | actual_per_weo_metadata | January/December |
| 2016 | 592.98 | 387.176203444318 | 205.80379655568203 | 205.80379655568203 | 53.155073768700724 | actual_per_weo_metadata | January/December |
| 2017 | 632.901 | 432.324025684263 | 200.57697431573695 | 200.57697431573695 | 46.395056115207275 | actual_per_weo_metadata | January/December |
| 2018 | 668.431 | 455.243962859534 | 213.18703714046603 | 213.18703714046603 | 46.82918490590618 | actual_per_weo_metadata | January/December |
| 2019 | 676.279 | 449.228467602439 | 227.05053239756097 | 227.05053239756097 | 50.54232952095492 | actual_per_weo_metadata | January/December |
| 2020 | 721.139 | 462.879071294011 | 258.259928705989 | 258.259928705989 | 55.7942548545142 | actual_per_weo_metadata | January/December |
| 2021 | 761.58 | 492.263142830507 | 269.31685716949306 | 269.31685716949306 | 54.709937376364294 | actual_per_weo_metadata | January/December |
| 2022 | 715.169 | 467.359825026238 | 247.80917497376197 | 247.80917497376197 | 53.02320860802482 | actual_per_weo_metadata | January/December |
| 2023 | 767.35 | 495.978897288721 | 271.37110271127904 | 271.37110271127904 | 54.714243729871335 | after_latest_actual | January/December |
| 2024 | 774.064 | 516.160999996036 | 257.90300000396394 | 257.90300000396394 | 49.965611506089104 | after_latest_actual | January/December |
| 2025 | 840.902 | 556.131398031455 | 284.77060196854507 | 284.77060196854507 | 51.205632873193466 | after_latest_actual | January/December |

### Field 16: Guinea

- Indicators: IMF NGDPDPC; WDI NY.GDP.PCAP.CD
- Median signed relative difference: 45.90201706678437
- Median absolute relative difference: 45.90201706678437
- Maximum absolute relative difference: 59.40269562219404
- Direction: IMF consistently higher
- IMF status hints: {'actual_per_weo_metadata': 10, 'after_latest_actual': 1}
- IMF reporting periods: {'January/December': 11}

| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |
|---:|---:|---:|---:|---:|---:|---|---|
| 2015 | 1083.833 | 747.356966759448 | 336.47603324055206 | 336.47603324055206 | 45.02213108409461 | actual_per_weo_metadata | January/December |
| 2016 | 1059.881 | 711.996509782316 | 347.88449021768406 | 347.88449021768406 | 48.86042072369784 | actual_per_weo_metadata | January/December |
| 2017 | 1273.683 | 833.598621691121 | 440.08437830887897 | 440.08437830887897 | 52.793318853632464 | actual_per_weo_metadata | January/December |
| 2018 | 1348.441 | 933.273615633705 | 415.167384366295 | 415.167384366295 | 44.4850660526164 | actual_per_weo_metadata | January/December |
| 2019 | 1504.748 | 1031.34146480732 | 473.40653519267994 | 473.40653519267994 | 45.90201706678437 | actual_per_weo_metadata | January/December |
| 2020 | 1679.564 | 1053.66097696415 | 625.9030230358501 | 625.9030230358501 | 59.40269562219404 | actual_per_weo_metadata | January/December |
| 2021 | 1755.783 | 1244.96550477914 | 510.8174952208599 | 510.8174952208599 | 41.030654524960525 | actual_per_weo_metadata | January/December |
| 2022 | 2048.481 | 1416.59612011764 | 631.8848798823601 | 631.8848798823601 | 44.605859843092446 | actual_per_weo_metadata | January/December |
| 2023 | 2349.043 | 1555.49375806861 | 793.54924193139 | 793.54924193139 | 51.01590654511568 | actual_per_weo_metadata | January/December |
| 2024 | 2487.359 | 1694.95375862185 | 792.4052413781499 | 792.4052413781499 | 46.7508471748779 | actual_per_weo_metadata | January/December |
| 2025 | 2675.004 | 1877.2541220972 | 797.7498779027999 | 797.7498779027999 | 42.49557204389477 | after_latest_actual | January/December |

### Field 16: Turkmenistan

- Indicators: IMF NGDPDPC; WDI NY.GDP.PCAP.CD
- Median signed relative difference: 71.799943395054
- Median absolute relative difference: 71.799943395054
- Maximum absolute relative difference: 110.106663314279
- Direction: IMF consistently higher
- IMF status hints: {'actual_per_weo_metadata': 11}
- IMF reporting periods: {'January/December': 11}

| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |
|---:|---:|---:|---:|---:|---:|---|---|
| 2015 | 6208.282 | 5759.497903834 | 448.7840961660004 | 448.7840961660004 | 7.792069789056654 | actual_per_weo_metadata | January/December |
| 2016 | 6165.055 | 5238.00827202546 | 927.0467279745399 | 927.0467279745399 | 17.698458647451975 | actual_per_weo_metadata | January/December |
| 2017 | 6354.528 | 5125.54920055808 | 1228.9787994419203 | 1228.9787994419203 | 23.977504680046906 | actual_per_weo_metadata | January/December |
| 2018 | 6720.789 | 3911.98557297865 | 2808.8034270213498 | 2808.8034270213498 | 71.799943395054 | actual_per_weo_metadata | January/December |
| 2019 | 7302.894 | 4365.1152919542 | 2937.7787080458 | 2937.7787080458 | 67.30128556880793 | actual_per_weo_metadata | January/December |
| 2020 | 7272.268 | 3935.37749365223 | 3336.89050634777 | 3336.89050634777 | 84.79213269197629 | actual_per_weo_metadata | January/December |
| 2021 | 7801.683 | 3713.20113171765 | 4088.48186828235 | 4088.48186828235 | 110.106663314279 | actual_per_weo_metadata | January/December |
| 2022 | 8813.475 | 5198.18947409551 | 3615.28552590449 | 3615.28552590449 | 69.54893706589164 | actual_per_weo_metadata | January/December |
| 2023 | 9639.771 | 5298.46421949276 | 4341.306780507241 | 4341.306780507241 | 81.93519104150614 | actual_per_weo_metadata | January/December |
| 2024 | 10408.348 | 5904.25772576512 | 4504.09027423488 | 4504.09027423488 | 76.28546183849392 | actual_per_weo_metadata | January/December |
| 2025 | 11586.537 | 6540.17876401136 | 5046.35823598864 | 5046.35823598864 | 77.15933184819403 | actual_per_weo_metadata | January/December |

### Field 18: Central African Republic

- Indicators: IMF PPPGDP; WDI NY.GDP.MKTP.PP.CD
- Median signed relative difference: 53.792151788724276
- Median absolute relative difference: 53.792151788724276
- Maximum absolute relative difference: 60.78639619190537
- Direction: IMF consistently higher
- IMF status hints: {'status_unclassified': 11}
- IMF reporting periods: {'unknown': 11}

| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |
|---:|---:|---:|---:|---:|---:|---|---|
| 2015 | 5474000000.0 | 3559349379.23233 | 1914650620.7676702 | 1914650620.7676702 | 53.792151788724276 | status_unclassified | unknown |
| 2016 | 5789000000.0 | 3893548336.23769 | 1895451663.76231 | 1895451663.76231 | 48.68185778306973 | status_unclassified | unknown |
| 2017 | 6159000000.0 | 4236556479.54651 | 1922443520.4534898 | 1922443520.4534898 | 45.37750245357928 | status_unclassified | unknown |
| 2018 | 6419000000.0 | 4419174296.74199 | 1999825703.25801 | 1999825703.25801 | 45.253379228159645 | status_unclassified | unknown |
| 2019 | 7307000000.0 | 4869757044.86639 | 2437242955.13361 | 2437242955.13361 | 50.04855340171246 | status_unclassified | unknown |
| 2020 | 8228999999.999999 | 5359843442.72162 | 2869156557.2783794 | 2869156557.2783794 | 53.530603793559315 | status_unclassified | unknown |
| 2021 | 8887000000.0 | 5769272621.61696 | 3117727378.3830404 | 3117727378.3830404 | 54.04021586189547 | status_unclassified | unknown |
| 2022 | 9703000000.0 | 6207661682.42162 | 3495338317.5783796 | 3495338317.5783796 | 56.30684300138667 | status_unclassified | unknown |
| 2023 | 10062000000.0 | 6482417925.94617 | 3579582074.05383 | 3579582074.05383 | 55.219859548493346 | status_unclassified | unknown |
| 2024 | 10725000000.0 | 6742985507.57026 | 3982014492.42974 | 3982014492.42974 | 59.05417545327934 | status_unclassified | unknown |
| 2025 | 11647000000.0 | 7243772032.86453 | 4403227967.13547 | 4403227967.13547 | 60.78639619190537 | status_unclassified | unknown |

### Field 18: Guinea

- Indicators: IMF PPPGDP; WDI NY.GDP.MKTP.PP.CD
- Median signed relative difference: 57.176263996400955
- Median absolute relative difference: 57.176263996400955
- Maximum absolute relative difference: 85.74261279564193
- Direction: IMF consistently higher
- IMF status hints: {'status_unclassified': 11}
- IMF reporting periods: {'unknown': 11}

| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |
|---:|---:|---:|---:|---:|---:|---|---|
| 2015 | 42176000000.0 | 22706690384.7223 | 19469309615.2777 | 19469309615.2777 | 85.74261279564193 | status_unclassified | unknown |
| 2016 | 46637000000.0 | 27228620630.0338 | 19408379369.9662 | 19408379369.9662 | 71.27933373370486 | status_unclassified | unknown |
| 2017 | 53251000000.0 | 33281442968.4819 | 19969557031.5181 | 19969557031.5181 | 60.002076984551465 | status_unclassified | unknown |
| 2018 | 54637000000.0 | 36138275786.6167 | 18498724213.3833 | 18498724213.3833 | 51.18872943084364 | status_unclassified | unknown |
| 2019 | 61748000000.0 | 40482435336.7228 | 21265564663.2772 | 21265564663.2772 | 52.53034924009767 | status_unclassified | unknown |
| 2020 | 74182000000.0 | 44550864730.0015 | 29631135269.998497 | 29631135269.998497 | 66.51079715192208 | status_unclassified | unknown |
| 2021 | 78952000000.0 | 51260936277.8168 | 27691063722.183197 | 27691063722.183197 | 54.01981651702003 | status_unclassified | unknown |
| 2022 | 88423000000.0 | 57087996759.7038 | 31335003240.296204 | 31335003240.296204 | 54.88895217709647 | status_unclassified | unknown |
| 2023 | 97789000000.0 | 62481097795.4779 | 35307902204.5221 | 35307902204.5221 | 56.509734064047656 | status_unclassified | unknown |
| 2024 | 106781000000.0 | 67457857041.0153 | 39323142958.9847 | 39323142958.9847 | 58.29290268600691 | status_unclassified | unknown |
| 2025 | 117115000000.0 | 74511886860.1443 | 42603113139.8557 | 42603113139.8557 | 57.176263996400955 | status_unclassified | unknown |

### Field 18: Zimbabwe

- Indicators: IMF PPPGDP; WDI NY.GDP.MKTP.PP.CD
- Median signed relative difference: 24.961367175918507
- Median absolute relative difference: 26.414762541604087
- Maximum absolute relative difference: 60.221466491462486
- Direction: mixed direction
- IMF status hints: {'status_unclassified': 11}
- IMF reporting periods: {'unknown': 11}

| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |
|---:|---:|---:|---:|---:|---:|---|---|
| 2015 | 55505000000.0 | 58256947220.4219 | -2751947220.421898 | 2751947220.421898 | -4.723809522681624 | status_unclassified | unknown |
| 2016 | 56700000000.0 | 62422817499.5463 | -5722817499.546303 | 5722817499.546303 | -9.16782953539048 | status_unclassified | unknown |
| 2017 | 63379000000.0 | 159329654489.141 | -95950654489.14099 | 95950654489.14099 | -60.221466491462486 | status_unclassified | unknown |
| 2018 | 62043000000.0 | 60030923851.1648 | 2012076148.8351974 | 2012076148.8351974 | 3.351732773301566 | status_unclassified | unknown |
| 2019 | 75853000000.0 | 63619334445.2571 | 12233665554.742897 | 12233665554.742897 | 19.22947742446075 | status_unclassified | unknown |
| 2020 | 81074000000.0 | 64879251749.7551 | 16194748250.244904 | 16194748250.244904 | 24.961367175918507 | status_unclassified | unknown |
| 2021 | 96802000000.0 | 76254864070.4384 | 20547135929.5616 | 20547135929.5616 | 26.945344641335573 | status_unclassified | unknown |
| 2022 | 109614000000.0 | 86692951272.7606 | 22921048727.239395 | 22921048727.239395 | 26.43934528785769 | status_unclassified | unknown |
| 2023 | 119729000000.0 | 94711248585.8574 | 25017751414.142593 | 25017751414.142593 | 26.414762541604087 | status_unclassified | unknown |
| 2024 | 124935000000.0 | 98689576199.0155 | 26245423800.984497 | 26245423800.984497 | 26.59391681656275 | status_unclassified | unknown |
| 2025 | 138849000000.0 | 109678697422.277 | 29170302577.723007 | 29170302577.723007 | 26.59614242628504 | status_unclassified | unknown |

### Field 20: Palau, Republic of

- Indicators: IMF PCPIPCH; WDI FP.CPI.TOTL.ZG
- Median signed relative difference: 16.319600000002264
- Median absolute relative difference: 64.13292500000038
- Maximum absolute relative difference: 233.6666666666455
- Direction: mixed direction
- IMF status hints: {'actual_per_weo_metadata': 11}
- IMF reporting periods: {'unknown': 11}

| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |
|---:|---:|---:|---:|---:|---:|---|---|
| 2015 | 2.199 | 0.949040643697081 | 1.2499593563029188 | 1.2499593563029188 | 131.70767391305597 | actual_per_weo_metadata | unknown |
| 2016 | -1.329 | -1.04230533415074 | -0.28669466584925996 | 0.28669466584925996 | 27.50582352942249 | actual_per_weo_metadata | unknown |
| 2017 | 1.09 | 1.41798819666919 | -0.32798819666919 | 0.32798819666919 | -23.13053080692942 | actual_per_weo_metadata | unknown |
| 2018 | 2.454 | 2.10970464135017 | 0.3442953586498301 | 0.3442953586498301 | 16.319600000002264 | actual_per_weo_metadata | unknown |
| 2019 | 0.466 | 0.267379679144439 | 0.19862032085556103 | 0.19862032085556103 | 74.28399999996483 | actual_per_weo_metadata | unknown |
| 2020 | 0.728 | 0.218181818181832 | 0.509818181818168 | 0.509818181818168 | 233.6666666666455 | actual_per_weo_metadata | unknown |
| 2021 | -0.526 | 2.6124818577648 | -3.1384818577648 | 3.1384818577648 | -120.13411111111172 | actual_per_weo_metadata | unknown |
| 2022 | 13.153 | 12.3526638378124 | 0.8003361621876 | 0.8003361621876 | 6.479057251907988 | actual_per_weo_metadata | unknown |
| 2023 | 12.412 | 12.8199748216533 | -0.40797482165329946 | 0.40797482165329946 | -3.182337152208899 | actual_per_weo_metadata | unknown |
| 2024 | 3.663 | 2.23172772921703 | 1.4312722707829697 | 1.4312722707829697 | 64.13292500000038 | actual_per_weo_metadata | unknown |
| 2025 | 0.226 | -0.418410041841039 | 0.644410041841039 | 0.644410041841039 | -154.0139999999955 | actual_per_weo_metadata | unknown |

### Field 20: Samoa

- Indicators: IMF PCPIPCH; WDI FP.CPI.TOTL.ZG
- Median signed relative difference: -16.81593370992702
- Median absolute relative difference: 65.06668705723652
- Maximum absolute relative difference: 196.06777270260517
- Direction: mixed direction
- IMF status hints: {'status_unclassified': 11}
- IMF reporting periods: {'unknown': 11}

| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |
|---:|---:|---:|---:|---:|---:|---|---|
| 2015 | 1.923 | 0.724470134874728 | 1.198529865125272 | 1.198529865125272 | 165.43537234043694 | status_unclassified | unknown |
| 2016 | 0.073 | 1.30471869303179 | -1.23171869303179 | 1.23171869303179 | -94.40492418864875 | status_unclassified | unknown |
| 2017 | 1.346 | 1.74989677484705 | -0.4038967748470499 | 0.4038967748470499 | -23.081177167284768 | status_unclassified | unknown |
| 2018 | 3.683 | 4.19745888663751 | -0.5144588866375104 | 0.5144588866375104 | -12.256436585365385 | status_unclassified | unknown |
| 2019 | 2.189 | 0.982326569888117 | 1.206673430111883 | 1.206673430111883 | 122.838317429337 | status_unclassified | unknown |
| 2020 | 1.48 | -1.56891247740895 | 3.04891247740895 | 3.04891247740895 | -194.33285930928486 | status_unclassified | unknown |
| 2021 | -3.01 | 3.13320473174494 | -6.143204731744939 | 6.143204731744939 | -196.06777270260517 | status_unclassified | unknown |
| 2022 | 8.747 | 10.9618822286843 | -2.2148822286842993 | 2.2148822286842993 | -20.20530947585395 | status_unclassified | unknown |
| 2023 | 11.981 | 7.92164684826777 | 4.05935315173223 | 4.05935315173223 | 51.243803586370305 | status_unclassified | unknown |
| 2024 | 3.586 | 2.17245530514377 | 1.4135446948562298 | 1.4135446948562298 | 65.06668705723652 | status_unclassified | unknown |
| 2025 | 1.84 | 2.2119620764675 | -0.3719620764675 | 0.3719620764675 | -16.81593370992702 | status_unclassified | unknown |

### Field 20: Tonga

- Indicators: IMF PCPIPCH; WDI FP.CPI.TOTL.ZG
- Median signed relative difference: -40.29913482335995
- Median absolute relative difference: 97.66561840628623
- Maximum absolute relative difference: 251.49195714287114
- Direction: mixed direction
- IMF status hints: {'status_unclassified': 11}
- IMF reporting periods: {'unknown': 11}

| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |
|---:|---:|---:|---:|---:|---:|---|---|
| 2015 | 0.054 | -1.05399831971282 | 1.10799831971282 | 1.10799831971282 | -105.12334782608698 | status_unclassified | unknown |
| 2016 | -0.621 | 2.57815515245081 | -3.19915515245081 | 3.19915515245081 | -124.0869910179639 | status_unclassified | unknown |
| 2017 | 7.201 | 7.51706283551115 | -0.31606283551115055 | 0.31606283551115055 | -4.204605474601686 | status_unclassified | unknown |
| 2018 | 6.093 | 5.03209691984882 | 1.0609030801511796 | 1.0609030801511796 | 21.082723505712057 | status_unclassified | unknown |
| 2019 | 4.146 | 1.179543348218 | 2.966456651782 | 2.966456651782 | 251.49195714287114 | status_unclassified | unknown |
| 2020 | 0.24 | -0.349737696727418 | 0.5897376967274179 | 0.5897376967274179 | -168.62285714286426 | status_unclassified | unknown |
| 2021 | 0.588 | 5.64051140636743 | -5.05251140636743 | 5.05251140636743 | -89.57541333333319 | status_unclassified | unknown |
| 2022 | 6.55 | 10.9713652903022 | -4.421365290302201 | 4.421365290302201 | -40.29913482335995 | status_unclassified | unknown |
| 2023 | 12.554 | 6.35112980255182 | 6.20287019744818 | 6.20287019744818 | 97.66561840628623 | status_unclassified | unknown |
| 2024 | 8.001 | 3.18188924237471 | 4.819110757625289 | 4.819110757625289 | 151.4543841893342 | status_unclassified | unknown |
| 2025 | 3.1 | 5.59276642101026 | -2.4927664210102596 | 2.4927664210102596 | -44.57125925455643 | status_unclassified | unknown |

### Field 21: Bahrain, Kingdom of

- Indicators: IMF LUR; WDI SL.UEM.TOTL.ZS
- Median signed relative difference: 281.1369509043928
- Median absolute relative difference: 281.1369509043928
- Maximum absolute relative difference: 500.5719733079123
- Direction: IMF consistently higher
- IMF status hints: {'actual_per_weo_metadata': 11}
- IMF reporting periods: {'unknown': 11}

| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |
|---:|---:|---:|---:|---:|---:|---|---|
| 2015 | 3.5 | 1.164 | 2.3360000000000003 | 2.3360000000000003 | 200.68728522336775 | actual_per_weo_metadata | unknown |
| 2016 | 3.9 | 1.19 | 2.71 | 2.71 | 227.7310924369748 | actual_per_weo_metadata | unknown |
| 2017 | 4.1 | 1.18 | 2.92 | 2.92 | 247.45762711864407 | actual_per_weo_metadata | unknown |
| 2018 | 4.3 | 1.188 | 3.112 | 3.112 | 261.952861952862 | actual_per_weo_metadata | unknown |
| 2019 | 4.7 | 1.217 | 3.483 | 3.483 | 286.19556285949056 | actual_per_weo_metadata | unknown |
| 2020 | 5.9 | 1.765 | 4.135000000000001 | 4.135000000000001 | 234.2776203966006 | actual_per_weo_metadata | unknown |
| 2021 | 5.9 | 1.548 | 4.352 | 4.352 | 281.1369509043928 | actual_per_weo_metadata | unknown |
| 2022 | 5.4 | 1.265 | 4.135000000000001 | 4.135000000000001 | 326.8774703557313 | actual_per_weo_metadata | unknown |
| 2023 | 6.3 | 1.049 | 5.2509999999999994 | 5.2509999999999994 | 500.5719733079123 | actual_per_weo_metadata | unknown |
| 2024 | 6.2 | 1.084 | 5.116 | 5.116 | 471.9557195571955 | actual_per_weo_metadata | unknown |
| 2025 | 5.6 | 1.102 | 4.497999999999999 | 4.497999999999999 | 408.1669691470053 | actual_per_weo_metadata | unknown |

### Field 21: Moldova, Republic of

- Indicators: IMF LUR; WDI SL.UEM.TOTL.ZS
- Median signed relative difference: 182.14486243683328
- Median absolute relative difference: 182.14486243683328
- Maximum absolute relative difference: 309.44584382871534
- Direction: IMF consistently higher
- IMF status hints: {'actual_per_weo_metadata': 11}
- IMF reporting periods: {'unknown': 11}

| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |
|---:|---:|---:|---:|---:|---:|---|---|
| 2015 | 5.025 | 1.781 | 3.2440000000000007 | 3.2440000000000007 | 182.14486243683328 | actual_per_weo_metadata | unknown |
| 2016 | 4.225 | 1.591 | 2.6339999999999995 | 2.6339999999999995 | 165.5562539283469 | actual_per_weo_metadata | unknown |
| 2017 | 4.125 | 1.622 | 2.503 | 2.503 | 154.31565967940816 | actual_per_weo_metadata | unknown |
| 2018 | 3.05 | 1.239 | 1.8109999999999997 | 1.8109999999999997 | 146.16626311541563 | actual_per_weo_metadata | unknown |
| 2019 | 5.119 | 1.502 | 3.617 | 3.617 | 240.81225033288948 | actual_per_weo_metadata | unknown |
| 2020 | 3.825 | 1.206 | 2.619 | 2.619 | 217.16417910447765 | actual_per_weo_metadata | unknown |
| 2021 | 3.251 | 0.794 | 2.457 | 2.457 | 309.44584382871534 | actual_per_weo_metadata | unknown |
| 2022 | 3.109 | 0.909 | 2.2 | 2.2 | 242.02420242024206 | actual_per_weo_metadata | unknown |
| 2023 | 4.593 | 1.57 | 3.0229999999999997 | 3.0229999999999997 | 192.5477707006369 | actual_per_weo_metadata | unknown |
| 2024 | 3.955 | 1.427 | 2.528 | 2.528 | 177.15487035739312 | actual_per_weo_metadata | unknown |
| 2025 | 3.802 | 1.505 | 2.297 | 2.297 | 152.624584717608 | actual_per_weo_metadata | unknown |

### Field 21: Philippines

- Indicators: IMF LUR; WDI SL.UEM.TOTL.ZS
- Median signed relative difference: 107.85219399538109
- Median absolute relative difference: 107.85219399538109
- Maximum absolute relative difference: 312.3711340206186
- Direction: IMF consistently higher
- IMF status hints: {'actual_per_weo_metadata': 11}
- IMF reporting periods: {'unknown': 11}

| Year | IMF | WDI | Signed difference | Absolute difference | Signed relative % | IMF status | Reporting period |
|---:|---:|---:|---:|---:|---:|---|---|
| 2015 | 6.275 | 3.068 | 3.2070000000000003 | 3.2070000000000003 | 104.53063885267275 | actual_per_weo_metadata | unknown |
| 2016 | 5.475 | 2.695 | 2.78 | 2.78 | 103.15398886827458 | actual_per_weo_metadata | unknown |
| 2017 | 5.725 | 2.552 | 3.1729999999999996 | 3.1729999999999996 | 124.33385579937301 | actual_per_weo_metadata | unknown |
| 2018 | 5.325 | 2.338 | 2.987 | 2.987 | 127.75876817792987 | actual_per_weo_metadata | unknown |
| 2019 | 5.1 | 2.237 | 2.8629999999999995 | 2.8629999999999995 | 127.9839070183281 | actual_per_weo_metadata | unknown |
| 2020 | 10.4 | 2.522 | 7.878 | 7.878 | 312.3711340206186 | actual_per_weo_metadata | unknown |
| 2021 | 7.792 | 3.398 | 4.394 | 4.394 | 129.31135962330782 | actual_per_weo_metadata | unknown |
| 2022 | 5.4 | 2.598 | 2.8020000000000005 | 2.8020000000000005 | 107.85219399538109 | actual_per_weo_metadata | unknown |
| 2023 | 4.358 | 2.2 | 2.1579999999999995 | 2.1579999999999995 | 98.09090909090907 | actual_per_weo_metadata | unknown |
| 2024 | 3.817 | 2.202 | 1.6150000000000002 | 1.6150000000000002 | 73.34241598546777 | actual_per_weo_metadata | unknown |
| 2025 | 4.208 | 2.235 | 1.9730000000000003 | 1.9730000000000003 | 88.27740492170024 | actual_per_weo_metadata | unknown |

## Interpretation limits

- This utility validates and summarizes the supplied comparison artifact; it does not retrieve original source records or source revision histories.
- A persistent discrepancy is a review priority, not proof that either provider is wrong.
- IMF actual status is only the comparison's hint from LATEST_ACTUAL_ANNUAL_DATA; WDI status is not classified.
- A same-numbered year may not represent the same reporting period; fiscal-year metadata is preserved but not shifted.
- Relative differences are unstable when the WDI denominator is close to zero; inspect absolute differences and source values as well.
- The live WDI API comparison is not vintage-aligned with the fixed IMF October 2026 export.
- No source policy, approval, release, or canonical database action is performed.
