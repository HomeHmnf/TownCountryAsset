# Source data policy

- Keep the downloaded Natural Earth archive unchanged in local source storage; do not commit large archives by default.
- Record source URL, retrieval date, layer/scale, actual release version, archive SHA-256, attribution and license. Never guess a release or retrieval date; complete the build config before publishing.
- Preserve all source attributes. Normalized fields supplement, not replace, source fields.
- Never infer or synthesize ISO identifiers. `feature-NNNN` is an internal fallback only.
- Reject unsafe ZIP paths and symbolic links; fail when an input directory contains multiple shapefiles rather than selecting one arbitrarily.
- Geometry profiles are derived using topology-preserving simplification; never overwrite source geometry. Validate each derived geometry.
- The generated manifest records payload SHA-256 hashes and sizes and omits build timestamps to keep outputs deterministic.
- Test multipart polygons, islands, interior rings/holes, aliases, deterministic outputs, archive safety and rendering validity before release.
- Natural Earth data is public domain; keep attribution and provenance for reproducible builds.
