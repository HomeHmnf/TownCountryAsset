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
    "TCA_FLAG_MANUAL_DIR": "raw_data/flags/manual",
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
    manual_svgs: dict[str, bytes] | None = None,
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

    manual_svgs = manual_svgs or {}
    code_owners: dict[str, str] = {}
    generated: dict[str, bytes] = {}
    file_metadata: list[dict[str, Any]] = []
    for game_id in sorted(registry_set & set(mappings)):
        record = mappings[game_id]
        code, manual_path, status = record.get("source_flag_code"), record.get("manual_svg_path"), record.get("status")
        if status != "reviewed":
            issues.append(f"{game_id}: mapping status is {status!r}; expected 'reviewed'")
            continue
        if isinstance(code, str) and CODE_RE.fullmatch(code):
            if manual_path:
                issues.append(f"{game_id}: choose either source_flag_code or manual_svg_path, not both")
                continue
            if code in code_owners:
                issues.append(f"source flag code {code!r} maps to both {code_owners[code]} and {game_id}")
                continue
            code_owners[code] = game_id
            payload = source_svgs.get(code)
            if payload is None:
                issues.append(f"{game_id}: source SVG for code {code!r} is missing")
                continue
            source_kind = "repository"
            source_identifier = code
        elif isinstance(manual_path, str) and manual_path.strip():
            if code is not None:
                issues.append(f"{game_id}: choose either source_flag_code or manual_svg_path, not both")
                continue
            safe_path = PurePosixPath(manual_path)
            if safe_path.is_absolute() or ".." in safe_path.parts or "\\" in manual_path or safe_path.suffix.lower() != ".svg":
                issues.append(f"{game_id}: manual_svg_path must be a safe relative .svg path under the configured manual directory")
                continue
            payload = manual_svgs.get(safe_path.as_posix())
            if payload is None:
                issues.append(f"{game_id}: manual SVG {manual_path!r} is missing or unreadable")
                continue
            source_kind = "manual"
            source_identifier = manual_path
        else:
            if code is not None and not (isinstance(code, str) and CODE_RE.fullmatch(code)):
                issues.append(f"{game_id}: source_flag_code must be a lowercase two-letter code")
            else:
                issues.append(f"{game_id}: provide a valid source_flag_code or manual_svg_path")
            continue
        try:
            validate_svg(payload, f"{game_id} ({source_identifier})")
        except ValueError as exc:
            issues.append(str(exc))
            continue
        filename = f"{game_id}.svg"
        generated[filename] = sized_flag_svg(payload)
        file_metadata.append({
            "game_id": game_id, "source_flag_code": code if source_kind == "repository" else None,
            "source_kind": source_kind, "source_identifier": source_identifier,
            "file": filename, "sha256": sha256_bytes(generated[filename]), "size_bytes": len(generated[filename]),
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


FLAG_SVG_WIDTH = 512
FLAG_SVG_HEIGHT = 384
FLAG_PROFILES = ("low", "medium", "high")


def sized_flag_svg(payload: bytes) -> bytes:
    """Set an explicit 512x384 SVG viewport while preserving the source viewBox."""
    validate_svg(payload, "flag source")
    root = ET.fromstring(payload)
    root.set("width", str(FLAG_SVG_WIDTH))
    root.set("height", str(FLAG_SVG_HEIGHT))
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_source_previews(output_dir: Path, source_svgs: dict[str, bytes]) -> None:
    """Write unassigned source previews; these never imply a game_id mapping."""
    for profile in FLAG_PROFILES:
        profile_dir = output_dir / "source" / profile
        profile_dir.mkdir(parents=True, exist_ok=True)
        for code, payload in sorted(source_svgs.items()):
            if not CODE_RE.fullmatch(code):
                raise ValueError(f"invalid source flag code {code!r}")
            (profile_dir / f"{code}.svg").write_bytes(sized_flag_svg(payload))
    manifest = {
        "schema_version": 1,
        "purpose": "Unassigned source previews for human review; not game_id mappings or approvals.",
        "width": FLAG_SVG_WIDTH,
        "height": FLAG_SVG_HEIGHT,
        "profiles": list(FLAG_PROFILES),
        "source_codes": sorted(source_svgs),
    }
    (output_dir / "source" / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


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
        f"| {item['game_id']} | {item['source_identifier']} | {item['file']} | {item['sha256']} | {item['size_bytes']} |"
        for item in result["files"]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def publish_flags(
    output_dir: Path, result: dict[str, Any], source_svgs: dict[str, bytes] | None = None,
) -> None:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.staging-", dir=output_dir.parent))
    backup = output_dir.with_name(f".{output_dir.name}.backup")
    try:
        for filename, payload in result["generated"].items():
            # Keep the original game_id-keyed file for existing consumers.
            (staging / filename).write_bytes(payload)
            # Also publish profile-compatible, explicitly sized vector files.
            for profile in FLAG_PROFILES:
                profile_dir = staging / profile
                profile_dir.mkdir(parents=True, exist_ok=True)
                (profile_dir / filename).write_bytes(sized_flag_svg(payload))
        if source_svgs is not None:
            write_source_previews(staging, source_svgs)
        manifest = {
            "schema_version": 1, "source": result["source"], "flags": result["files"],
            "profiles": list(FLAG_PROFILES), "width": FLAG_SVG_WIDTH, "height": FLAG_SVG_HEIGHT,
        }
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
        manual_dir = resolve_path(config.get("TCA_FLAG_MANUAL_DIR", "raw_data/flags/manual"))
        manual_svgs: dict[str, bytes] = {}
        if manual_dir.exists():
            for path in manual_dir.rglob("*.svg"):
                if path.is_symlink():
                    raise ValueError(f"manual flag directory must not contain symlinks: {path}")
                relative = path.relative_to(manual_dir).as_posix()
                if ".." in PurePosixPath(relative).parts:
                    raise ValueError(f"unsafe manual SVG path: {relative}")
                manual_svgs[relative] = path.read_bytes()
        result = audit_and_generate(registry, mapping, source_svgs, provenance, manual_svgs)
        write_report(report_path, result)
        if not result["ok"]:
            # Source-code previews remain available for visual review even while
            # game_id mappings are unreviewed. They are stored separately and
            # never count as generated/approved country flags.
            write_source_previews(output_dir, source_svgs)
            print(f"Flag audit failed: {len(result['issues'])} issue(s); see {report_path}", file=sys.stderr)
            print(f"Unassigned source previews: {output_dir / 'source'}", file=sys.stderr)
            return 1
        publish_flags(output_dir, result, source_svgs)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"Flag generation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Flag generation succeeded: {result['generated_count']} flags")
    print(f"Output: {output_dir}")
    print(f"Audit report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
