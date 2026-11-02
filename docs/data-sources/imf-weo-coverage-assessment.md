# IMF WEO October 2026 coverage assessment

**Status:** read-only assessment tooling implemented; owner-side execution and validation pending  
**Source:** `imf_weo`  
**Input:** manually acquired October 2026 WEO CSV export and Database Appendix

## Reuse of existing project tooling

The assessment follows the existing `tools/assess_world_bank_wdi.py` pattern:
- a provider-specific, read-only assessment module with an argparse CLI;
- timestamped JSON, Markdown and CSV evidence reports;
- explicit side-effect declarations;
- unit tests using fixture inputs;
- no database writes, source policy changes, snapshot acquisition or release promotion.

It reuses the existing source registry, source-selection policy and country identity registry as fingerprinted inputs. It does not duplicate the approval or promotion workflow in `tools/validate_source_release.py`. That workflow remains a later, separate gate and currently requires its own source-specific validation contract before IMF WEO can be proposed for promotion.

## Command

From the repository root:

```fish
uv run python -m tools.assess_imf_weo
```

Optional arguments:

```fish
uv run python -m tools.assess_imf_weo --start-year 2015 --end-year 2025
```

The default range is 1980–2031. The tool writes timestamped reports under:

`reports/sources/imf-weo/<timestamp>/`

Outputs:
- `assessment.json`: complete machine-readable assessment, indicator distributions and series-level records;
- `assessment.md`: human-readable summary and limitations;
- `country_coverage.csv`: country/economy series coverage and identity match status;
- `series_rows.csv`: all five target indicator series, including aggregate rows.

## Scope and safeguards

The tool:
- verifies the CSV and Appendix against the manually recorded SHA-256 and byte counts;
- fingerprints the identity registry, source-selection policy and source registry;
- checks the annual series codes for WP1.5 fields 15, 16, 18, 20 and 21;
- reports units, scales, latest-actual metadata, reporting-year month conventions and non-null year coverage;
- compares three-letter source prefixes against existing registry codes and reports name-match status;
- excludes non-three-letter group prefixes from country identity matching;
- preserves fiscal-year labels without converting them to calendar years;
- leaves PPP GDP status unresolved where latest-actual metadata is absent;
- leaves unemployment unit unresolved while the source unit field is blank.

It does not:
- infer an approved ISO assignment or create a game identity;
- treat all three-letter prefixes as verified ISO alpha-3 codes;
- convert billions to base currency values;
- classify every observation as actual, estimated or projected;
- compare WDI values or claim definition equivalence;
- acquire or rewrite source snapshots;
- alter source registry or selection policy;
- write to SQLite, create a database application approval, or promote a release.

## Interpretation

Registry code matches are diagnostic matches only. The country identity registry contains records at differing review statuses; the report deliberately labels these as registry matches requiring ISO-status review rather than approved identity mappings.

The WDI comparison remains `not_assessed`: the previous WDI work established live API coverage but did not acquire and normalize a same-vintage WDI snapshot. A later comparison must align country identity, annual period, currency/price basis, indicator definition and vintage before supporting a source-policy decision.

The release-promotion workflow in `tools/validate_source_release.py` is not invoked. IMF WEO must have a source-specific semantic validation report and an explicit approval proposal before any future `latest_validated` promotion.
