# Feature documentation standard

**Applies to:** new features, substantial feature changes, data-source integrations, tooling, schema changes and cross-cutting implementation work.

A feature should have one primary feature document. Put it in the subject area that owns the work (usually docs/roadmap/ for planned feature work); link supporting architecture, implementation and source documents rather than duplicating them.

## Required document structure

1. **Status and ownership** — current state, target branch/work package and last meaningful update.
2. **Problem and motivation** — observable problem, user/system impact and evidence.
3. **Goals and non-goals** — measurable outcomes and explicit exclusions.
4. **Scope and dependencies** — affected modules, data domains, consumers, configuration, external providers and prerequisites.
5. **Design and decisions** — contracts, data flow, identity rules, schemas, failure semantics, alternatives and authoritative architecture links.
6. **Implementation plan** — numbered work units; each names code/configuration/docs affected and expected outcome.
7. **Data, provenance and compatibility** — source versions, units, identity mapping, licensing, migrations, compatibility and data preservation where applicable.
8. **Safety and operational boundaries** — read/write effects, approval gates, rollback, immutability, secrets and out-of-scope systems.
9. **Validation and acceptance criteria** — exact commands, expected checks, evidence artifacts and distinction between implemented, automated-tested and owner-validated.
10. **Documentation and related records** — links to the relevant area index, architecture contract, implementation log, source assessment, decisions and reports.
11. **Open questions and next steps** — unresolved evidence, decision owner and next bounded action.

## Required status language

- **Planned:** design or implementation has not started.
- **Implemented:** code/documentation exists; this alone is not validation.
- **Automated tests passed:** report the exact suite and result, and identify who ran it.
- **Locally validated:** only after the repository owner supplies local command output.
- **Reviewed/approved:** identify the decision and evidence; test success is not approval.
- **Applied/promoted:** identify the exact approval, release or application record.

A GitHub commit, code inspection or assistant-side review is not owner-side local validation.

## Documentation update rule

Every implementation step that changes behavior, interfaces, configuration, data contracts, validation or operational procedures must update the relevant feature document and implementation/architecture/source document in the same step. Update the area index when adding or moving a document. If no documentation change is needed, state why in the implementation record.

## Writing and maintenance rules

- One document, one primary responsibility; split long documents when acquisition, methodology, implementation or decisions need independent lifecycles.
- Keep decisions and contracts in one authoritative location. Other documents link to them.
- Prefer relative Markdown links within the repository.
- Record exact paths, commands, identifiers, hashes, versions and dates where reproducibility depends on them.
- Distinguish source facts, measured results, interpretations and unresolved hypotheses.
- Do not record secrets, personal local paths or unverified assumptions.
- Preserve historical validation records, but clearly mark superseded instructions and stale reports.
- Keep indexes concise and complete; they are navigation layers, not duplicate documents.

## Feature document template

Copy [feature-template.md](feature-template.md) and replace every prompt. Remove instructional notes only after the section has been addressed.
