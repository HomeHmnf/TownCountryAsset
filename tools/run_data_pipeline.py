#!/usr/bin/env python3
"""Fetch configured sources and prepare candidate country assets for the game.

This tool operates only in TownCountryAsset. It never writes to the game repo,
never approves ISO assignments, and never promotes candidate output to approved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import shutil
import tempfile
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "TCA_NATURAL_EARTH_URL": "https://naturalearth.s3.amazonaws.com/50m_cultural/ne_50m_admin_0_countries.zip",
    "TCA_ISO_REFERENCE_URL": "https://raw.githubusercontent.com/stefangabos/world_countries/master/data/countries/en/world.csv",
    "TCA_PERSIAN_LABEL_SOURCE_URL": "https://query.wikidata.org/sparql",
    "TCA_FLAG_SOURCE_URL": "https://github.com/lipis/flag-icons",
    "TCA_FLAG_SOURCE_REF": "main",
    "TCA_FLAG_SOURCE_DIR": "raw_data/flags",
    "TCA_FLAG_ASSET_OUTPUT_DIR": "generated/town_country_asset_candidate/flags",
    "TCA_FLAG_MAPPING": "config/country_flag_mapping.json",
    "TCA_FLAG_REPORT": "reports/flag-asset-review.md",
    "TCA_FLAG_REFRESH_ENABLED": "true",
    "TCA_FETCHED_DATA_DIR": "raw_data/fetched",
    "TCA_ISO_DATA_DIR": "raw_data/iso",
    "TCA_PERSIAN_DATA_DIR": "raw_data/persian",
    "TCA_PERSIAN_LOCALIZATION_REPORT": "reports/persian-localization-proposals.md",
    "TCA_GAME_DATA_OUTPUT_DIR": "generated/town_country_asset_candidate",
    "TCA_APPROVED_DATA_DIR": "generated/town_country_asset",
    "TCA_REPORT_DIR": "reports/data-refresh",
    "TCA_ISO_PROPOSAL_REPORT": "reports/iso-assignment-proposals.md",
    "TCA_GENERATION_CONFIG": "config/generation.json",
    "TCA_REGIONS_CONFIG": "config/regions.json",
    "TCA_IDENTITY_REGISTRY": "config/country_identity_registry.json",
    "TCA_GENERATE_SVGS": "true",
    "TCA_COMPARE_WITH_APPROVED": "true",
    "TCA_RUN_ISO_REVIEW": "true",
    "TCA_RUN_PERSIAN_LOCALIZATION": "true",
    "TCA_HTTP_TIMEOUT_SECONDS": "60",
}
USER_AGENT = "TownCountryAsset-DataPipeline/1.0"


def load_dotenv(path: Path, environ: dict[str, str] | None = None) -> dict[str, str]:
    """Load simple KEY=VALUE lines; existing environment values win."""
    result = dict(os.environ if environ is None else environ)
    if not path.exists():
        return result
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ValueError(f"{path}:{number}: expected KEY=VALUE")
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
            raise ValueError(f"{path}:{number}: invalid environment variable name")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        result.setdefault(key, value)
    for key, default in DEFAULTS.items():
        result.setdefault(key, default)
    return result


def enabled(value: str, key: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{key} must be true/false, yes/no, on/off, or 1/0")


def configured_path(config: dict[str, str], key: str) -> Path:
    path = Path(config[key]).expanduser()
    return path if path.is_absolute() else ROOT / path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_archive(url: str, destination_dir: Path, timeout: float, now: datetime) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Natural Earth source URL must be an absolute HTTPS URL")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise RuntimeError(f"HTTP status {status}")
            payload = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Download failed for {url}: {exc}") from exc
    if not payload:
        raise RuntimeError(f"Download returned an empty response: {url}")
    # A ZIP signature check catches HTML error pages served with HTTP 200.
    if not payload.startswith(b"PK\x03\x04"):
        raise ValueError("Natural Earth download does not look like a ZIP archive (missing ZIP signature)")
    stamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination_dir.mkdir(parents=True, exist_ok=True)
    archive_path = destination_dir / f"natural-earth-admin0-{stamp}.zip"
    provenance_path = destination_dir / f"natural-earth-admin0-provenance-{stamp}.json"
    if archive_path.exists() or provenance_path.exists():
        raise FileExistsError(f"Refusing to overwrite source snapshot for {stamp}")
    archive_path.write_bytes(payload)
    metadata = {
        "dataset": "Natural Earth Admin 0 Countries",
        "source_url": url,
        "retrieved_at_utc": now.astimezone(timezone.utc).isoformat(),
        "archive_path": str(archive_path.relative_to(ROOT)) if archive_path.is_relative_to(ROOT) else str(archive_path),
        "archive_sha256": sha256_bytes(payload),
        "archive_size_bytes": len(payload),
        "release_version": None,
        "release_version_note": "Not inferred from the download URL; fill only from verifiable upstream release metadata.",
    }
    provenance_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {"archive": archive_path, "provenance": provenance_path, **metadata}


def create_staging_dir(output_dir: Path) -> Path:
    """Create an isolated sibling directory for a candidate build."""
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.staging-", dir=output_dir.parent))


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, ignore_errors=True)
    else:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def publish_candidate(staging_dir: Path, output_dir: Path) -> None:
    """Replace candidate output only after all build stages and audits pass.

    The existing candidate is moved aside first and restored if publishing the
    staging directory fails. The approved snapshot is never touched.
    """
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    backup_dir = output_dir.with_name(f".{output_dir.name}.backup-{uuid.uuid4().hex}")
    had_output = output_dir.exists() or output_dir.is_symlink()
    if had_output:
        output_dir.rename(backup_dir)
    try:
        staging_dir.rename(output_dir)
    except OSError:
        if had_output and backup_dir.exists() and not output_dir.exists():
            backup_dir.rename(output_dir)
        raise
    if had_output:
        _remove_path(backup_dir)


def run_command(label: str, command: list[str], results: list[dict[str, Any]]) -> bool:
    try:
        completed = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, check=False
        )
        results.append({
            "stage": label,
            "status": "success" if completed.returncode == 0 else "failed",
            "return_code": completed.returncode,
            "command": command,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        })
        return completed.returncode == 0
    except OSError as exc:
        results.append({
            "stage": label, "status": "failed", "return_code": None,
            "command": command, "stdout": "", "stderr": str(exc),
        })
        return False


def write_summary(report_dir: Path, started: datetime, stages: list[dict[str, Any]], fetched: dict[str, Any] | None,
                  output_dir: Path, overall_status: str) -> tuple[Path, Path]:
    finished = datetime.now(timezone.utc)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / f"data-refresh-{stamp}.json"
    md_path = report_dir / f"data-refresh-{stamp}.md"
    summary = {
        "status": overall_status,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
        "duration_seconds": round((finished - started).total_seconds(), 3),
        "candidate_output_dir": str(output_dir),
        "natural_earth": ({
            "source_url": fetched["source_url"],
            "archive": str(fetched["archive"]),
            "provenance": str(fetched["provenance"]),
            "sha256": fetched["archive_sha256"],
            "size_bytes": fetched["archive_size_bytes"],
        } if fetched else None),
        "stages": stages,
    }
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Data refresh run summary", "",
        f"- **Status:** {overall_status.upper()}",
        f"- Started (UTC): {started.isoformat()}",
        f"- Finished (UTC): {finished.isoformat()}",
        f"- Duration: {summary['duration_seconds']} seconds",
        f"- Candidate output: `{output_dir}`",
        "",
        "## Source fetch",
        "",
    ]
    if fetched:
        lines += [
            f"- Source URL: {fetched['source_url']}",
            f"- Archive: `{fetched['archive']}`",
            f"- SHA-256: `{fetched['archive_sha256']}`",
            f"- Size: {fetched['archive_size_bytes']} bytes",
        ]
    else:
        lines.append("- Natural Earth source fetch did not complete.")
    lines += ["", "## Pipeline stages", ""]
    for stage in stages:
        lines.append(f"### {stage['stage']}: {stage['status'].upper()}")
        if stage.get("stdout"):
            lines += ["", "Output:", "```text", stage["stdout"], "```"]
        if stage.get("stderr"):
            lines += ["", "Errors/details:", "```text", stage["stderr"], "```"]
        lines.append("")
    lines += [
        "## Safety notes", "",
        "- Candidate outputs are not promoted to the approved snapshot.",
        "- This run does not write to TownCountryGame.",
        "- ISO candidates remain review-only; no assignment is automatically verified.",
        "- Persian localization labels remain review-only; no label is automatically approved or written to the identity registry.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path


def execute(config: dict[str, str]) -> int:
    started = datetime.now(timezone.utc)
    report_dir = configured_path(config, "TCA_REPORT_DIR")
    output_dir = configured_path(config, "TCA_GAME_DATA_OUTPUT_DIR")
    source_dir = configured_path(config, "TCA_FETCHED_DATA_DIR")
    iso_dir = configured_path(config, "TCA_ISO_DATA_DIR")
    stages: list[dict[str, Any]] = []
    fetched: dict[str, Any] | None = None
    staging_dir: Path | None = None
    failed = False
    timeout = float(config["TCA_HTTP_TIMEOUT_SECONDS"])
    if timeout <= 0:
        raise ValueError("TCA_HTTP_TIMEOUT_SECONDS must be positive")
    for flag in ("TCA_GENERATE_SVGS", "TCA_COMPARE_WITH_APPROVED", "TCA_RUN_ISO_REVIEW", "TCA_RUN_PERSIAN_LOCALIZATION"):
        enabled(config[flag], flag)
    try:
        fetched = fetch_archive(
            config["TCA_NATURAL_EARTH_URL"], source_dir, timeout, started
        )
        stages.append({
            "stage": "fetch Natural Earth archive", "status": "success",
            "stdout": f"Saved {fetched['archive']}\nSHA-256: {fetched['archive_sha256']}",
            "stderr": "",
        })
    except Exception as exc:
        failed = True
        stages.append({"stage": "fetch Natural Earth archive", "status": "failed",
                       "return_code": None, "stdout": "", "stderr": str(exc)})

    if not failed and enabled(config["TCA_RUN_ISO_REVIEW"], "TCA_RUN_ISO_REVIEW"):
        ok = run_command("refresh ISO review proposals", [
            sys.executable, "tools/refresh_iso_review.py",
            "--output-dir", str(iso_dir),
            "--report", str(configured_path(config, "TCA_ISO_PROPOSAL_REPORT")),
            "--source-url", config["TCA_ISO_REFERENCE_URL"],
        ], stages)
        failed = failed or not ok

    if not failed and fetched and enabled(config["TCA_RUN_PERSIAN_LOCALIZATION"], "TCA_RUN_PERSIAN_LOCALIZATION"):
        ok = run_command("refresh Persian localization proposals from current Wikidata labels", [
            sys.executable, "tools/refresh_persian_localization.py",
            "--source-archive", str(fetched["archive"]),
            "--registry", str(configured_path(config, "TCA_IDENTITY_REGISTRY")),
            "--output-dir", str(configured_path(config, "TCA_PERSIAN_DATA_DIR")),
            "--report", str(configured_path(config, "TCA_PERSIAN_LOCALIZATION_REPORT")),
            "--source-url", config["TCA_PERSIAN_LABEL_SOURCE_URL"],
            "--timeout", str(timeout),
        ], stages)
        failed = failed or not ok

    if not failed and fetched:
        try:
            staging_dir = create_staging_dir(output_dir)
            stages.append({
                "stage": "prepare isolated candidate directory", "status": "success",
                "stdout": str(staging_dir), "stderr": "",
            })
        except OSError as exc:
            failed = True
            stages.append({
                "stage": "prepare isolated candidate directory", "status": "failed",
                "return_code": None, "stdout": "", "stderr": str(exc),
            })

    if not failed and fetched and staging_dir:
        compile_command = [
            sys.executable, "tools/compile_natural_earth.py",
            "--source", str(fetched["archive"]),
            "--output", str(staging_dir),
            "--config", str(configured_path(config, "TCA_GENERATION_CONFIG")),
            "--regions", str(configured_path(config, "TCA_REGIONS_CONFIG")),
            "--identity-registry", str(configured_path(config, "TCA_IDENTITY_REGISTRY")),
        ]
        ok = run_command("compile candidate game data", compile_command, stages)
        failed = failed or not ok

    if not failed and enabled(config["TCA_GENERATE_SVGS"], "TCA_GENERATE_SVGS"):
        ok = run_command("generate SVG assets", [
            sys.executable, "tools/generate_country_svgs.py",
            "--data", str(staging_dir),
            "--output", str(staging_dir / "svg"),
        ], stages)
        failed = failed or not ok

    if not failed:
        ok = run_command("audit generated assets", [
            sys.executable, "tools/audit_generated_assets.py",
            "--data", str(staging_dir),
            "--source", str(fetched["archive"]),
        ], stages)
        failed = failed or not ok

    if not failed:
        ok = run_command("audit persistent identity registry", [
            sys.executable, "tools/audit_country_identity_registry.py",
            "--registry", str(configured_path(config, "TCA_IDENTITY_REGISTRY")),
            "--output", str(report_dir / "country-identity-review.md"),
        ], stages)
        failed = failed or not ok

    if not failed and enabled(config["TCA_COMPARE_WITH_APPROVED"], "TCA_COMPARE_WITH_APPROVED"):
        approved = configured_path(config, "TCA_APPROVED_DATA_DIR")
        if approved.is_dir() and (approved / "countries.json").is_file():
            ok = run_command("compare candidate with approved snapshot", [
                sys.executable, "tools/compare_asset_snapshots.py",
                "--old", str(approved), "--new", str(staging_dir),
                "--new-display-path", str(output_dir),
                "--output", str(report_dir / "asset-comparison.md"),
            ], stages)
            failed = failed or not ok
        else:
            stages.append({
                "stage": "compare candidate with approved snapshot",
                "status": "skipped",
                "stdout": f"No approved snapshot found at {approved}; no comparison performed.",
                "stderr": "",
            })

    if not failed and staging_dir is not None:
        try:
            publish_candidate(staging_dir, output_dir)
            staging_dir = None
            stages.append({
                "stage": "publish validated candidate", "status": "success",
                "stdout": f"Published validated candidate to {output_dir}", "stderr": "",
            })
        except OSError as exc:
            failed = True
            stages.append({
                "stage": "publish validated candidate", "status": "failed",
                "return_code": None, "stdout": "", "stderr": str(exc),
            })

    if staging_dir is not None:
        _remove_path(staging_dir)

    status = "failed" if failed else "success"
    try:
        md_path, json_path = write_summary(report_dir, started, stages, fetched, output_dir, status)
        print(f"Data refresh {status.upper()}.")
        print(f"Summary: {md_path}")
        print(f"Machine-readable report: {json_path}")
        for stage in stages:
            print(f"- {stage['stage']}: {stage['status']}")
    except OSError as exc:
        print(f"Could not write run summary: {exc}", file=sys.stderr)
        return 1
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env",
                        help="local KEY=VALUE configuration file (default: repository .env)")
    parser.add_argument("--help-config", action="store_true",
                        help="show configuration keys and their defaults")
    args = parser.parse_args()
    if args.help_config:
        for key, value in DEFAULTS.items():
            print(f"{key}={value}")
        return 0
    try:
        config = load_dotenv(args.env_file.expanduser())
        return execute(config)
    except (OSError, ValueError) as exc:
        started = datetime.now(timezone.utc)
        try:
            report_dir = ROOT / "reports" / "data-refresh"
            md_path, json_path = write_summary(
                report_dir, started,
                [{"stage": "load configuration", "status": "failed", "return_code": None,
                  "stdout": "", "stderr": str(exc)}],
                None, ROOT / "generated" / "town_country_asset_candidate", "failed",
            )
            print(f"Configuration failed: {exc}", file=sys.stderr)
            print(f"Failure report: {md_path}", file=sys.stderr)
            print(f"Machine-readable report: {json_path}", file=sys.stderr)
        except OSError as report_error:
            print(f"Configuration error: {exc}; also failed to write report: {report_error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
