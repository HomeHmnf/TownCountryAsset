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
- Country returned HTTP 200 but an empty `MemberListJSON` envelope: `Levels`, `Members`, `DT`, and `Sel` were all null.
- Time returned the same empty envelope.

### ICP 2021 (cube 3869)

- Classification returned 17 members; its selected set contained only `PPPGlob` (Purchasing power parity (PPP) (US$ = 1)).
- Series returned 48 members; its selected set contained six indicators.
- Country returned HTTP 200 with the same all-null envelope.
- The Time request ended with HAR status 0 and no response body.

These responses do **not** establish a valid Country or Time selection. In particular, a null `Sel` must not be silently interpreted as “all members selected”: the browser capture provides no evidence for that assumption.

## Fix applied

`_dimension_response()` previously treated the all-null server envelope as a generic malformed response and retried it with exponential backoff. The captures show this is a deterministic server response, not a transport timeout. The acquisition code now recognizes this exact empty-envelope signature and fails immediately with a dimension-specific diagnostic. A regression test verifies that it performs only one request even when retries are configured.

This is a fail-fast correction, not a claim that the captured reports are now exportable. It prevents long, futile retries and prevents the acquisition pipeline from fabricating a selection for Country or Time.

## What the HARs do not prove

Neither capture contains a successful user-driven Country/Time selection followed by the complete export workflow. The HARs do not contain successful requests to `SelectVariableHandler.ashx`, `FileInfoHandler.ashx`, or `FileDownloadHandler.ashx`. Consequently, the browser-side endpoint names are confirmed from the loaded page and JavaScript, but the exact POST body and export option values currently used by the Python client are not yet validated against a real successful browser export.

The next required capture must include opening Country and Time, changing or confirming their selections, applying the variable changes, and completing a CSV export. It should retain request and response bodies for the three handlers above. Until then, changing the current export form fields would be guesswork.
