# Temporary IMF WEO semantic-review workspace

This directory is an evidence-staging area, not a canonical data location. Copy generated reports here when preparing the next review bundle. Do not place raw provider downloads, SQLite databases, credentials or private keys here. Keep original source snapshots in their registered `raw_data/sources/` locations.

## Populate from the current owner-run reports

Run this from the repository root in Fish:

```fish
set workspace reports/workspaces/imf-weo-semantic-review
mkdir -p $workspace
cp -a reports/sources/imf-weo/20261105T101443Z $workspace/
cp -a reports/sources/imf-wdi-comparison/20261105T103220Z $workspace/
cp -a reports/sources/imf-wdi-discrepancy-investigation/20261105T104531Z $workspace/
```

This copies the existing report outputs without modifying their originals. Re-running the command replaces no files; if a destination already exists, `cp` may create a nested timestamp directory. For a clean refresh, choose a new workspace name (for example, append a UTC timestamp) before copying.

## Add subsequent source-level review outputs

Write each new assessment to its own timestamped subdirectory under `reports/sources/` first. Then copy that complete directory into this workspace. Preserve the report's JSON, Markdown and CSV together. Include a short README with:
- exact command and arguments;
- retrieval timestamp and source endpoint/release;
- whether source data were fetched or only existing reports were analyzed;
- SHA-256 and byte count for acquired response artifacts;
- whether any database, registry, policy or approval state changed.

Do not describe live WDI API data as an immutable vintage. Do not overwrite the original comparison run. Keep Bahrain's documented disposition closed unless genuinely new primary evidence is presented.

## Stage and push only the review bundle

After copying the reports, inspect the staged file list and size. Then explicitly stage only this workspace:

```fish
git status --short
git add reports/workspaces/imf-weo-semantic-review
git diff --cached --stat
git commit -m "Add IMF WEO semantic review evidence bundle"
git push origin work/compiler-hardening
```

Do not use `git add .`. Do not include canonical databases or unrelated local changes.
