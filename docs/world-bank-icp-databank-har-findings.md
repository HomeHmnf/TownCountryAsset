# World Bank ICP DataBank HAR findings

## Captures inspected

Both HAR files on `work/compiler-hardening` were parsed as HAR 1.2, including the page HTML, loaded JavaScript, request bodies, response status codes, and JSON response bodies.

| Capture | Report URL | Cube ID | HAR entries |
|---|---|---:|---:|
| `icp2005.har` | `https://databank.worldbank.org/id/4129804e` | `1009` | 83 |
| `icp2021.har` | `https://databank.worldbank.org/id/1da9d9a2?Report_Name=ICP-Annual-PPPs` | `3869` | 225 |

The 2021 capture contains an earlier ICP 2005 page load as well as the ICP 2021 page load. The ICP 2021 session is the second report-page request.

## Confirmed browser contract

The report page declares these client-side endpoints:

- Dimension metadata: `/AjaxServices/AjaxReportMethods.asmx/GetDimensionJSON`
- Selected-variable registration: `/AjaxDownload/SelectVariableHandler.ashx`
- Export descriptor: `/AjaxDownload/FileInfoHandler.ashx`
- Export download: `/AjaxDownload/FileDownloadHandler.ashx`

The browser's `setSelectedVariables()` serializes the hidden input `hdnSelectVars` and POSTs that form field to `gbl_select_variables_url`. Its payload is an array of dimension objects containing `controlid`, `memberdetails`, and `aggregationruleall`. Each member contains `uniquename`, `displayname`, `iscustom`, `customdefinition`, and `AggregationRule`.

The browser's `loadDimensionList()` calls `GetDimensionJSON` with `cubeid`, `controlid`, and the hierarchy name. The captured hierarchy names match the Python implementation:

- `[Country].[List]`
- `[Classification].[List]`
- `[Series].[List]`
- `[Time].[List]`

The Python implementation's dimension order, endpoint paths, and selected-variable form field are consistent with the inspected browser source.

## Actual dimension responses

### ICP 2005 (cube 1009)

- Classification returned 16 members and a populated `Sel`.
- Series returned 47 members and a populated `Sel`.
- Country returned HTTP 200 with an all-null `MemberListJSON` envelope.
- Time returned HTTP 200 with the same all-null envelope.

### ICP 2021 (cube 3869): successful capture on 2026-11-19

The new browser capture is split across `temp/browser-captures/newfile-parts/part-001.har` through `part-012.har`. In `part-010.har`, the dimension requests at entries 0, 4, 9, and 12 all returned HTTP 200 with populated responses:

| Dimension | DT | Members | Sel |
|---|---:|---:|---:|
| Country | C | 207 | 184 |
| Classification | N | 17 | 1 |
| Series | S | 48 | 6 |
| Time | T | 7 | 7 |

Important response-shape observations:

- `Members` is a list of available member records; it is not the selected set.
- `Sel` is a dictionary keyed by each selected member's unique name.
- `Levels` is empty for Country, Classification, and Time in this successful capture. This is valid and must not be treated as an uninitialized dimension.
- `DT` is the dimension type marker (`C`, `N`, `S`, or `T`), not a count.
- Country has 207 available members but 184 selected members.

The same capture records successful selected-variable registration with 184 Country members, one Classification member, six Series members, and seven Time members. FileInfo requests for CSV, Excel, and tab-delimited output returned HTTP 200; the corresponding downloads also returned HTTP 200. The CSV request's browser form includes `ddl-excel-format=xlsx` even though `down-radio=csv`.

## Fix applied

`_dimension_response()` recognizes the all-null envelope signature (all of `Levels`, `Members`, `DT`, and `Sel` are null) as an uninitialized server response and fails immediately rather than retrying it. It does not reject an empty `Levels` list when the other response fields are populated.

The FileInfo CSV form now matches the successful browser request captured in `part-010.har`, including `ddl-excel-format=xlsx` and excluding fields not present in that captured request. The regression test asserts the complete CSV form field set.

## What the HARs do not prove

Neither capture contains a successful user-driven Country/Time selection followed by the complet## What the HARs do not prove

The new capture establishes one successful ICP 2021 browser export sequence and its selected-variable registration. It does not establish that every saved report, report release, or selection configuration will behave identically. The HAR contains sensitive session and request material; keep the captures private and do not publish them without reviewing and redacting request headers, cookies, tokens, and bodies.
