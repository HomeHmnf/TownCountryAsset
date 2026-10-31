"""Project-wide source registry, immutable acquisition, and snapshot validation."""
from __future__ import annotations
import hashlib, json, re, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "config" / "data_sources.json"
SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")

class SourceError(RuntimeError):
    """Source registry or acquisition failure."""

def load_registry(path: Path = REGISTRY):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceError(f"Cannot load source registry {path}: {exc}") from exc
    if data.get("schema_version") != 1 or not isinstance(data.get("sources"), dict):
        raise SourceError("Invalid project source registry schema")
    for sid, source in data["sources"].items():
        if not SAFE.fullmatch(sid) or not isinstance(source, dict) or not isinstance(source.get("downloads", []), list):
            raise SourceError(f"Invalid source record: {sid}")
        seen = set()
        for item in source.get("downloads", []):
            did, release, filename, url = item.get("id"), item.get("release"), item.get("filename"), item.get("url")
            if not all(isinstance(v, str) and SAFE.fullmatch(v) for v in (did, release, filename)) or did in seen:
                raise SourceError(f"Invalid download definition for {sid}")
            seen.add(did)
            parsed = urlparse(url or "")
            if parsed.scheme != "https" or not parsed.netloc:
                raise SourceError(f"Download URL must be HTTPS: {sid}/{did}")
    data["_root"] = ROOT if path.resolve() == REGISTRY.resolve() else path.resolve().parent
    return data

def _paths(registry, sid, item):
    root = registry.get("_root", ROOT)
    raw = root / registry["storage"]["raw_root"] / sid / item["id"] / item["release"] / item["filename"]
    manifest = root / registry["storage"]["manifest_root"] / sid / item["id"] / f"{item['release']}.json"
    return raw, manifest

def inspect_snapshots(registry):
    rows = []
    root = registry.get("_root", ROOT)
    for sid, source in registry["sources"].items():
        for item in source.get("downloads", []):
            raw, manifest = _paths(registry, sid, item)
            status, detail = "missing", "raw snapshot or manifest missing"
            if raw.is_file() and manifest.is_file():
                try:
                    meta = json.loads(manifest.read_text(encoding="utf-8"))
                    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
                    if meta.get("sha256") != digest or meta.get("byte_count") != raw.stat().st_size:
                        status, detail = "invalid", "checksum or byte count mismatch"
                    elif meta.get("source_id") != sid or meta.get("download_id") != item["id"]:
                        status, detail = "invalid", "manifest source/download identity mismatch"
                    else:
                        status, detail = "valid", f"{raw.stat().st_size} bytes; sha256 verified"
                except (OSError, json.JSONDecodeError) as exc:
                    status, detail = "invalid", str(exc)
            rows.append({"source_id": sid, "download_id": item["id"], "release": item["release"],
                         "status": status, "detail": detail, "raw_path": str(raw.relative_to(root))})
    return rows

def acquire_one(registry, sid, item, timeout=60, expected_sha256=None):
    source = registry["sources"][sid]
    raw, manifest = _paths(registry, sid, item)
    if raw.exists() or manifest.exists():
        raise SourceError(f"Snapshot already exists; refusing overwrite: {raw}")
    raw.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(item["url"], headers={"User-Agent": "TownCountryAsset-SourceManager/1.0", "Accept": "*/*"})
    digest, size = hashlib.sha256(), 0
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            parsed = urlparse(final_url)
            if parsed.scheme != "https" or not parsed.netloc:
                raise SourceError("Redirect target must remain HTTPS")
            content_type = response.headers.get("Content-Type")
            with raw.open("xb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
    except Exception as exc:
        raw.unlink(missing_ok=True)
        if isinstance(exc, SourceError):
            raise
        raise SourceError(f"Download failed for {sid}/{item['id']}: {exc}") from exc
    if not size:
        raw.unlink(missing_ok=True)
        raise SourceError("Downloaded file is empty")
    if expected_sha256 and digest.hexdigest() != expected_sha256:
        raw.unlink(missing_ok=True)
        raise SourceError("SHA-256 mismatch: expected {}, received {}".format(expected_sha256, digest.hexdigest()))
    meta = {"manifest_schema_version": 1, "source_id": sid, "source_name": source["name"],
            "download_id": item["id"], "release": item["release"], "source_url": item["url"],
            "final_url": final_url, "terms_url": source.get("terms_url"),
            "attribution": source.get("attribution"),
            "license_status": source.get("license_status", "unclear_or_unverified"),
            "retrieved_at": datetime.now(timezone.utc).isoformat(), "filename": item["filename"],
            "local_raw_path": raw.relative_to(registry.get("_root", ROOT)).as_posix(),
            "content_type": content_type, "byte_count": size, "sha256": digest.hexdigest(),
            "format": item.get("format"), "fields": item.get("fields", [])}
    try:
        manifest.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raw.unlink(missing_ok=True)
        raise SourceError(f"Cannot write manifest: {exc}") from exc
    return meta

def check_online(registry, timeout=15):
    results = []
    for sid, source in registry["sources"].items():
        for item in source.get("downloads", []):
            request = urllib.request.Request(item["url"], method="HEAD",
                headers={"User-Agent": "TownCountryAsset-SourceManager/1.0"})
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    results.append({"source_id": sid, "download_id": item["id"],
                                    "status": "reachable", "http_status": getattr(response, "status", None)})
            except Exception as exc:
                results.append({"source_id": sid, "download_id": item["id"],
                                "status": "unreachable", "detail": str(exc)})
    return results
