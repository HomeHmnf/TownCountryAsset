# Source data policy

- Keep the downloaded Natural Earth archive unchanged in local source storage; do not commit large archives by default.
- Record source URL, retrieval date, layer/scale, version, SHA-256, attribution and license.
- Preserve all source attributes. Normalized fields supplement, not replace, source fields.
- Never infer or synthesize ISO identifiers. `feature-NNNN` is an internal fallback only.
- Geometry profiles are derived using topology-preserving simplification; never overwrite source geometry.
- Test multipart polygons, islands, interior rings/holes, aliases, deterministic outputs and rendering validity before release.
- Natural Earth data is public domain; keep attribution and provenance for reproducibility.
