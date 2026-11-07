# Turkmenistan macroeconomic evidence acquisition

## Scope

This source-specific acquisition captures five primary research artifacts relevant to the WDI/IMF WEO nominal-GDP discrepancy and the 2018 conversion-factor break:

- IMF Working Paper 2023/207, *Reassessing GDP Growth in Countries with Statistical Shortcomings: A Case Study on Turkmenistan*.
- TurkmenStat's 17 January 2025 national-accounts methodology notice.
- TurkmenStat's 23 June 2026 statistical-system reform notice.
- IMF's 10 June 2025 Article IV mission statement.
- IMF's 22 June 2026 Article IV mission statement.

The TurkmenStat notices and IMF June 2026 mission statement are retained as HTML captures. The IMF June 2025 statement is retained in the IMF site's structured JSON representation: the canonical article page exposes an official `index.json` alternate and bundle manifest. TurkmenStat URLs use the verified canonical `www.stat.gov.tm` host rather than the `editor` subdomain, whose TLS certificate failed hostname verification in the acquisition environment; the IMF working paper is retained as the publisher's full-text XML because the PDF endpoints did not provide a retrievable PDF in the acquisition environment. Each publication has its own dataset identity, acquisition stream and manifest. This avoids treating distinct publication vintages as one rolling bundle.

## Research relevance and limits

The WDI decomposition snapshot (retrieved 7 November 2026) shows that reported current-USD GDP is reproduced by dividing current-LCU GDP by the DEC alternative conversion factor in every year from 2015 through 2025. The official exchange-rate indicator is missing for Turkmenistan in that capture. The DEC factor moves from 3.98 in 2017 to 5.48 in 2018, coinciding with the sharp WDI/WEO divergence. This arithmetic does not establish that the DEC factor is a parallel-market rate or identify the source of the factor.

The IMF 2023 paper documents the official rate at 3.5 manat per US dollar since 2015 and describes parallel-market rate developments, while cautioning that parallel-market observations are indicative rather than official statistics. Its estimates and analysis are research evidence, not an official statistical series or a substitute for WDI/WEO observations.

TurkmenStat's January 2025 notice reports phased modernization of national-accounts methods and statistical reporting. Its June 2026 notice describes World Bank technical assistance for national accounts under the 2025 SNA and ICP methodology. The notices do not provide a numerical back-series reconciliation in the captured page text.

The IMF 2025 and 2026 mission statements identify exchange-rate unification, the official/parallel-rate gap, and statistical quality as policy issues. The 2026 statement explicitly says the narrative underlying official GDP growth estimates is difficult to reconcile with other available data and that IMF staff use their own GDP estimates. These are IMF staff assessments, not an endorsement of any single WDI or WEO series.

## Automated acquisition

Run from the repository root:

```fish
uv run python -m tools.acquire_turkmenistan_evidence
```

For already downloaded artifacts, `--use-existing` verifies the file signatures and records filesystem modification time as the timestamp basis; it does not misrepresent that time as a verified HTTP retrieval time.

The tool:
- downloads the five official publication records over HTTPS; for IMF Working Paper 2023/207 it falls back to the official eLibrary full-text XML after the media PDF endpoint returns HTTP 403 and the eLibrary PDF endpoint returns HTTP 202; for the June 2025 IMF mission statement it attempts the same article's official IMF `index.json` alternate, whose bundle manifest identifies it as the agent-facing structured representation; both canonical and JSON endpoints currently return HTTP 403 to the acquisition client.
- uses a 120-second timeout and up to three retries for transient transport failures and selected transient HTTP statuses;
- validates PDF, HTML or XML signatures as appropriate;
- writes raw artifacts under `raw_data/sources/`;
- writes one immutable timestamped manifest per publication under `data_manifests/sources/`;
- records URL, final URL, content type, byte count, SHA-256, publication date and retrieval timestamp basis;
- refuses to overwrite a manifest;
- performs no statistical extraction, semantic validation, approval, source selection, release promotion, or SQLite writes.

Raw artifacts remain local-only under the project storage policy. Manifests are tracked. Confirm licensing and redistribution conditions independently before any redistribution.

## Source references

- IMF Working Paper 2023/207 publication record: https://www.imf.org/en/publications/wp/issues/2023/09/29/reassessing-gdp-growth-in-countries-with-statistical-shortcomings-a-case-study-on-539482
- IMF Working Paper 2023/207 official eLibrary full text (XML): https://www.elibrary.imf.org/view/journals/001/2023/207/article-A001-en.xml
- TurkmenStat, 17 January 2025: https://www.stat.gov.tm/en/news/204
- TurkmenStat, 23 June 2026: https://www.stat.gov.tm/en/news/359
- IMF, 10 June 2025 canonical article: https://www.imf.org/en/news/articles/2025/06/10/pr-25190-turkmenistan-imf-completes-2025-article-iv-mission
- IMF, 10 June 2025 structured JSON alternate: https://www.imf.org/en/news/articles/2025/06/10/pr-25190-turkmenistan-imf-completes-2025-article-iv-mission/index.json
- IMF, 10 June 2025 bundle manifest: https://www.imf.org/en/news/articles/2025/06/10/pr-25190-turkmenistan-imf-completes-2025-article-iv-mission/bundle-manifest.json
- IMF, 22 June 2026: https://www.imf.org/en/news/articles/2026/06/22/pr26218-turkmenistan-imf-staff-completes-2026-article-iv-mission

## Validation and provenance status

Owner-run tests, acquisition, manifest audit and Project DB registration are pending. No acquisition or semantic approval is implied by this design document.


### Resume and overwrite protection

The automated acquisition command is resumable. Before downloading a publication, it checks the dataset manifest directory and existing raw artifact. If a prior manifest and raw artifact agree on source, dataset, relative path, SHA-256 and byte count, the publication is reported as `already_acquired_verified` and is not downloaded or overwritten. If a raw artifact exists without a manifest, or an existing manifest does not match the raw artifact, acquisition stops for that publication rather than overwriting evidence. This protects completed events when a later publication in the batch fails. The explicit `--use-existing` mode remains a separate manual integrity-capture path and does not imply an HTTP retrieval timestamp.



### IMF June 2025 structured representation and access fallback

The canonical IMF article landing page and its official `index.json` alternate both returned HTTP 403 to the automated acquisition client. The JSON alternate remains configured because it is the same-host structured representation, but neither endpoint is currently retrievable from this environment. The attributed Publicnow republication also returned HTTP 403 and is not configured as a fallback. The June 2025 statement therefore remains an acquisition gap: no raw artifact or manifest is created, and no third-party copy is substituted. The IMF publication remains independently discoverable through the official IMF page and search-indexed content. A future manual capture must preserve its actual retrieval timestamp basis and URL; content found in a search result is not treated as a captured source artifact.


### Batch failure handling

A transport failure for one publication is recorded in the command's `failures` array with status `acquisition_failed_no_manifest`; the batch continues to later publications. The command exits non-zero if any publication failed, even when other publications were successfully acquired. This permits independent publications in the same batch to be captured without concealing an incomplete batch. A failed publication is not registered as an acquisition and does not create an empty or synthetic manifest.
