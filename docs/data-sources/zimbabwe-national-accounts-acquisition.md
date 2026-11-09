# ZIMSTAT national-accounts workbook acquisition

## Scope and source boundaries

The acquisition captures two distinct official ZIMSTAT workbooks used in the Zimbabwe GDP/PPP reconciliation:

1. **GDP Trends 2009 to 2018** — legacy XLS workbook, published in 2019.
2. **Revised Annual 2023 GDP and 2024 Annual GDP / GDP Tables 2019–2024** — XLSX workbook published 27 June 2025.

These are separate publication datasets with separate Project DB dataset identities, acquisition streams, raw paths and manifest directories. Do not concatenate their series or assume a continuous currency basis. Preserve workbook labels, units, currency columns, publication dates and revision context.

The ZIMSTAT National Accounts page is the discovery/landing page. The configured download URLs are the exact workbook URLs used by this acquisition. The June 2025 XLSX endpoint is the verified \`GDP_Tables_2019_2024_June.xlsx\` file; an earlier guessed filename \`Publish_GDP_Tables_2019_2024_37062025.xlsx\` returned HTTP 404 and is not configured.

## Automated acquisition

From the repository root, direct HTTPS:

\`\`\`fish
uv run python -m tools.acquire_zimbabwe_national_accounts
\`\`\`

Through the local SOCKS5 proxy, including proxy-side DNS resolution:

\`\`\`fish
uv run python -m tools.acquire_zimbabwe_national_accounts \\
    --socks5-proxy 127.0.0.1:10808
\`\`\`

The command:
- downloads both configured official workbooks;
- supports an optional SOCKS5 proxy via curl's \`--socks5-hostname\`;
- uses a 120-second per-download maximum and up to three curl retries by default;
- validates the legacy XLS OLE compound-file signature and the XLSX ZIP container, including \`xl/workbook.xml\` and ZIP CRC integrity;
- writes each workbook under its own stable raw path;
- writes one immutable timestamped manifest per dataset acquisition, including requested/final URL, content type, byte count, SHA-256, publication date and retrieval timestamp;
- skips a previously acquired workbook only when its raw bytes and every existing manifest agree;
- refuses to overwrite an unmanifested raw workbook or a manifest/raw mismatch;
- continues to the second publication if the first download fails and returns a non-zero exit status if either fails.

Raw workbooks remain local-only. Manifests are tracked. Format validation and hashes do not constitute statistical-content review, semantic validation, source approval, source selection, release promotion or Game DB application.

## Manifest audit and Project DB registration

Read-only audit, catalogue synchronization and registration preflight:

\`\`\`fish
uv run python -m tools.process_zimbabwe_national_accounts
\`\`\`

After reviewing a clean \`ready_for_registration\` result, explicitly register both events and their artifact records in the Project DB:

\`\`\`fish
uv run python -m tools.process_zimbabwe_national_accounts --register
\`\`\`

The processing command requires exactly two clean manifests and two eligible dataset/stream mappings. It never writes the Game DB and does not approve or apply statistical values.

## Source references

- ZIMSTAT National Accounts landing page: https://www.zimstat.co.zw/national-accounts/
- GDP Trends 2009–2018 XLS: https://www.zimstat.co.zw/wp-content/uploads/Macro/NationalAccounts/Publications/GDP_Trends_2009to2018.xls
- Revised GDP tables 2019–2024 XLSX: https://www.zimstat.co.zw/wp-content/uploads/Macro/NationalAccounts/2025/GDP_Tables_2019_2024_June.xlsx

## Validation commands

\`\`\`fish
uv run python -m pytest -v \\
    tests/test_zimbabwe_national_accounts_acquisition.py \\
    tests/test_process_zimbabwe_national_accounts.py

uv run python -m compileall -q \\
    tools/acquire_zimbabwe_national_accounts.py \\
    tools/process_zimbabwe_national_accounts.py
\`\`\`

Owner-run validation results are recorded here after the local commands have been executed.
