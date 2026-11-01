# Flag source discovery and review

- Run time (UTC): 2026-10-26T15:56:54.775682+00:00
- Status: REVIEW REQUIRED
- Source repository: https://github.com/lipis/flag-icons
- Configured ref: main
- Resolved commit: ac7e0eb3259eb62aa6100c435607e2fe03896a97
- Retrieved (UTC): 2026-10-26T15:56:54Z
- Archive SHA-256: 478bf8407080f3e8a0ed8b688f29daf7fcaed585be829fe3f980229e35b2f3ae
- Available source SVG codes: 257
- Registry records: 242
- Unconfirmed/unusable mappings: 242
- Manual SVG directory: /home/hmnf/Projects/Python/TownAndCountry/raw_data/flags/manual
- Manual SVG files found: 0
- ISO operator confirmation: yes
- ISO reference selected: /home/hmnf/Projects/Python/TownAndCountry/data/reference/iso/iso-3166-1.csv
- ISO note: Operator confirmed the manual reference; validated 249 rows from /home/hmnf/Projects/Python/TownAndCountry/data/reference/iso/iso-3166-1.csv.

## Seven edge cases

| Territory                   | game_id                             | Mapping status | Candidate source codes found | Evidence URL                                                          | Review guidance                                                                                                                                                         |
| --------------------------- | ----------------------------------- | -------------- | ---------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Falkland Islands            | tc_815eb2563fde4a4cb077173220e2a533 | unreviewed     | fk (available)               | https://www.gov.fk/about/                                             | The lipis source is expected to contain fk. Verify the territorial flag and add FK/FLK ISO metadata only from authoritative evidence.                                   |
| Somaliland                  | tc_9a78f2eebcc24906a5c67581c0c3895e | unreviewed     | no safe automatic candidate  | https://govsomaliland.org/                                            | No official ISO 3166-1 alpha-2/alpha-3 assignment. Use a source flag only if the artwork is explicitly Somaliland's flag; otherwise review a manual SVG.                |
| Somaliland                  | tc_a3f73fd3bb6d4d7fb4ea31d433453bae | unreviewed     | no safe automatic candidate  | https://govsomaliland.org/                                            | No official ISO 3166-1 alpha-2/alpha-3 assignment. Use a source flag only if the artwork is explicitly Somaliland's flag; otherwise review a manual SVG.                |
| Kosovo                      | tc_28aa17b84db24952b92fc51b421075e0 | unreviewed     | xk (available)               | https://president-ksgov.net/en/legislation/                           | XK/XKX are user-assigned conventions, not official ISO 3166-1 assignments. Verify a Kosovo-specific flag and record the source identifier separately from ISO metadata. |
| Northern Cyprus             | tc_d3e7f81572fd44ab920bfc066d592873 | unreviewed     | no safe automatic candidate  | https://mfa.gov.ct.tr/                                                | No official ISO 3166-1 assignment. Verify the artwork and political/territorial representation before mapping a source or manual SVG.                                   |
| Northern Cyprus             | tc_3c148b1f7650455fa710ca87cf376728 | unreviewed     | no safe automatic candidate  | https://mfa.gov.ct.tr/                                                | No official ISO 3166-1 assignment. Verify the artwork and political/territorial representation before mapping a source or manual SVG.                                   |
| Indian Ocean Territories    | tc_73138c628d2a4509bad88f66deb5b27b | unreviewed     | no safe automatic candidate  | https://www.gov.uk/world/organisations/british-indian-ocean-territory | Resolve the exact entity represented by this Natural Earth record before choosing a flag. Do not assume it means the British Indian Ocean Territory.                    |
| Indian Ocean Territories    | tc_39ad5030b5f94f068d4a1528c60e5638 | unreviewed     | no safe automatic candidate  | https://www.gov.uk/world/organisations/british-indian-ocean-territory | Resolve the exact entity represented by this Natural Earth record before choosing a flag. Do not assume it means the British Indian Ocean Territory.                    |
| Indian Ocean Territories    | tc_7cd2130353a64e57bd3782773a8e12c7 | unreviewed     | no safe automatic candidate  | https://www.gov.uk/world/organisations/british-indian-ocean-territory | Resolve the exact entity represented by this Natural Earth record before choosing a flag. Do not assume it means the British Indian Ocean Territory.                    |
| Ashmore and Cartier Islands | tc_b61ca098adb74efc84564fd9fa800bf8 | unreviewed     | no safe automatic candidate  | https://www.dcceew.gov.au/                                            | Decide explicitly whether the game representation should use Australia's flag or another approved representation; do not infer this from geography.                     |
| Siachen Glacier             | tc_644aaabf37604038996e34c1bc91c970 | unreviewed     | no safe automatic candidate  | https://www.britannica.com/place/Siachen-Glacier                      | This is a geographic feature, not an ISO 3166-1 country. Do not assign a national flag by inference; decide whether a neutral marker is appropriate.                    |

