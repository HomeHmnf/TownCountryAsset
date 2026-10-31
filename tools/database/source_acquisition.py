"""Acquire immutable WP1.5 source snapshots with tracked provenance manifests.

Raw source bytes are written below raw_data/ and are intentionally not committed.
The corresponding JSON manifest is written below data_manifests/ for version control.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from tools.database.connection import REPOSITORY_ROOT
from tools.sources.registry import load_registry, acquire_one

DEFAULT_CONFIG = REPOSITORY_ROOT / "config" / "data_sources.json"
DEFAULT_RAW_ROOT = REPOSITORY_ROOT / "raw_data" / "sources"
DEFAULT_MANIFEST_ROOT = REPOSITORY_ROOT / "data_manifests" / "sources"
SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")


class SourceAcquisitionError(RuntimeError):
    """Raised when a source snapshot cannot be captured safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_component(value: str, label: str) -> str:
    if not isinstance(value, str) or not SAFE_COMPONENT.fullmatch(value):
        raise SourceAcquisitionError(f"{label} must be a simple filename/path component")
    if value in {".", ".."}:
        raise SourceAcquisitionError(f"Invalid {label}")
    return value


def _load_config(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceAcquisitionError(f"Cannot read source contract {path}: {exc}") from exc
    if not isinstance(payload, dict) or not (
        payload.get("schema_version") == 1 or payload.get("work_package") == "WP1.5"
    ):
        raise SourceAcquisitionError("Unsupported project source registry")
    if not isinstance(payload.get("sources"), dict):
        raise SourceAcquisitionError("Project source registry must define a sources object")
    return payload


def _validate_https_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SourceAcquisitionError("Source URL must be an absolute HTTPS URL")


def acquire_source_snapshot(
    *,
    source_key: str,
    release: str,
    url: str,
    filename: str,
    terms_url: str | None = None,
    attribution: str | None = None,
    license_status: str = "unclear_or_unverified",
    expected_sha256: str | None = None,
    config_path: str | Path = DEFAULT_CONFIG,
    raw_root: str | Path = DEFAULT_RAW_ROOT,
    manifest_root: str | Path = DEFAULT_MANIFEST_ROOT,
    timeout: int = 60,
) -> dict[str, Any]:
    """Download one source file once and write its immutable checksum manifest."""
    source_key = _safe_component(source_key, "source key")
    release = _safe_component(release, "release")
    filename = _safe_component(filename, "filename")
    if timeout < 1 or timeout > 600:
        raise SourceAcquisitionError("timeout must be between 1 and 600 seconds")
    _validate_https_url(url)
    if terms_url:
        _validate_https_url(terms_url)
    if expected_sha256 and (
        len(expected_sha256) != 64
        or any(char not in "0123456789abcdef" for char in expected_sha256)
    ):
        raise SourceAcquisitionError("expected_sha256 must be a lowercase SHA-256 digest")

    config = _load_config(Path(config_path))
    sources = config["sources"]
    if source_key not in sources:
        raise SourceAcquisitionError(f"Unknown source key in project source registry: {source_key}")
    source = sources[source_key]

    if (
        Path(config_path).resolve() == DEFAULT_CONFIG.resolve()
        and Path(raw_root).resolve() == DEFAULT_RAW_ROOT.resolve()
        and Path(manifest_root).resolve() == DEFAULT_MANIFEST_ROOT.resolve()
    ):
        registry = load_registry(DEFAULT_CONFIG)
        matches = [
            item for item in source.get("downloads", [])
            if item.get("release") == release and item.get("url") == url
            and item.get("filename") == filename
        ]
        if len(matches) != 1:
            raise SourceAcquisitionError("No unique matching download in the central source registry")
        try:
            return acquire_one(registry, source_key, matches[0], timeout=timeout, expected_sha256=expected_sha256)
        except Exception as exc:
            raise SourceAcquisitionError(str(exc)) from exc

    raw_dir = Path(raw_root) / source_key / release
    manifest_dir = Path(manifest_root) / source_key
    raw_path = raw_dir / filename
    manifest_path = manifest_dir / f"{release}.json"
    if raw_path.exists() or manifest_path.exists():
        raise SourceAcquisitionError(
            f"Snapshot already exists; refusing to overwrite raw data or manifest: {raw_path}"
        )

    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TownCountryAsset-WP1.5/1.0", "Accept": "*/*"},
    )
    digest = hashlib.sha256()
    byte_count = 0
    content_type: str | None = None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            _validate_https_url(final_url)
            content_type = response.headers.get("Content-Type")
            with raw_path.open("xb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
                    byte_count += len(chunk)
    except (OSError, urllib.error.URLError) as exc:
        raw_path.unlink(missing_ok=True)
        raise SourceAcquisitionError(f"Download failed for {source_key}: {exc}") from exc

    sha256 = digest.hexdigest()
    if byte_count == 0:
        raw_path.unlink(missing_ok=True)
        raise SourceAcquisitionError("Downloaded source file is empty")
    if expected_sha256 and sha256 != expected_sha256:
        raw_path.unlink(missing_ok=True)
        raise SourceAcquisitionError(
            f"SHA-256 mismatch: expected {expected_sha256}, received {sha256}"
        )

    manifest = {
        "manifest_schema_version": 1,
        "work_package": "WP1.5",
        "source_registry": "config/data_sources.json",
        "source_key": source_key,
        "source_name": source.get("name"),
        "release": release,
        "source_url": url,
        "final_url": final_url,
        "terms_url": terms_url,
        "attribution": attribution,
        "license_status": license_status,
        "retrieved_at": _utc_now(),
        "filename": filename,
        "local_raw_path": raw_path.as_posix(),
        "content_type": content_type,
        "byte_count": byte_count,
        "sha256": sha256,
    }
    try:
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    except OSError as exc:
        raw_path.unlink(missing_ok=True)
        raise SourceAcquisitionError(f"Cannot write source manifest {manifest_path}: {exc}") from exc
    return manifest
