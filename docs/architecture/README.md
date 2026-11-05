# Architecture documentation index

- [Canonical database architecture](canonical-database.md) — current SQLite schema, integrity constraints and migration architecture; describes the existing implementation pending the approved separation work.
- [Data-store separation plan](data-store-separation-plan.md) — proposed boundary between the game database and project source/research database, exact two-version retention, migration strategy and acceptance criteria.
- [Country identity contract](country-identity-contract.md) — persistent game identity, source identifiers, names and ISO identity boundaries.
- [ISO assignment review log](iso-assignment-review-log.md) — recorded ISO assignment review evidence and decisions.

Architecture documents define stable contracts and system boundaries. Implementation history belongs in [implementation](../implementation/README.md); provider-specific evidence belongs in [data sources](../data-sources/README.md).

**Status note:** The data-store separation plan is approved for review, not yet implemented. Until its implementation stages are completed and locally validated, the current canonical database documentation describes the running schema.
