# Documentation index

This directory is the documentation home for TownCountryAsset. Start with the [project context guide](PROJECT_CONTEXT.md), then use the subject index for the relevant topic.

## Subject indexes

| Area | Index | Responsibility |
|---|---|---|
| Architecture | [Architecture](architecture/README.md) | Stable identities, data-store boundaries, database design and contracts |
| Data sources | [Data sources](data-sources/README.md) | Providers, acquisition, validation, source selection and comparability |
| Implementation | [Implementation](implementation/README.md) | Engineering implementation records, operational workflows and owner validation history |
| Review | [Review](review/README.md) | Focused audits, investigations and review decisions |
| Roadmap | [Roadmap](roadmap/README.md) | Feature plans, work packages, sequencing and acceptance criteria |

## Cross-cutting references

- [Feature documentation standard](feature-documentation-standard.md)
- [CLI tool reference](cli-tool.md)
- [Configuration reference](configuration-reference.md)
- [Source policy](source-policy.md)

## Documentation rules

1. Each subject area maintains one README index linking to its documents.
2. The root index links to subject-area indexes; it does not duplicate their inventories.
3. Each document has one primary responsibility. Split acquisition, dataset structure, methodology, implementation and review findings when they need independent lifecycles.
4. Link related documents rather than copying content. Keep one authoritative home for each decision or fact.
5. New feature documents follow the feature documentation standard.
6. Update the relevant index whenever a document is added, renamed, split or retired.
7. Update documentation in the same implementation step as code, tests, configuration or operational changes.
8. Keep [the project context guide](PROJECT_CONTEXT.md) concise and update it when architecture, workflow or project status changes; link to detailed documents instead of duplicating them.
