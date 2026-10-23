#!/usr/bin/env python3
"""Generate game_id-keyed SVG flags from reviewed mappings and cached source."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "TCA_FLAG_SOURCE_DIR": "raw_data/flags",
    "TCA_FLAG_ASSET_OUTPUT_DIR": "generated/town_country_asset_candidate/flags",
    "TCA_FLAG_MAPPING": "config/country_flag_mapping.json",
    "TCA_FLAG_REPORT": "reports/flag-asset-review.md",
}
CODE_RE = re.compile(r"^[a-z]{2}$")


def load_config(env_file: Path, environ: dict[str, str] | None = None) -> dict[str, str]:
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


def resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_latest_source(source_dir: Path) -> tuple[Path, dict[str, Any]]:
    latest_path = source_dir / "latest.json"
    if not latest_path.is_file():
        raise ValueError(f"missing {latest_path}; run tools/refresh_flag_source.py first")
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    archive_name, provenance_name = latest.get("archive_file"), latest.get("provenance_file")
    if not isinstance(archive_name, str) or Path(archive_name).name != archive_name:
        raise ValueError("latest.json has an invalid archive_file")
    if not isinstance(provenance_name, str) or Path(provenance_name).name != provenance_name:
        raise ValueError("latest.json has an invalid provenance_file")
    archive_path, provenance_path = source_dir / archive_name, source_dir / provenance_name
    if not archive_path.is_file() or not provenance_path.is_file():
        raise ValueError("cached source archive or provenance file is missing")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    payload = archive_path.read_bytes()
    if sha256_bytes(payload) != provenance.get("archive_sha256"):
        raise ValueError("cached archive SHA-256 does not match provenance")
    if latest.get("resolved_commit") != provenance.get("resolved_commit"):
        raise ValueError("latest.json commit does not match provenance")
    if provenance.get("license") != "MIT":
        raise ValueError("source provenance does not identify the expected MIT license")
    return archive_path, provenance


def load_source_svgs(archive_path: Path) -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    try:
        archive = zipfile.ZipFile(archive_path)
    except zipfile.BadZipFile as exc:
        raise ValueError("cached source is not a valid ZIP archive") from exc
    with archive:
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            mode = (info.external_attr >> 16) & 0xFFFF
            if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
                raise ValueError(f"unsafe path in archive: {info.filename}")
            if mode and (mode & 0o170000) == 0o120000:
                raise ValueError(f"symbolic link in archive: {info.filename}")
            if len(path.parts) < 3 or path.parts[-3:-1] != ("flags", "4x3") or path.suffix.lower() != ".svg":
                continue
            code = path.stem
            if not CODE_RE.fullmatch(code):
                continue
            if code in found:
                raise ValueError(f"duplicate source SVG for code {code!r}")
            found[code] = archive.read(info)
    if not found:
        raise ValueError("archive has no SVG files under flags/4x3/")
    return found


def validate_svg(payload: bytes, description: str) -> None:
    if not payload.strip():
        raise ValueError(f"{description}: SVG is empty")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ValueError(f"{description}: malformed SVG XML: {exc}") from exc
    if root.tag.split("}")[-1].lower() != "svg":
        raise ValueError(f"{description}: XML root is not svg")


def audit_and_generate(
    registry: dict[str, Any], mapping: dict[str, Any],
    source_svgs: dict[str, bytes], provenance: dict[str, Any],
) -> dict[str, Any]:
    registry_records, mapping_records = registry.get("records"), mapping.get("records")
    if not isinstance(registry_records, list):
        raise ValueError("identity registry records must be an array")
    if not isinstance(mapping_records, list):
        raise ValueError("flag mapping records must be an array")
    issues: list[str] = []
    registry_ids: list[str] = []
    for index, record in enumerate(registry_records):
        if not isinstance(record, dict) or not isinstance(record.get("game_id"), str) or not record["game_id"].strip():
            issues.append(f"registry record {index}: missing or invalid game_id")
        else:
            registry_ids.append(record["game_id"])
    if len(registry_ids) != len(set(registry_ids)):
        issues.append("identity registry contains duplicate game_id values")
    registry_set = set(registry_ids)
    mappings: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(mapping_records):
        if not isinstance(record, dict):
            issues.append(f"mapping record {index}: not an object")
            continue
        game_id = record.get("game_id")
        if not isinstance(game_id, str) or not game_id.strip():
            issues.append(f"mapping record {index}: missing or invalid game_id")
            continue
        if game_id in mappings:
            issues.append(f"duplicate mapping for game_id {game_id}")
            continue
        mappings[game_id] = record
        if game_id not in registry_set:
            issues.append(f"mapping references unknown game_id {game_id}")
    for game_id in sorted(registry_set - set(mappings)):
        issues.append(f"missing flag mapping for game_id {game_id}")

    code_owners: dict[str, str] = {}
    generated: dict[str, bytes] = {}
    file_metadata: list[dict[str, Any]] = []
    for game_id in sorted(registry_set & set(mappings)):
        record = mappings[game_id]
        code, status = record.get("source_flag_code"), record.get("status")
        if status != "reviewed":
            issues.append(f"{game_id}: mapping status is {status!r}; expected 'reviewed'")
            continue
        if not isinstance(code, str) or not CODE_RE.fullmatch(code):
            issues.append(f"{game_id}: source_flag_code must be a lowercase two-letter code")
            continue
        if code in code_owners:
            issues.append(f"source flag code {code!r} maps to both {code_owners[code]} and {game_id}")
            continue
        code_owners[code] = game_id
        payload = source_svgs.get(code)
        if payload is None:
            issues.append(f"{game_id}: source SVG for code {code!r} is missing")
            continue
        try:
            validate_svg(payload, f"{game_id} ({code})")
        except ValueError as exc:
            issues.append(str(exc))
            continue
        filename = f"{game_id}.svg"
        generated[filename] = payload
        file_metadata.append({
            "game_id": game_id, "source_flag_code": code, "file": filename,
            "sha256": sha256_bytes(payload), "size_bytes": len(payload),
        })
    source = {
        "source_url": provenance.get("source_url"),
        "configured_ref": provenance.get("configured_ref"),
        "resolved_commit": provenance.get("resolved_commit"),
        "retrieved_at_utc": provenance.get("retrieved_at_utc"),
        "archive_sha256": provenance.get("archive_sha256"),
        "license": provenance.get("license"),
        "license_sha256": provenance.get("license_sha256"),
        "archive_file": provenance.get("archive_file"),
    }
    return {
        "ok": not issues and len(generated) == len(registry_ids),
        "issues": issues, "registry_count": len(registry_ids),
        "mapping_count": len(mapping_records), "generated_count": len(generated),
        "generated": generated, "files": file_metadata, "source": source,
    }


def write_report(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Flag asset coverage audit", "",
        f"- **Status:** {'PASS' if result['ok'] else 'FAIL'}",
        f"- Registry IDs: {result['registry_count']}",
        f"- Mapping records: {result['mapping_count']}",
        f"- Valid generated flags: {result['generated_count']}",
        f"- Source repository: {result['source'].get('source_url')}",
        f"- Configured ref: {result['source'].get('configured_ref')}",
        f"- Resolved commit: {result['source'].get('resolved_commit')}",
        f"- Retrieved (UTC): {result['source'].get('retrieved_at_utc')}",
        f"- Archive SHA-256: {result['source'].get('archive_sha256')}",
        f"- License: {result['source'].get('license')}",
        f"- License SHA-256: {result['source'].get('license_sha256')}",
        "", "## Issues", "",
    ]
    lines.extend([f"- {issue}" for issue in result["issues"]] if result["issues"] else ["- None"])
    lines += ["", "## Generated file hashes", "", "| game_id | source code | file | SHA-256 | bytes |", "|---|---|---|---|---:|"]
    lines.extend(
        f"| {item['game_id']} | {item['source_flag_code']} | {item['file']} | {item['sha256']} | {item['size_bytes']} |"
        for item in result["files"]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def publish_flags(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.staging-", dir=output_dir.parent))
    backup = output_dir.with_name(f".{output_dir.name}.backup")
    try:
        for filename, payload in result["generated"].items():
            (staging / filename).write_bytes(payload)
        manifest = {"schema_version": 1, "source": result["source"], "flags": result["files"]}
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if backup.exists():
            shutil.rmtree(backup) if backup.is_dir() else backup.unlink()
        if output_dir.exists():
            output_dir.rename(backup)
        try:
            staging.rename(output_dir)
        except OSError:
            if backup.exists() and not output_dir.exists():
                backup.rename(output_dir)
            raise
        if backup.exists():
            shutil.rmtree(backup) if backup.is_dir() else backup.unlink()
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--mapping", type=Path)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        config = load_config(args.env_file)
        registry_path = args.registry or resolve_path(config.get("TCA_IDENTITY_REGISTRY", "config/country_identity_registry.json"))
        mapping_path = args.mapping or resolve_path(config["TCA_FLAG_MAPPING"])
        source_dir = args.source_dir or resolve_path(config["TCA_FLAG_SOURCE_DIR"])
        output_dir = args.output_dir or resolve_path(config["TCA_FLAG_ASSET_OUTPUT_DIR"])
        report_path = args.report or resolve_path(config["TCA_FLAG_REPORT"])
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        archive_path, provenance = load_latest_source(source_dir)
        source_svgs = load_source_svgs(archive_path)
        result = audit_and_generate(registry, mapping, source_svgs, provenance)
        write_report(report_path, result)
        if not result["ok"]:
            print(f"Flag audit failed: {len(result['issues'])} issue(s); see {report_path}", file=sys.stderr)
            return 1
        publish_flags(output_dir, result)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"Flag generation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Flag generation succeeded: {result['generated_count']} flags")
    print(f"Output: {output_dir}")
    print(f"Audit report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
