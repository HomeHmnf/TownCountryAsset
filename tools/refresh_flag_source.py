#!/usr/bin/env python3
"""Refresh the configured flag-icons source archive with immutable provenance.

The command caches an archive only; it does not assign flags, generate game
assets, or modify the identity registry or approved/game repositories.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "TCA_FLAG_SOURCE_URL": "https://github.com/lipis/flag-icons",
    "TCA_FLAG_SOURCE_REF": "main",
    "TCA_FLAG_SOURCE_DIR": "raw_data/flags",
    "TCA_HTTP_TIMEOUT_SECONDS": "60",
}


def load_config(env_file: Path, environ: dict[str, str] | None = None) -> dict[str, str]:
    """Read simple .env settings; process environment has precedence."""
    result = dict(os.environ if environ is None else environ)
    if env_file.exists():
        for number, line in enumerate(env_file.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(f"{env_file}:{number}: expected KEY=VALUE")
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
                raise ValueError(f"{env_file}:{number}: invalid environment variable name")
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            result.setdefault(key, value)
    for key, value in DEFAULTS.items():
        result.setdefault(key, value)
    return result


def repository_parts(source_url: str) -> tuple[str, str]:
    """Accept a GitHub repository URL only; do not fetch arbitrary hosts."""
    parsed = urllib.parse.urlparse(source_url)
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        raise ValueError("flag source URL must be an HTTPS github.com repository URL")
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) != 2:
        raise ValueError("flag source URL must identify exactly one owner/repository")
    owner, repository = parts
    repository = repository.removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", repository):
        raise ValueError("flag source URL contains an invalid owner or repository")
    return owner, repository


def request_bytes(url: str, timeout: int, *, accept: str = "application/vnd.github+json") -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TownCountryAsset-flag-refresh/1.0", "Accept": accept},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
    if not data:
        raise ValueError(f"empty response from {url}")
    return data


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_archive(archive_bytes: bytes) -> dict[str, Any]:
    """Reject unsafe archives and require SVG flags plus an MIT license file."""
    try:
        archive = zipfile.ZipFile(BytesIO(archive_bytes))
    except zipfile.BadZipFile as exc:
        raise ValueError("downloaded flag source is not a valid ZIP archive") from exc
    with archive:
        names = archive.namelist()
        if not names:
            raise ValueError("flag source archive is empty")
        svg_count = 0
        license_name = None
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            mode = (info.external_attr >> 16) & 0xFFFF
            if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
                raise ValueError(f"unsafe path in source archive: {info.filename}")
            if mode and (mode & 0o170000) == 0o120000:
                raise ValueError(f"symbolic links are not allowed in source archive: {info.filename}")
            lower_parts = [part.lower() for part in path.parts]
            if path.name.lower() in {"license", "license.txt", "license.md"}:
                license_name = info.filename
            if path.suffix.lower() == ".svg" and "flags" in lower_parts:
                svg_count += 1
        if svg_count == 0:
            raise ValueError("source archive contains no SVG files under a flags directory")
        if license_name is None:
            raise ValueError("source archive does not contain a license file")
        license_text = archive.read(license_name).decode("utf-8", errors="replace")
        if "mit license" not in license_text.lower() and "permission is hereby granted" not in license_text.lower():
            raise ValueError("source license file does not appear to contain MIT license terms")
        return {
            "svg_file_count": svg_count,
            "license_archive_path": license_name,
            "license_text": license_text,
            "license_sha256": sha256_bytes(license_text.encode("utf-8")),
        }


def refresh(source_url: str, source_ref: str, output_dir: Path, timeout: int) -> dict[str, Any]:
    owner, repository = repository_parts(source_url)
    encoded_ref = urllib.parse.quote(source_ref, safe="")
    api_url = f"https://api.github.com/repos/{owner}/{repository}/commits/{encoded_ref}"
    commit_payload = json.loads(request_bytes(api_url, timeout).decode("utf-8"))
    commit_sha = commit_payload.get("sha")
    if not isinstance(commit_sha, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", commit_sha):
        raise ValueError("GitHub commit lookup did not return a full 40-character commit SHA")
    commit_sha = commit_sha.lower()
    archive_url = f"https://codeload.github.com/{owner}/{repository}/zip/{commit_sha}"
    archive_bytes = request_bytes(archive_url, timeout, accept="application/zip")
    archive_info = validate_archive(archive_bytes)

    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"flag-icons-{commit_sha[:12]}"
    archive_name = f"{stem}.zip"
    license_name = f"{stem}-LICENSE.txt"
    provenance_name = f"{stem}-provenance.json"
    archive_path = output_dir / archive_name
    license_path = output_dir / license_name
    provenance_path = output_dir / provenance_name

    provenance = {
        "source_url": source_url,
        "configured_ref": source_ref,
        "resolved_commit": commit_sha,
        "archive_url": archive_url,
        "retrieved_at_utc": retrieved_at,
        "archive_file": archive_name,
        "archive_sha256": sha256_bytes(archive_bytes),
        "archive_size_bytes": len(archive_bytes),
        "license": "MIT",
        "license_archive_path": archive_info["license_archive_path"],
        "license_file": license_name,
        "license_sha256": archive_info["license_sha256"],
        "svg_file_count": archive_info["svg_file_count"],
    }
    # Atomic writes prevent a partial archive or provenance file being treated as valid.
    for final_path, payload in (
        (archive_path, archive_bytes),
        (license_path, archive_info["license_text"].encode("utf-8")),
        (provenance_path, (json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode("utf-8")),
    ):
        fd, temp_name = tempfile.mkstemp(prefix=f".{final_path.name}.", dir=output_dir)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, final_path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
    latest = {
        "provenance_file": provenance_name,
        "archive_file": archive_name,
        "resolved_commit": commit_sha,
    }
    (output_dir / "latest.json").write_text(json.dumps(latest, indent=2) + "\n", encoding="utf-8")
    return provenance


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env", help="configuration file (default: .env)")
    parser.add_argument("--source-url", help="override TCA_FLAG_SOURCE_URL")
    parser.add_argument("--source-ref", help="override TCA_FLAG_SOURCE_REF")
    parser.add_argument("--output-dir", type=Path, help="override TCA_FLAG_SOURCE_DIR")
    parser.add_argument("--timeout", type=int, help="override TCA_HTTP_TIMEOUT_SECONDS")
    args = parser.parse_args()
    try:
        config = load_config(args.env_file)
        source_url = args.source_url or config["TCA_FLAG_SOURCE_URL"]
        source_ref = args.source_ref or config["TCA_FLAG_SOURCE_REF"]
        output_dir = args.output_dir or Path(config["TCA_FLAG_SOURCE_DIR"])
        if not output_dir.is_absolute():
            output_dir = ROOT / output_dir
        timeout = args.timeout or int(config["TCA_HTTP_TIMEOUT_SECONDS"])
        if timeout <= 0:
            raise ValueError("HTTP timeout must be a positive integer")
        provenance = refresh(source_url, source_ref, output_dir, timeout)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, urllib.error.URLError, TimeoutError) as exc:
        print(f"Flag source refresh failed: {exc}", file=__import__("sys").stderr)
        return 1
    print(f"Flag source refresh succeeded: commit {provenance['resolved_commit']}")
    print(f"Archive: {provenance['archive_file']} ({provenance['archive_size_bytes']} bytes)")
    print(f"SHA-256: {provenance['archive_sha256']}")
    print(f"SVG files: {provenance['svg_file_count']}; license: {provenance['license']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
