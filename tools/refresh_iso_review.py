#!/usr/bin/env python3
"""Fetch an ISO-code reference snapshot and generate review-only proposals.

The upstream dataset is a maintained third-party distribution of ISO 3166-1
codes, not the ISO organization's own downloadable product. The raw response is
preserved with a timestamp and checksum; normalized data and provenance are
written separately. No registry data is changed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.propose_iso_assignments import propose, read_reference, render_report


SOURCE_REPOSITORY = "https://github.com/stefangabos/world_countries"
SOURCE_URL = (
    "https://raw.githubusercontent.com/stefangabos/world_countries/"
    "master/data/countries/en/world.csv"
)
DEFAULT_OUTPUT_DIR = Path("raw_data/iso")
DEFAULT_REGISTRY = Path("config/country_identity_registry.json")
DEFAULT_REPORT = Path("reports/iso-assignment-proposals.md")
USER_AGENT = "TownCountryAsset-ISO-review/1.0"


def fetch_bytes(url: str = SOURCE_URL, timeout: float = 30.0) -> bytes:
    """Download source bytes with a timeout and an identifiable user agent."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise RuntimeError(f"Reference download returned HTTP {status}")
            payload = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not fetch ISO reference from {url}: {exc}") from exc
    if not payload:
        raise RuntimeError(f"Reference download from {url} was empty")
    return payload


def normalize_source(raw_bytes: bytes, minimum_rows: int = 200) -> tuple[str, int]:
    """Convert upstream CSV to the proposal tool's strict uppercase schema."""
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Reference download is not valid UTF-8") from exc

    reader = csv.DictReader(io.StringIO(text, newline=""))
    required = {"alpha2", "alpha3", "name"}
    columns = set(reader.fieldnames or [])
    missing = sorted(required - columns)
    if missing:
        raise ValueError(
            "Upstream CSV schema changed; missing columns: " + ", ".join(missing)
        )

    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output, fieldnames=["alpha2", "alpha3", "english_name"], lineterminator="\n"
    )
    writer.writeheader()
    count = 0
    seen2: set[str] = set()
    seen3: set[str] = set()
    for line, raw in enumerate(reader, start=2):
        alpha2 = (raw.get("alpha2") or "").strip().upper()
        alpha3 = (raw.get("alpha3") or "").strip().upper()
        name = (raw.get("name") or "").strip()
        if len(alpha2) != 2 or not alpha2.isascii() or not alpha2.isalpha():
            raise ValueError(f"Upstream CSV line {line}: invalid alpha2 {alpha2!r}")
        if len(alpha3) != 3 or not alpha3.isascii() or not alpha3.isalpha():
            raise ValueError(f"Upstream CSV line {line}: invalid alpha3 {alpha3!r}")
        if not name:
            raise ValueError(f"Upstream CSV line {line}: empty name")
        if alpha2 in seen2 or alpha3 in seen3:
            raise ValueError(f"Upstream CSV line {line}: duplicate ISO code")
        seen2.add(alpha2)
        seen3.add(alpha3)
        writer.writerow(
            {"alpha2": alpha2, "alpha3": alpha3, "english_name": name}
        )
        count += 1
    if count < minimum_rows:
        raise ValueError(
            f"Reference unexpectedly contains only {count} rows; refusing to use it"
        )
    return output.getvalue(), count


def refresh(
    registry_path: Path = DEFAULT_REGISTRY,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_path: Path = DEFAULT_REPORT,
    source_url: str = SOURCE_URL,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fetch, preserve, normalize, record provenance, and generate proposals."""
    retrieved = now or datetime.now(timezone.utc)
    if retrieved.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    stamp = retrieved.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    retrieved_on = retrieved.astimezone(timezone.utc).date().isoformat()

    raw_bytes = fetch_bytes(source_url)
    normalized_text, row_count = normalize_source(raw_bytes)
    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    normalized_sha256 = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / f"iso-3166-1-upstream-{stamp}.csv"
    normalized_path = output_dir / "iso-3166-1.csv"
    metadata_path = output_dir / f"iso-3166-1-provenance-{stamp}.json"
    # Timestamped raw snapshots are immutable: never overwrite an earlier fetch.
    if raw_path.exists() or metadata_path.exists():
        raise FileExistsError(f"Snapshot already exists for timestamp {stamp}")
    raw_path.write_bytes(raw_bytes)
    normalized_path.write_text(normalized_text, encoding="utf-8", newline="")
    metadata = {
        "dataset": "ISO 3166-1 alpha-2/alpha-3 reference",
        "source_url": source_url,
        "source_repository": SOURCE_REPOSITORY,
        "source_description": (
            "Third-party maintained distribution of ISO 3166-1 code elements; "
            "not a direct ISO-hosted export. Verify candidates against authoritative "
            "ISO evidence before approval."
        ),
        "retrieved_at_utc": retrieved.astimezone(timezone.utc).isoformat(),
        "retrieved_on_utc": retrieved_on,
        "raw_snapshot": str(raw_path),
        "raw_sha256": raw_sha256,
        "normalized_reference": str(normalized_path),
        "normalized_sha256": normalized_sha256,
        "reference_row_count": row_count,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    reference = read_reference(normalized_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    result = propose(registry, reference)
    report = render_report(
        result,
        str(normalized_path),
        f"{source_url} (third-party distribution; repository: {SOURCE_REPOSITORY})",
        retrieved_on,
    )
    report += (
        "\n## Download provenance\n\n"
        f"- Raw snapshot: `{raw_path}`\n"
        f"- Provenance metadata: `{metadata_path}`\n"
        f"- Raw SHA-256: `{raw_sha256}`\n"
        f"- Normalized SHA-256: `{normalized_sha256}`\n"
        f"- Reference row count: {row_count}\n"
        "- The source is not an ISO-hosted export; candidates remain unverified.\n"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return {
        "raw_snapshot": str(raw_path),
        "normalized_reference": str(normalized_path),
        "provenance": str(metadata_path),
        "report": str(report_path),
        "raw_sha256": raw_sha256,
        "normalized_sha256": normalized_sha256,
        "reference_row_count": row_count,
        "candidate_count": result["candidate_count"],
        "no_match_count": result["no_match_count"],
        "ambiguous_count": result["ambiguous_count"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--source-url", default=SOURCE_URL)
    args = parser.parse_args()
    try:
        result = refresh(
            registry_path=args.registry,
            output_dir=args.output_dir,
            report_path=args.report,
            source_url=args.source_url,
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
