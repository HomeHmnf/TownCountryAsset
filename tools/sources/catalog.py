"""Read-only accessors for the central project-wide source registry."""
from __future__ import annotations
from functools import lru_cache
from tools.sources.registry import REGISTRY, canonical_source_id, load_registry

@lru_cache(maxsize=1)
def _sources():
    return load_registry(REGISTRY)["sources"]

def source_record(source_id: str) -> dict:
    registry = load_registry(REGISTRY)
    canonical = canonical_source_id(registry, source_id)
    if canonical is None:
        raise KeyError(f"Unknown project source ID: {source_id}")
    return registry["sources"][canonical]

def source_url(source_id: str, download_id: str | None = None) -> str:
    source = source_record(source_id)
    if download_id is not None:
        for item in source.get("downloads", []):
            if item["id"] == download_id:
                return item["url"]
        raise KeyError(f"Unknown download {download_id!r} for source {source_id!r}")
    url = source.get("homepage_url")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise KeyError(f"Source {source_id!r} has no configured HTTPS homepage URL")
    return url