## Unconfirmed or unusable mappings

A mapping is unresolved when it is not marked reviewed or its selected source SVG/manual SVG is unavailable. This report does not approve or edit any mapping.

| Territory | game_id | Source code | Manual SVG path | Status |
|---|---|---|---|---|
| Zimbabwe | tc_168ca96e60634f5d83f3f22ad2505e66 | — | — | unreviewed |
| Zambia | tc_e75bc9ac62fa443c90b5529778f3b1af | — | — | unreviewed |
| Yemen | tc_e32ec835b247449084d1b535ebccf7f1 | — | — | unreviewed |
| Vietnam | tc_e65eabf3cd054585a43347bdfea6201b | — | — | unreviewed |
| Venezuela | tc_1aa00cb7ebb34cdca928353a58ff5b12 | — | — | unreviewed |
| Vatican | tc_a8a10a8bdf13428593d1b0ab46990697 | — | — | unreviewed |
| Vanuatu | tc_43c4be0a76ca43a2bb7e634de5a1f4f4 | — | — | unreviewed |
| Uzbekistan | tc_5d951c36a4ad4471ae9b9037fe338d70 | — | — | unreviewed |
| Uruguay | tc_e19506c4a1564ca085b73b9284fa6f56 | — | — | unreviewed |
| Federated States of Micronesia | tc_4add61cba99b4e63a37406cd1d0feb5f | — | — | unreviewed |
| Marshall Islands | tc_f201b19690a04a8f903f9ea4cb0c7af4 | — | — | unreviewed |
| Northern Mariana Islands | tc_07747651759a40219ba3f4710fa6ab11 | — | — | unreviewed |
| United States Virgin Islands | tc_504d6ccab85e4fbdad7ddd881dd6d87d | — | — | unreviewed |
| Guam | tc_ff2aa3765a3d4ee4a6d0c0bd0fb61ddd | — | — | unreviewed |
| American Samoa | tc_ab146a31fa9243bc81a35e9cfaa1ed05 | — | — | unreviewed |
| Puerto Rico | tc_37f10315a18d4c3abf3486086b5822e1 | — | — | unreviewed |
| United States of America | tc_f0a8b61c54a14d4089774716657e9433 | — | — | unreviewed |
| South Georgia and the Islands | tc_c08d501548d346c3ad3e27b514e1e902 | — | — | unreviewed |
| British Indian Ocean Territory | tc_73138c628d2a4509bad88f66deb5b27b | — | — | unreviewed |
| Saint Helena | tc_9bd5e00f9fc944edbf2eb3097e413328 | — | — | unreviewed |
| Pitcairn Islands | tc_0900903d1eb84838aae9c039c9fd0da2 | — | — | unreviewed |
| Anguilla | tc_0b9688bbf4264477b023a0f2af180c2e | — | — | unreviewed |
| Falkland Islands | tc_815eb2563fde4a4cb077173220e2a533 | — | — | unreviewed |
| Cayman Islands | tc_19acfc8e1cf44c25aa753729115d60d6 | — | — | unreviewed |
| Bermuda | tc_d81e2d4c4b934f57a67f380b2fdaec9d | — | — | unreviewed |
| British Virgin Islands | tc_f3832fd029cb445483c26654bddadfac | — | — | unreviewed |
| Turks and Caicos Islands | tc_ea6ba8b48782477bad74e946641a16ae | — | — | unreviewed |
| Montserrat | tc_bb1615e8a28b4b3f8a248ca8a5e6fa6d | — | — | unreviewed |
| Jersey | tc_43796017cb7d4a279de2d9ed65c32c80 | — | — | unreviewed |
| Guernsey | tc_be9b1fd97db1475191612805ba7f9920 | — | — | unreviewed |
| Isle of Man | tc_f94f97a8ffc24ef18872cadb5736ea2b | — | — | unreviewed |
| United Kingdom | tc_8d01644699e04b74ae3a4751c6f1fc41 | — | — | unreviewed |
| United Arab Emirates | tc_3cbd960008724744b928265acc0638a4 | — | — | unreviewed |
| Ukraine | tc_65f8a168b10143c2a596917c1fca3731 | — | — | unreviewed |
| Uganda | tc_2bd67b30564b46b4b502a36decc333bf | — | — | unreviewed |
| Turkmenistan | tc_72de9a194d85404098bb741ae4ffc826 | — | — | unreviewed |
| Turkey | tc_155414257ec0498690f73c3595d85e7c | — | — | unreviewed |
| Tunisia | tc_1d1d2c1274384efa82f9591e1c069aba | — | — | unreviewed |
| Trinidad and Tobago | tc_1bd98a138f884dd4b4d9d1efbbf357b0 | — | — | unreviewed |
| Tonga | tc_2c6f6c5486f04a87aa94277e67d6e51a | — | — | unreviewed |
| Togo | tc_06a09ff0e27b49e392ef2e88161023eb | — | — | unreviewed |
| East Timor | tc_bd40ea14860a4c4083eced5549d2d9c4 | — | — | unreviewed |
| Thailand | tc_fc12d0184fc7498f982ab8033ae64436 | — | — | unreviewed |
| United Republic of Tanzania | tc_0f4c47ec59434e46871845e474964499 | — | — | unreviewed |
| Tajikistan | tc_772e2ac5253c46e98b79cf5a6f19e9f5 | — | — | unreviewed |
| Taiwan | tc_98ab3dee1d554162b6bbd5dac6374fc8 | — | — | unreviewed |
| Syria | tc_c205b2615c45490182519ecedb651e99 | — | — | unreviewed |
| Switzerland | tc_e693e8b799f94e7bb814e89bd46d886d | — | — | unreviewed |
| Sweden | tc_d74b429fff544cf9bafeb459c4b3edd8 | — | — | unreviewed |
| eSwatini | tc_fc2ad04f3c88446e91bd770190d6fe4c | — | — | unreviewed |
| Suriname | tc_168a848021b84cc6a6c3fc320012a176 | — | — | unreviewed |
| South Sudan | tc_12491d45eed544948b316c89f82a7ee7 | — | — | unreviewed |
| Sudan | tc_b0ca3e0386b34603a6356b8ebc8b0565 | — | — | unreviewed |
| Sri Lanka | tc_5e47c88bebac452e953fc5dfa8b1ba06 | — | — | unreviewed |
| Spain | tc_21a70a0fbf1b43c292783397ce218239 | — | — | unreviewed |
| South Korea | tc_cf8be733dbf44dd6b112e9fe12d2b19e | — | — | unreviewed |
| South Africa | tc_dc6419869818416db051f50cbfd95036 | — | — | unreviewed |
| Somalia | tc_e82cc51b989841109d9e1a7f6a5d1727 | — | — | unreviewed |
| Somaliland | tc_9a78f2eebcc24906a5c67581c0c3895e | — | — | unreviewed |
| Solomon Islands | tc_0ce7eb254c32428c88601905c0df8e87 | — | — | unreviewed |
| Slovakia | tc_b3bea891d7114d148714d5e398ee06b1 | — | — | unreviewed |
| Slovenia | tc_c0484640d9554c8285e92412bae25785 | — | — | unreviewed |
| Singapore | tc_9d65e06bf97d417c8aa62742225ef5c9 | — | — | unreviewed |
| Sierra Leone | tc_56e9d1977fa14da298ae125fbda1b63c | — | — | unreviewed |
| Seychelles | tc_4bc377d3ea57485bac43c9b512587dbc | — | — | unreviewed |
| Republic of Serbia | tc_98a68180b9f0479f90dcde7809d60470 | — | — | unreviewed |
| Senegal | tc_29ec74ae4e094053a930487b9ce602d1 | — | — | unreviewed |
| Saudi Arabia | tc_86b0f7fcb4504f9b8dc1b60b42b16ea0 | — | — | unreviewed |
| São Tomé and Principe | tc_4a2ed326dc6047efa2e28926df0bc7f0 | — | — | unreviewed |
| San Marino | tc_e4ea859bd6704c13912ad7f5cf19de41 | — | — | unreviewed |
| Samoa | tc_76082bd796c546d1ab76a7a8a3251369 | — | — | unreviewed |
| Saint Vincent and the Grenadines | tc_67290f5714c846f4a84d1f53c6fd495a | — | — | unreviewed |
| Saint Lucia | tc_6629fdb92d05409f856d9030b63b1470 | — | — | unreviewed |
| Saint Kitts and Nevis | tc_f22d58e7280f41f7a5a68fb03e1ab87e | — | — | unreviewed |
| Rwanda | tc_7f3c6637070f4c42a40c1f5456ec4721 | — | — | unreviewed |
| Russia | tc_c587d1c1cd8d4ec489f3d8e2524ec607 | — | — | unreviewed |
| Romania | tc_c41863f7cb4e4dccbbdf0a1296f9ee1c | — | — | unreviewed |
| Qatar | tc_13df99232f33400d9079316c041f066c | — | — | unreviewed |
| Portugal | tc_43ee3db974884a72bacf5f5519e2c145 | — | — | unreviewed |
| Poland | tc_9865dd6a50c3458b98f5040f0cc76357 | — | — | unreviewed |
| Philippines | tc_fc8f1a9536d342899526129acf15acd2 | — | — | unreviewed |
| Peru | tc_a90d391a4a9a473b9074fc99cce11cb5 | — | — | unreviewed |
| Paraguay | tc_3eb6dc12494541e793a8a5b68980f29f | — | — | unreviewed |
| Papua New Guinea | tc_82d51d964745422e8ed3a9109757d2ee | — | — | unreviewed |
| Panama | tc_ba6cf14fa6224eb4a0b085b3ea1df6dc | — | — | unreviewed |
| Palau | tc_642fbe2581cf4b8c857d967717d1f1ef | — | — | unreviewed |
| Pakistan | tc_0dc6216a94e34b44b27e42ed35fa6376 | — | — | unreviewed |
| Oman | tc_22bd85ff61234a46a95506d105d5fee4 | — | — | unreviewed |
| Norway | tc_f4a6e15a05474af2b81c9524ed988d89 | — | — | unreviewed |
| North Korea | tc_4a3793e49e5441ae94aeec78cc887021 | — | — | unreviewed |
| Nigeria | tc_7a8158c93a934345a2ade9fd16ee4999 | — | — | unreviewed |
| Niger | tc_4d31375845614c2b91a71736069d4ab3 | — | — | unreviewed |
| Nicaragua | tc_2fdae8757e51402e9f67c428d2b79368 | — | — | unreviewed |
| New Zealand | tc_d4b67e03f0c04d9a87089f477e5fa669 | — | — | unreviewed |
| Niue | tc_4cb90152915543348c9a793599240eaa | — | — | unreviewed |
| Cook Islands | tc_d0017ca5d5084ceeaedc02b6d436fb39 | — | — | unreviewed |
| Netherlands | tc_898b220cf53a425e9bac3630f2c17473 | — | — | unreviewed |
| Aruba | tc_8344feaf14da4684aaa8d4c263653778 | — | — | unreviewed |
| Curaçao | tc_2d0dc3f3edb9467090ea74861dbc7b9e | — | — | unreviewed |
| Nepal | tc_1c4ff3f2a8f04b43b0c28e830a9403ad | — | — | unreviewed |
| Nauru | tc_2722269bdef04648b655fe363650d565 | — | — | unreviewed |
| Namibia | tc_7379cdcc5c4848c181ace3144aeba70f | — | — | unreviewed |
| Mozambique | tc_2249b79a9c944a1c835b0cad2676e48d | — | — | unreviewed |
| Morocco | tc_84dc0c18f03144bea337f6aacd50bf0f | — | — | unreviewed |
| Western Sahara | tc_3487eebc07114ff589974150237cae4f | — | — | unreviewed |
| Montenegro | tc_eb1de71332ef4db496cb76c95aa56cd4 | — | — | unreviewed |
| Mongolia | tc_d0fb202ca0aa4a868af6fa154ab84c30 | — | — | unreviewed |
| Moldova | tc_96ea5c49288d40b0945401031405c2c8 | — | — | unreviewed |
| Monaco | tc_da92472e602c45c69d331812fa5193d8 | — | — | unreviewed |
| Mexico | tc_c6b830c3cba64d4883eac8cee7864cfd | — | — | unreviewed |
| Mauritius | tc_c7b728ec16b94e35b05d96d14a253eec | — | — | unreviewed |
| Mauritania | tc_17137c4e4fcc4fa58e32c924f08efcda | — | — | unreviewed |
| Malta | tc_f97b2223a2a84e53ac13614ddde1f602 | — | — | unreviewed |
| Mali | tc_a3f73fd3bb6d4d7fb4ea31d433453bae | — | — | unreviewed |
| Maldives | tc_408d22fe5b894b4b947a0521ace1018a | — | — | unreviewed |
| Malaysia | tc_b21225f45c3b40509640603249110f89 | — | — | unreviewed |
| Malawi | tc_ee1c1ac1ad5c4faf818070115133b174 | — | — | unreviewed |
| Madagascar | tc_7abbe0f9aa1346c7a9f69cc1027b4282 | — | — | unreviewed |
| North Macedonia | tc_949bf877e3284f5c8a56cfc89bcafa90 | — | — | unreviewed |
| Luxembourg | tc_f4261f4507cd48858cdfb7e3bd0ae738 | — | — | unreviewed |
| Lithuania | tc_77de0a41c4d94d8388d6f0732438be81 | — | — | unreviewed |
| Liechtenstein | tc_a8bd42bd635b43289f3c26695dc58939 | — | — | unreviewed |
| Libya | tc_bb5622bab363429ca481c5476acc824c | — | — | unreviewed |
| Liberia | tc_40dc9d2e141343e98a4d0c762c578473 | — | — | unreviewed |
| Lesotho | tc_c0fa4e9b8e984f59ba17beb7547c5811 | — | — | unreviewed |
| Lebanon | tc_8466a0747d0b4d1a8c23feb70f7c6ed1 | — | — | unreviewed |
| Latvia | tc_f161aef25a39413e8aef8c147e97b28a | — | — | unreviewed |
| Laos | tc_71a3ecd24ca74da9a6cea3dae8cd1f82 | — | — | unreviewed |
| Kyrgyzstan | tc_130ca81b84d04b058e9301121b2b7802 | — | — | unreviewed |
| Kuwait | tc_fa491c61ffa24dc3a21c6a6da7d39fad | — | — | unreviewed |
| Kosovo | tc_28aa17b84db24952b92fc51b421075e0 | — | — | unreviewed |
| Kiribati | tc_c23a3cf00b1a4ebf97a70a4f41a7761d | — | — | unreviewed |
| Kenya | tc_9f3dc962bf9744a5a3cdf1f7a1cbb159 | — | — | unreviewed |
| Kazakhstan | tc_feadffc011db4cf695df6c0997a003c8 | — | — | unreviewed |
| Jordan | tc_6e28258973b54dfeb5811c563cd0a2e8 | — | — | unreviewed |
| Japan | tc_8d0620ea475f498d9402134857882bf1 | — | — | unreviewed |
| Jamaica | tc_bf02736242694622ae7c730beb0f0da6 | — | — | unreviewed |
| Italy | tc_1f3e0c90df4341f082ed90ecdd95fb10 | — | — | unreviewed |
| Israel | tc_28952c75855947a7b31bb7509dc1fce1 | — | — | unreviewed |
| Palestine | tc_50c420df8b2c4c6eaae47d795f9a1ea2 | — | — | unreviewed |
| Ireland | tc_16d6044d9abf4743821a6fb238942a22 | — | — | unreviewed |
| Iraq | tc_5ee7b31f968941dca65e70519901915f | — | — | unreviewed |
| Iran | tc_ddf21c4d378e4fc9bc3d5b4ba50890a2 | — | — | unreviewed |
| Indonesia | tc_c40da0ac977b4201b8587ce04aa66f56 | — | — | unreviewed |
| India | tc_39ad5030b5f94f068d4a1528c60e5638 | — | — | unreviewed |
| Iceland | tc_861af4b9250e4e17a9d3f1f4e1ea33d4 | — | — | unreviewed |
| Hungary | tc_e3ede57c1b754a2dbd940335f9655f11 | — | — | unreviewed |
| Honduras | tc_80c318b9217a4320beaad6b93eb74ac5 | — | — | unreviewed |
| Haiti | tc_9ee610c6d55a4f4bbdbbb073b33628a2 | — | — | unreviewed |
| Guyana | tc_893d4efa8ccf42af896949ffd7007fef | — | — | unreviewed |
| Guinea-Bissau | tc_dc93b6caf7324df884ec2b070a5296b9 | — | — | unreviewed |
| Guinea | tc_05eaf88055cc4388b518332f2e7fc115 | — | — | unreviewed |
| Guatemala | tc_9348779eba844ab2beb5bed00053b7c6 | — | — | unreviewed |
| Grenada | tc_c5b3fecc12a94e85a7acddc70fa7a086 | — | — | unreviewed |
| Greece | tc_dab67464d7ad44cdbf925450627e4186 | — | — | unreviewed |
| Ghana | tc_f63061b714ce4390948838410758c016 | — | — | unreviewed |
| Germany | tc_ff445b0a87494070bf868827de190acf | — | — | unreviewed |
| Georgia | tc_741bd244c1ec4961918565c4ed02c5c6 | — | — | unreviewed |
| Gambia | tc_d1d3a8eb94cb4a558b51f3bd73cb4b2a | — | — | unreviewed |
| Gabon | tc_d59dfb6324524b07a32c87b73009e97f | — | — | unreviewed |
| France | tc_471ae6d7112b4537a7ae5ca1e6a816a5 | — | — | unreviewed |
| Saint Pierre and Miquelon | tc_5551c0cc249f4e4e9ea6d57a0dacd2d5 | — | — | unreviewed |
| Wallis and Futuna | tc_9f1be169ba5347ff81384c532820401b | — | — | unreviewed |
| Saint Martin | tc_cc0688860b8848ddb5f52395162d9b71 | — | — | unreviewed |
| Saint Barthelemy | tc_e0f0ed8d4d284acd8b41435902f2a6cc | — | — | unreviewed |
| French Polynesia | tc_2493e62a2f78442e8fd4b8c0f0ca847c | — | — | unreviewed |
| New Caledonia | tc_e7d7320224a64229881b6b49ef1e74c3 | — | — | unreviewed |
| French Southern and Antarctic Lands | tc_c84e6493c6fc4373842ee9ba3a509db0 | — | — | unreviewed |
| Aland | tc_592dfefc0b584872853eedbd05b5e970 | — | — | unreviewed |
| Finland | tc_374e55a3eefe4a1a83fed6b64b5045f5 | — | — | unreviewed |
| Fiji | tc_8d67737674744dce8986565b98cbbb1f | — | — | unreviewed |
| Ethiopia | tc_860d12ee66fc4fceb3faddbc92c87930 | — | — | unreviewed |
| Estonia | tc_383873de760147cd97dfac5ef5d60b08 | — | — | unreviewed |
| Eritrea | tc_f9d7128c5ef04c6f955f43f9bcc56a0c | — | — | unreviewed |
| Equatorial Guinea | tc_06d71df13c4f415fbf22a0147f19bc53 | — | — | unreviewed |
| El Salvador | tc_471268dbb85845de93e546317686debb | — | — | unreviewed |
| Egypt | tc_939f236600dd47a8bf850a7ff19dc047 | — | — | unreviewed |
| Ecuador | tc_2a54eb1caed54a2185a62cce0c2db6cb | — | — | unreviewed |
| Dominican Republic | tc_ee04e01170f84b92afabbb40abdbd4e3 | — | — | unreviewed |
| Dominica | tc_e5391af862dd490bb3a01fa80f4ac15e | — | — | unreviewed |
| Djibouti | tc_f4814b1a89384c4d93a92c19b301a814 | — | — | unreviewed |
| Greenland | tc_cbf271e54b9c4e3fbaa93c291355f6f7 | — | — | unreviewed |
| Faroe Islands | tc_d608e7f9138e459ab3b96263618ae407 | — | — | unreviewed |
| Denmark | tc_11da440eb0704bd195fe0b11fa0890af | — | — | unreviewed |
| Czechia | tc_e43afc3a83a3458c833dac5644b7186a | — | — | unreviewed |
| Northern Cyprus | tc_d3e7f81572fd44ab920bfc066d592873 | — | — | unreviewed |
| Cyprus | tc_3c148b1f7650455fa710ca87cf376728 | — | — | unreviewed |
| Cuba | tc_576e758e1fbb456a973d63c58222dc30 | — | — | unreviewed |
| Croatia | tc_fb4046d4910a4bf89f4a93810e2f4d8a | — | — | unreviewed |
| Ivory Coast | tc_18c639798e4948899643d84aa2bce93c | — | — | unreviewed |
| Costa Rica | tc_79512b2eaf8f45b5b118130859ebdaaf | — | — | unreviewed |
| Democratic Republic of the Congo | tc_2763c19aa8734ce9aa8b17d8effb6645 | — | — | unreviewed |
| Republic of the Congo | tc_451d8109e28b45eaa6923dfcac9d1601 | — | — | unreviewed |
| Comoros | tc_10dd5e9664664abf9eca33c250a74cdb | — | — | unreviewed |
| Colombia | tc_648b019cc83e486ab9fb8497386777a9 | — | — | unreviewed |
| China | tc_3349a0b8b7454088b11e917a24de3ad5 | — | — | unreviewed |
| Macao S.A.R | tc_f9a64d8c1e6342d2b1941833ff7588d0 | — | — | unreviewed |
| Hong Kong S.A.R. | tc_394248a9960c4d28b4385210c82a0a0b | — | — | unreviewed |
| Chile | tc_4c51c695cb6e47d2aed2fb04c397bece | — | — | unreviewed |
| Chad | tc_1da2daf3a3d34a30b96100d643963f70 | — | — | unreviewed |
| Central African Republic | tc_9d80376a997845b6ba6bbc08d436a50d | — | — | unreviewed |
| Cabo Verde | tc_d9d1737635ce4385a50c4307c2716832 | — | — | unreviewed |
| Canada | tc_ba9087366ba54d51932e88bf8a11616d | — | — | unreviewed |
| Cameroon | tc_f5cd614ef03c414d8e98d87102df5c14 | — | — | unreviewed |
| Cambodia | tc_f956986338e5418481784ba2d2781063 | — | — | unreviewed |
| Myanmar | tc_b4847e5d14f94efdbbd46d6467d90237 | — | — | unreviewed |
| Burundi | tc_4ac5b3c6b7774a05b4ceb5573c4a9d27 | — | — | unreviewed |
| Burkina Faso | tc_3c920b9b9f324cb19ef9d4b6debf10ba | — | — | unreviewed |
| Bulgaria | tc_523810acde564c1c907acd5befe575ab | — | — | unreviewed |
| Brunei | tc_e416804f7e41490a9e7d743a45a72f0e | — | — | unreviewed |
| Brazil | tc_4923336d91d94afc919d8a2b8a4ad415 | — | — | unreviewed |
| Botswana | tc_ca2bdd688a454bb8b6457c9448612669 | — | — | unreviewed |
| Bosnia and Herzegovina | tc_0628271c897b49558f423321cbc48ce4 | — | — | unreviewed |
| Bolivia | tc_4cd6d52014244914bdeb62e6a6452e42 | — | — | unreviewed |
| Bhutan | tc_91f04a21215642aeb5da856a78dc9949 | — | — | unreviewed |
| Benin | tc_874ae1f05e8c4d67a2c839095d760b72 | — | — | unreviewed |
| Belize | tc_d066174c4df546d1a410d386f363ee80 | — | — | unreviewed |
| Belgium | tc_f1cc713e923c4be48e176657a00469f0 | — | — | unreviewed |
| Belarus | tc_6ebc90b251e14f70b8bf758d8008e839 | — | — | unreviewed |
| Barbados | tc_7a679c592eef40c58b7cdf58e6032bb5 | — | — | unreviewed |
| Bangladesh | tc_8169e562ece7475e960f78f231cb1ab7 | — | — | unreviewed |
| Bahrain | tc_38fd6c5cd2be45739f3be11bc4cab9c8 | — | — | unreviewed |
| The Bahamas | tc_53553c35a9f44fddb64f46b5b2d7b90c | — | — | unreviewed |
| Azerbaijan | tc_b8c860bb8d404dcca918bad769e7ead7 | — | — | unreviewed |
| Austria | tc_a0422e821c824e78bd95525b36155b65 | — | — | unreviewed |
| Australia | tc_270a6ecb902d4ea1ac7373b3d1a3b2cc | — | — | unreviewed |
| Indian Ocean Territories | tc_7cd2130353a64e57bd3782773a8e12c7 | — | — | unreviewed |
| Heard Island and McDonald Islands | tc_e86aec8164734ab8be1b207a743e6ea4 | — | — | unreviewed |
| Norfolk Island | tc_003dbd71493240f5bd22a52176868806 | — | — | unreviewed |
| Ashmore and Cartier Islands | tc_b61ca098adb74efc84564fd9fa800bf8 | — | — | unreviewed |
| Armenia | tc_f97b56c9c74845de8b41aa24ed12a47f | — | — | unreviewed |
| Argentina | tc_2a29d5b72b294244a5de6db37118237a | — | — | unreviewed |
| Antigua and Barbuda | tc_9221f2a3fd704847b66da16efa03c2b8 | — | — | unreviewed |
| Angola | tc_fa43ff476d6b428fa8edb4dde1aa9d3f | — | — | unreviewed |
| Andorra | tc_224c06bfe0f04031b422bddc81ea3ce5 | — | — | unreviewed |
| Algeria | tc_e245d37005f843168d67b7b327ece7f9 | — | — | unreviewed |
| Albania | tc_4d8b70a33bce41a9b8bf8fbe22d6d0f1 | — | — | unreviewed |
| Afghanistan | tc_928d15fd89764353a6889f571bfd0a1c | — | — | unreviewed |
| Siachen Glacier | tc_644aaabf37604038996e34c1bc91c970 | — | — | unreviewed |
| Antarctica | tc_c3c21e18d6e94254a4ca4a009530bac9 | — | — | unreviewed |
| Sint Maarten | tc_d79e2777be2741c3bcf291431e2e4efb | — | — | unreviewed |
| Tuvalu | tc_47cd272cd9c9455185a13f6e69bd805c | — | — | unreviewed |

