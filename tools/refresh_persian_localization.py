#!/usr/bin/env python3
"""Fetch current Wikidata Persian labels as review-only localization candidates.

Wikidata items are joined to Natural Earth features only through the explicit
WIKIDATAID source attribute. Names are never used to infer an item mapping, and
the identity registry is never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import shapefile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_URL = "https://query.wikidata.org/sparql"
DEFAULT_ARCHIVE = Path("raw_data/fetched")
DEFAULT_REGISTRY = Path("config/country_identity_registry.json")
DEFAULT_OUTPUT_DIR = Path("raw_data/persian")
DEFAULT_REPORT = Path("reports/persian-localization-proposals.md")
USER_AGENT = "TownCountryAsset-PersianLocalization/1.0 (review-only data refresh)"
QID_PATTERN = re.compile(r"Q[1-9][0-9]*\Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def source_qids_from_archive(archive_path: Path) -> dict[str, str]:
    """Return stable Natural Earth source ID -> Wikidata QID mappings."""
    if not zipfile.is_zipfile(archive_path):
        raise ValueError(f"Natural Earth source is not a valid ZIP archive: {archive_path}")
    with tempfile.TemporaryDirectory(prefix="tca-wikidata-") as temp:
        root = Path(temp).resolve()
        with zipfile.ZipFile(archive_path) as archive:
            for info in archive.infolist():
                member = Path(info.filename)
                if member.is_absolute() or ".." in member.parts:
                    raise ValueError(f"Unsafe path in Natural Earth ZIP: {info.filename!r}")
                target = (root / member).resolve()
                if target != root and root not in target.parents:
                    raise ValueError(f"Unsafe path in Natural Earth ZIP: {info.filename!r}")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info) as source, target.open("wb") as sink:
                        sink.write(source.read())
        shp_files = list(root.rglob("*.shp")) + list(root.rglob("*.SHP"))
        if len(shp_files) != 1:
            raise ValueError(f"Expected exactly one shapefile in archive; found {len(shp_files)}")
        reader = shapefile.Reader(str(shp_files[0]), encoding="utf-8")
        try:
            fields = [field[0] for field in reader.fields[1:]]
            by_upper = {field.upper(): field for field in fields}
            source_field = by_upper.get("ADM0_A3")
            qid_field = by_upper.get("WIKIDATAID")
            if not source_field or not qid_field:
                raise ValueError(
                    "Natural Earth schema must contain ADM0_A3 and WIKIDATAID fields; "
                    f"found: {', '.join(fields)}"
                )
            mappings: dict[str, str] = {}
            for row_number, record in enumerate(reader.iterRecords(), start=1):
                attrs = dict(zip(fields, record))
                source_id = str(attrs.get(source_field) or "").strip()
                qid = str(attrs.get(qid_field) or "").strip()
                if not source_id or source_id in {"-99", "-"}:
                    continue
                if qid and not QID_PATTERN.fullmatch(qid):
                    qid = ""
                if source_id in mappings and mappings[source_id] != qid:
                    raise ValueError(f"Duplicate Natural Earth source ID {source_id!r} at row {row_number}")
                mappings[source_id] = qid
            return mappings
        finally:
            reader.close()


def build_sparql_query(qids: list[str]) -> str:
    valid = sorted({qid for qid in qids if QID_PATTERN.fullmatch(qid)})
    if not valid:
        raise ValueError("No valid Wikidata QIDs found in Natural Earth WIKIDATAID fields")
    values = " ".join(f"wd:{qid}" for qid in valid)
    return (
        "SELECT ?item ?itemLabel WHERE { VALUES ?item { " + values + " } "
        "?item rdfs:label ?itemLabel . FILTER(LANG(?itemLabel) = \"fa\") } "
        "ORDER BY ?item"
    )


def fetch_labels(source_url: str, qids: list[str], timeout: float) -> tuple[bytes, dict[str, str]]:
    parsed = urllib.parse.urlparse(source_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("TCA_PERSIAN_LABEL_SOURCE_URL must be an absolute HTTPS URL")
    query = build_sparql_query(qids)
    body = urllib.parse.urlencode({"query": query, "format": "json"}).encode("utf-8")
    request = urllib.request.Request(
        source_url,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/sparql-results+json, application/json",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise RuntimeError(f"Wikidata query returned HTTP {status}")
            payload = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not fetch Persian labels from {source_url}: {exc}") from exc
    if not payload:
        raise RuntimeError("Wikidata query returned an empty response")
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Wikidata response is not valid UTF-8 JSON") from exc
    bindings = decoded.get("results", {}).get("bindings")
    if not isinstance(bindings, list):
        raise ValueError("Wikidata response is missing results.bindings")
    labels: dict[str, str] = {}
    for index, binding in enumerate(bindings):
        item_uri = binding.get("item", {}).get("value", "")
        label = binding.get("itemLabel", {}).get("value", "").strip()
        qid = item_uri.rsplit("/", 1)[-1]
        if not QID_PATTERN.fullmatch(qid) or not label:
            raise ValueError(f"Invalid Wikidata binding at row {index + 1}")
        if qid in labels and labels[qid] != label:
            raise ValueError(f"Multiple Persian labels returned for {qid}")
        labels[qid] = label
    return payload, labels


def build_review(registry: dict[str, Any], source_qids: dict[str, str],
                 labels: dict[str, str]) -> dict[str, Any]:
    records = registry.get("records")
    if not isinstance(records, list):
        raise ValueError("Registry records must be an array")
    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Registry record {index} is not an object")
        game_id = record.get("game_id")
        if not isinstance(game_id, str) or not game_id.strip() or game_id in seen_ids:
            raise ValueError(f"Registry record {index} has a missing or duplicate game_id")
        seen_ids.add(game_id)
        source = record.get("source") if isinstance(record.get("source"), dict) else {}
        names = record.get("names") if isinstance(record.get("names"), dict) else {}
        source_id = str(source.get("current_source_id") or "")
        qid = source_qids.get(source_id, "")
        label = labels.get(qid, "") if qid else ""
        status = "candidate available; human review required" if label else (
            "no Wikidata QID in source" if not qid else "no Persian label returned"
        )
        rows.append({
            "game_id": game_id,
            "source_id": source_id,
            "english_name": str(names.get("en") or ""),
            "current_persian_name": str(names.get("fa") or ""),
            "wikidata_qid": qid,
            "candidate_persian_name": label,
            "candidate_status": status,
            "review_status": "unreviewed",
        })
    return {
        "record_count": len(records),
        "unique_game_ids": len(seen_ids),
        "candidate_count": sum(bool(row["candidate_persian_name"]) for row in rows),
        "missing_qid_count": sum(not row["wikidata_qid"] for row in rows),
        "missing_label_count": sum(bool(row["wikidata_qid"]) and not row["candidate_persian_name"] for row in rows),
        "rows": rows,
    }


def render_report(review: dict[str, Any], source_url: str, retrieved_at: str,
                  raw_path: Path, provenance_path: Path, raw_sha256: str) -> str:
    lines = [
        "# Persian localization proposal review", "",
        "- **Status:** proposals only; no labels are approved or written to the identity registry.",
        f"- Source endpoint: {source_url}",
        f"- Retrieved at (UTC): {retrieved_at}",
        f"- Raw response: `{raw_path}`",
        f"- Provenance: `{provenance_path}`",
        f"- Raw response SHA-256: `{raw_sha256}`",
        f"- Registry records: {review['record_count']}",
        f"- Unique stable game IDs: {review['unique_game_ids']}",
        f"- Persian label candidates: {review['candidate_count']}",
        f"- Missing Wikidata QIDs: {review['missing_qid_count']}",
        f"- QIDs without a Persian label: {review['missing_label_count']}",
        "", "## Record-level review worksheet", "",
        "| game_id | Source ID | English name | Current Persian name | Wikidata QID | Candidate Persian name | Candidate status | Review status |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in review["rows"]:
        cells = [row[key] for key in (
            "game_id", "source_id", "english_name", "current_persian_name",
            "wikidata_qid", "candidate_persian_name", "candidate_status", "review_status",
        )]
        lines.append("| " + " | ".join(
            (value or "—").replace("|", "\\|").replace("\n", " ").replace("\r", " ")
            for value in cells
        ) + " |")
    lines += [
        "", "## Review safeguards", "",
        "- The mapping from a Natural Earth feature to Wikidata uses only its explicit WIKIDATAID field.",
        "- English or Persian names, ISO codes, source order, and fuzzy matching are not used to infer Wikidata identity.",
        "- Candidate labels are current labels returned by the configured endpoint at retrieval time, not verified official translations.",
        "- No candidate is applied to config/country_identity_registry.json or generated/approved game data.",
        "- Reviewers should record evidence and decisions before any separately designed approval workflow.",
        "",
    ]
    return "\n".join(lines)


def refresh(archive_path: Path, registry_path: Path = DEFAULT_REGISTRY,
            output_dir: Path = DEFAULT_OUTPUT_DIR, report_path: Path = DEFAULT_REPORT,
            source_url: str = DEFAULT_SOURCE_URL, timeout: float = 60.0,
            now: datetime | None = None) -> dict[str, Any]:
    retrieved = now or datetime.now(timezone.utc)
    if retrieved.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    source_qids = source_qids_from_archive(archive_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry_ids = {str(record.get("source", {}).get("current_source_id") or "") for record in registry.get("records", [])}
    relevant_qids = sorted({qid for source_id, qid in source_qids.items() if source_id in registry_ids and qid})
    payload, labels = fetch_labels(source_url, relevant_qids, timeout)
    review = build_review(registry, source_qids, labels)
    stamp = retrieved.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / f"wikidata-persian-labels-{stamp}.json"
    candidates_path = output_dir / f"wikidata-persian-candidates-{stamp}.json"
    provenance_path = output_dir / f"wikidata-persian-provenance-{stamp}.json"
    if any(path.exists() for path in (raw_path, candidates_path, provenance_path)):
        raise FileExistsError(f"Refusing to overwrite Wikidata snapshot for {stamp}")
    raw_path.write_bytes(payload)
    candidates_path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metadata = {
        "dataset": "Wikidata Persian-language labels for Natural Earth Admin 0 features",
        "source_url": source_url,
        "source_description": "Current Persian (fa) rdfs:label values queried from Wikidata; review-only candidates.",
        "retrieved_at_utc": retrieved.astimezone(timezone.utc).isoformat(),
        "raw_snapshot": str(raw_path),
        "raw_sha256": sha256_bytes(payload),
        "raw_size_bytes": len(payload),
        "candidate_snapshot": str(candidates_path),
        "candidate_count": review["candidate_count"],
        "registry_record_count": review["record_count"],
        "wikidata_qid_count": len(relevant_qids),
        "label_count": len(labels),
    }
    provenance_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(review, source_url, metadata["retrieved_at_utc"], raw_path, provenance_path, metadata["raw_sha256"]), encoding="utf-8")
    return {
        "raw_snapshot": str(raw_path), "candidate_snapshot": str(candidates_path),
        "provenance": str(provenance_path), "report": str(report_path),
        "raw_sha256": metadata["raw_sha256"], "record_count": review["record_count"],
        "candidate_count": review["candidate_count"], "missing_qid_count": review["missing_qid_count"],
        "missing_label_count": review["missing_label_count"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    try:
        result = refresh(args.source_archive, args.registry, args.output_dir, args.report, args.source_url, args.timeout)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