## Source catalogue

Source codes available in the refreshed archive:

`ad`, `ae`, `af`, `ag`, `ai`, `al`, `am`, `ao`, `aq`, `ar`, `as`, `at`, `au`, `aw`, `ax`, `az`, `ba`, `bb`, `bd`, `be`, `bf`, `bg`, `bh`, `bi`, `bj`, `bl`, `bm`, `bn`, `bo`, `bq`, `br`, `bs`, `bt`, `bv`, `bw`, `by`, `bz`, `ca`, `cc`, `cd`, `cf`, `cg`, `ch`, `ci`, `ck`, `cl`, `cm`, `cn`, `co`, `cp`, `cr`, `cu`, `cv`, `cw`, `cx`, `cy`, `cz`, `de`, `dg`, `dj`, `dk`, `dm`, `do`, `dz`, `ec`, `ee`, `eg`, `eh`, `er`, `es`, `et`, `eu`, `fi`, `fj`, `fk`, `fm`, `fo`, `fr`, `ga`, `gb`, `gd`, `ge`, `gf`, `gg`, `gh`, `gi`, `gl`, `gm`, `gn`, `gp`, `gq`, `gr`, `gs`, `gt`, `gu`, `gw`, `gy`, `hk`, `hm`, `hn`, `hr`, `ht`, `hu`, `ic`, `id`, `ie`, `il`, `im`, `in`, `io`, `iq`, `ir`, `is`, `it`, `je`, `jm`, `jo`, `jp`, `ke`, `kg`, `kh`, `ki`, `km`, `kn`, `kp`, `kr`, `kw`, `ky`, `kz`, `la`, `lb`, `lc`, `li`, `lk`, `lr`, `ls`, `lt`, `lu`, `lv`, `ly`, `ma`, `mc`, `md`, `me`, `mf`, `mg`, `mh`, `mk`, `ml`, `mm`, `mn`, `mo`, `mp`, `mq`, `mr`, `ms`, `mt`, `mu`, `mv`, `mw`, `mx`, `my`, `mz`, `na`, `nc`, `ne`, `nf`, `ng`, `ni`, `nl`, `no`, `np`, `nr`, `nu`, `nz`, `om`, `pa`, `pc`, `pe`, `pf`, `pg`, `ph`, `pk`, `pl`, `pm`, `pn`, `pr`, `ps`, `pt`, `pw`, `py`, `qa`, `re`, `ro`, `rs`, `ru`, `rw`, `sa`, `sb`, `sc`, `sd`, `se`, `sg`, `sh`, `si`, `sj`, `sk`, `sl`, `sm`, `sn`, `so`, `sr`, `ss`, `st`, `sv`, `sx`, `sy`, `sz`, `tc`, `td`, `tf`, `tg`, `th`, `tj`, `tk`, `tl`, `tm`, `tn`, `to`, `tr`, `tt`, `tv`, `tw`, `tz`, `ua`, `ug`, `um`, `un`, `us`, `uy`, `uz`, `va`, `vc`, `ve`, `vg`, `vi`, `vn`, `vu`, `wf`, `ws`, `xk`, `xx`, `ye`, `yt`, `za`, `zm`, `zw`

## Manual SVG instructions

1. Put a reviewed SVG in `/home/hmnf/Projects/Python/TownAndCountry/raw_data/flags/manual` (prefer a descriptive filename such as `somaliland.svg`).
2. Keep the original source/evidence URL and licensing details in the mapping record's evidence/decision note.
3. In config/country_flag_mapping.json, set manual_svg_path to the relative filename under the manual directory, source_flag_code to null, and status to reviewed only after human review.
4. Never set status to reviewed just because the file parses; confirm its identity, provenance, and usage rights.
5. Run the separate game-asset build command only after decisions are reviewed.

## ISO manual reference instructions

Operator confirmed the manual reference; validated 249 rows from /home/hmnf/Projects/Python/TownAndCountry/data/reference/iso/iso-3166-1.csv.

## Safety

- No identity registry or mapping records were modified.
- No mapping was auto-approved.
- Candidate assets were not generated by this review command.
