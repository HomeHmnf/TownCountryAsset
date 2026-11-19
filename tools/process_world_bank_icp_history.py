"""Review, dry-run and approval-gated import of ICP annual PPP history.

This adapter never guesses country identities. Proposed mappings remain pending
until a reviewer edits the crosswalk and re-fingerprints the complete input set.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.database.application_approval import (
    ApplicationApprovalError, build_application_artifact,
    propose_application, require_approved_application, record_application_applied,
)
from tools.database.connection import DEFAULT_DATABASE_PATH, REPOSITORY_ROOT, connect_database
from tools.database.schema import apply_migrations, validate_database
from tools.validate_world_bank_icp_databank import validate_manifest

ROOT = REPOSITORY_ROOT
DEFAULT_MANIFEST = Path("data_manifests/sources/world_bank_icp/databank_exports/databank_20261119T075746677306Z.json")
DEFAULT_MAPPING = Path("data/manual/source_crosswalks/world_bank_icp.json")
ASSET_COUNTRIES = Path("generated/town_country_asset/countries.json")
WPP_CROSSWALK = Path("data/manual/source_crosswalks/un_wpp.json")
REPORT_DIR = Path("reports/sources/world-bank-icp/country-mapping-review")
DOMAIN = "world_bank_icp_historical_statistics"
UNIT = "PPP ratio (US$ = 1)"
INDICATOR_NAMES = {
    "1000000": "Gross domestic product",
    "9020000": "Actual individual consumption",
    "9100000": "Households and NPISHs final consumption expenditure",
    "9270000": "General government final consumption expenditure",
    "1501000": "Gross fixed capital formation",
    "9250000": "Domestic absorption",
}


class ICPHistoryError(RuntimeError):
    """An ICP history review or import cannot safely proceed."""


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ICPHistoryError(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ICPHistoryError(f"Expected a JSON object in {path}")
    return value


def _manifest_paths(root: Path, manifest_path: Path) -> tuple[dict[str, Any], Path, Path]:
    manifest_file = (root / manifest_path).resolve() if not manifest_path.is_absolute() else manifest_path.resolve()
    manifest_file.relative_to(root.resolve())
    validation = validate_manifest(repository_root=root, manifest_path=manifest_file)
    manifest = _json(manifest_file)
    files = manifest.get("files")
    if not isinstance(files, list):
        raise ICPHistoryError("Manifest files must be an array")
    data = next((x for x in files if x.get("artifact_role") == "extracted_csv_member"
                 and str(x.get("source_filename", x.get("archive_member", ""))).endswith("_Data.csv")), None)
    # Older manifests identify the Data member by archive_member, not source_filename.
    if data is None:
        data = next((x for x in files if x.get("artifact_role") == "extracted_csv_member"
                     and str(x.get("archive_member", "")).endswith("_Data.csv")), None)
    metadata = next((x for x in files if x.get("artifact_role") == "extracted_csv_member"
                     and "Metadata" in str(x.get("archive_member", ""))), None)
    if data is None or metadata is None:
        raise ICPHistoryError("Manifest must identify Data and Series Metadata CSV artifacts")
    data_path = (root / data["local_raw_path"]).resolve()
    metadata_path = (root / metadata["local_raw_path"]).resolve()
    data_path.relative_to(root.resolve())
    metadata_path.relative_to(root.resolve())
    return manifest, data_path, metadata_path


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
    from io import StringIO
    reader = csv.DictReader(StringIO(text, newline=""), strict=True)
    if not reader.fieldnames:
        raise ICPHistoryError(f"CSV has no header: {path}")
    if len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ICPHistoryError(f"CSV has duplicate headers: {path}")
    return list(reader.fieldnames), list(reader)


def _norm_m49(value: Any) -> str:
    raw = str(value or "").strip()
    return str(int(raw)) if raw.isdigit() else raw


def _dimension_members(manifest: dict[str, Any], control: str) -> list[dict[str, str]]:
    for dim in manifest.get("dimensions", []):
        if dim.get("control_id") == control:
            return list(dim.get("selected_members") or [])
    raise ICPHistoryError(f"Manifest has no {control} dimension")


def _series_dictionary(metadata_path: Path, manifest: dict[str, Any]) -> list[dict[str, str]]:
    _, rows = _read_csv(metadata_path)
    descriptions = {}
    for row in rows:
        code = (row.get("Classification Name") or "").strip()
        name = (row.get("Classification Code") or "").strip()
        if code == "Code" and name:
            continue
        if code.isdigit() and name:
            descriptions[code] = name
    result = []
    for member in _dimension_members(manifest, "Series"):
        unique = str(member.get("unique_name", ""))
        code = unique.rsplit("&[", 1)[-1].rstrip("]")
        label = member.get("display_name", "")
        result.append({
            "indicator_code": code,
            "indicator_name": INDICATOR_NAMES.get(code, label.split(":", 1)[-1].strip()),
            "source_display_name": label,
            "source_definition": descriptions.get(code, ""),
            "unit": UNIT,
        })
    if len(result) != 6 or {x["indicator_code"] for x in result} != set(INDICATOR_NAMES):
        raise ICPHistoryError("Selected ICP Series dimension does not match the six reviewed indicator codes")
    return result


def build_country_mapping_review(
    *, repository_root: str | Path = ROOT, manifest_path: str | Path,
    asset_countries_path: str | Path = ASSET_COUNTRIES,
    wpp_crosswalk_path: str | Path = WPP_CROSSWALK,
    output_dir: str | Path = REPORT_DIR,
    crosswalk_path: str | Path = DEFAULT_MAPPING,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    manifest, data_path, metadata_path = _manifest_paths(root, Path(manifest_path))
    headers, rows = _read_csv(data_path)
    if not {"Country Code", "Country Name"}.issubset(headers):
        raise ICPHistoryError("Data CSV is missing country identity columns")
    country_rows: dict[str, str] = {}
    for row in rows:
        code, name = (row.get("Country Code") or "").strip(), (row.get("Country Name") or "").strip()
        if code and name:
            if code in country_rows and country_rows[code] != name:
                raise ICPHistoryError(f"Country code {code} has conflicting labels")
            country_rows[code] = name
    assets = _json(root / asset_countries_path)
    wpp = _json(root / wpp_crosswalk_path)
    by_iso3: dict[str, list[dict[str, Any]]] = {}
    for item in assets.get("countries", []):
        iso = str(item.get("iso3") or "").upper()
        if iso:
            by_iso3.setdefault(iso, []).append(item)
    by_m49: dict[str, list[dict[str, Any]]] = {}
    for item in wpp.get("mappings", []):
        by_m49.setdefault(_norm_m49(item.get("source_id")), []).append(item)
    aggregate_codes = {"EAB", "ECB", "LCB", "MEB", "NAB", "SAB", "SSB", "WLD"}
    mappings, exceptions = [], []
    for code, name in sorted(country_rows.items(), key=lambda pair: pair[0]):
        asset_matches = by_iso3.get(code, [])
        game_matches = []
        for asset in asset_matches:
            m49 = _norm_m49((asset.get("source_attributes") or {}).get("UN_A3"))
            game_matches.extend(by_m49.get(m49, []))
        unique_games = {x["game_id"]: x for x in game_matches}
        if len(asset_matches) == 1 and len(unique_games) == 1:
            asset = asset_matches[0]
            match = next(iter(unique_games.values()))
            mappings.append({
                "source_country_code": code,
                "source_country_name": name,
                "asset_country_id": asset.get("id"),
                "asset_country_name": asset.get("name"),
                "game_id": match["game_id"],
                "wpp_m49_source_id": match["source_id"],
                "match_method": "candidate_iso3_asset_and_un_m49_wpp_crosswalk",
                "review_status": "pending",
                "review_note": "Candidate only. Verify ICP entity scope and persistent game identity before changing review_status to approved.",
            })
        else:
            if code in aggregate_codes or "Benchmark" in name:
                status = "aggregate_not_a_country"
            elif not asset_matches:
                status = "unmatched_identity"
            elif len(asset_matches) > 1 or len(unique_games) > 1:
                status = "ambiguous_identity"
            else:
                status = "manual_review_no_approved_game_crosswalk"
            exceptions.append({
                "source_country_code": code,
                "source_country_name": name,
                "asset_candidates": [
                    {"asset_country_id": x.get("id"), "asset_country_name": x.get("name"),
                     "un_m49": (x.get("source_attributes") or {}).get("UN_A3")}
                    for x in asset_matches
                ],
                "game_id_candidates": sorted(unique_games),
                "status": status,
                "review_status": "pending",
            })
    indicators = _series_dictionary(metadata_path, manifest)
    counts = Counter(x["status"] for x in exceptions)
    summary = {
        "source_country_count": len(country_rows),
        "candidate_game_mappings": len(mappings),
        "exact_iso3_asset_matches": len(mappings) + sum(bool(x["asset_candidates"]) for x in exceptions),
        "ambiguous": counts["ambiguous_identity"],
        "manual_review_no_approved_game_crosswalk": counts["manual_review_no_approved_game_crosswalk"],
        "aggregate_not_a_country": counts["aggregate_not_a_country"],
        "unmatched_identity": counts["unmatched_identity"],
        "approved_mappings": 0,
        "policy": "All candidate mappings remain pending; no name-only, fuzzy, ISO-inferred or aggregate-to-country mapping is approved automatically.",
    }
    report = {
        "schema_version": 1,
        "report_type": "world_bank_icp_country_identity_mapping_review",
        "source_key": "world_bank_icp",
        "dataset_key": "world_bank_icp_databank_saved_report",
        "export_id": manifest.get("export_id"),
        "retrieved_at": manifest.get("retrieved_at"),
        "mapping_basis": {
            "first_link": "ICP Country Code equals generated asset ISO3 code",
            "second_link": "generated asset UN_A3 M49 code joins the already-reviewed UN WPP source crosswalk",
            "limitation": "This is a candidate bridge, not an ICP-approved identity crosswalk; the existing WPP approval is explicitly source-specific.",
        },
        "summary": summary,
        "indicators": indicators,
        "mappings": mappings,
        "exceptions": exceptions,
    }
    out = (root / output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "country_mapping_review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (out / "country_mapping_review.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "source_country_code", "source_country_name", "asset_country_id",
            "asset_country_name", "game_id", "wpp_m49_source_id", "status",
            "review_status", "review_note",
        ])
        writer.writeheader()
        for item in mappings:
            writer.writerow({**item, "status": "candidate_mapping"})
        for item in exceptions:
            writer.writerow({
                "source_country_code": item["source_country_code"],
                "source_country_name": item["source_country_name"],
                "asset_country_id": ";".join(x["asset_country_id"] or "" for x in item["asset_candidates"]),
                "asset_country_name": ";".join(x["asset_country_name"] or "" for x in item["asset_candidates"]),
                "game_id": ";".join(item["game_id_candidates"]),
                "status": item["status"], "review_status": item["review_status"],
            })
    (out / "indicator_dictionary.json").write_text(json.dumps(indicators, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    crosswalk_file = (root / crosswalk_path).resolve() if not Path(crosswalk_path).is_absolute() else Path(crosswalk_path).resolve()
    crosswalk_file.relative_to(root)
    crosswalk_file.parent.mkdir(parents=True, exist_ok=True)
    crosswalk = {
        "schema_version": 1, "dataset": "world_bank_icp_databank_saved_report",
        "source_key": "world_bank_icp", "mapping_policy": report["mapping_basis"],
        "review_approval": {"status": "pending", "scope": "ICP source identity mapping only; not global identity or ISO assignment approval."},
        "mappings": mappings, "exceptions": exceptions,
    }
    crosswalk_file.write_text(json.dumps(crosswalk, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    return report


def _approved_mapping_index(mapping: dict[str, Any]) -> dict[str, dict[str, str]]:
    result = {}
    seen_games = set()
    for item in mapping.get("mappings", []):
        if item.get("review_status") != "approved":
            continue
        code, game_id = item.get("source_country_code"), item.get("game_id")
        if not isinstance(code, str) or not isinstance(game_id, str):
            raise ICPHistoryError("Approved mapping requires source_country_code and game_id")
        if code in result or game_id in seen_games:
            raise ICPHistoryError("Approved ICP country mappings must be one-to-one")
        result[code] = item
        seen_games.add(game_id)
    return result


def dry_run_icp_history(
    *, repository_root: str | Path = ROOT, manifest_path: str | Path,
    mapping_path: str | Path = DEFAULT_MAPPING,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    manifest, data_path, metadata_path = _manifest_paths(root, Path(manifest_path))
    mapping_file = (root / mapping_path).resolve() if not Path(mapping_path).is_absolute() else Path(mapping_path).resolve()
    mapping_file.relative_to(root)
    mapping = _json(mapping_file)
    headers, rows = _read_csv(data_path)
    indicator_columns = [x for x in headers if x[:1].isdigit() and ":" in x]
    indicator_codes = [x.split(":", 1)[0] for x in indicator_columns]
    country_codes = {x["source_country_code"] for x in mapping.get("mappings", [])}
    country_codes.update(x["source_country_code"] for x in mapping.get("exceptions", []))
    selected_country_count = next((int(x["selected_count"]) for x in manifest["dimensions"] if x.get("control_id") == "Country"), None)
    if selected_country_count is None or len(country_codes) != selected_country_count:
        raise ICPHistoryError("Mapping review does not cover the complete selected Country dimension")
    approved = _approved_mapping_index(mapping)
    if set(indicator_codes) != set(INDICATOR_NAMES):
        raise ICPHistoryError("Data CSV indicator columns differ from the six-indicator contract")
    valid_rows = [r for r in rows if (r.get("Country Code") or "").strip() and (r.get("Time Code") or "").strip()]
    expected = len(valid_rows) * len(indicator_columns)
    observed = missing = eligible = 0
    per_indicator = {}
    mapped_codes = set(approved)
    for col, code in zip(indicator_columns, indicator_codes):
        count_observed = count_missing = count_eligible = 0
        for row in valid_rows:
            raw = (row.get(col) or "").strip()
            if raw == "..":
                count_missing += 1
            else:
                try:
                    value = float(raw)
                except ValueError as exc:
                    raise ICPHistoryError(f"Non-numeric value {raw!r} in {col}") from exc
                if not math.isfinite(value):
                    raise ICPHistoryError(f"Non-finite value in {col}")
                count_observed += 1
            if (row.get("Country Code") or "").strip() in mapped_codes:
                count_eligible += 1
        per_indicator[code] = {
            "indicator_name": INDICATOR_NAMES[code],
            "observed_values": count_observed,
            "source_missing_values": count_missing,
            "eligible_rows_after_mapping_approval": count_eligible,
        }
        observed += count_observed
        missing += count_missing
        eligible += count_eligible
    years = sorted({(r.get("Time") or "").strip() for r in valid_rows})
    return {
        "assessment": "world_bank_icp_historical_import_dry_run",
        "export_id": manifest.get("export_id"),
        "observation_rows": len(valid_rows),
        "country_year_rows": len(valid_rows),
        "indicator_count": len(indicator_columns),
        "historical_cells_expected": expected,
        "years": years,
        "source_country_count": len(country_codes),
        "approved_country_mappings": len(approved),
        "pending_candidate_mappings": sum(x.get("review_status") != "approved" for x in mapping.get("mappings", [])),
        "unmapped_or_manual_review_entities": len(mapping.get("exceptions", [])),
        "eligible_historical_cells": eligible,
        "observed_values": observed,
        "source_missing_values": missing,
        "indicators": per_indicator,
        "canonical_database_written": False,
        "game_database_written": False,
        "approval_created": False,
        "observations_imported": False,
        "status": "ready_for_mapping_review" if not approved else "ready_for_approval_proposal",
    }


def build_icp_application_artifact(
    *, repository_root: str | Path = ROOT, manifest_path: str | Path,
    mapping_path: str | Path = DEFAULT_MAPPING,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    manifest, data_path, metadata_path = _manifest_paths(root, Path(manifest_path))
    mapping_file = (root / mapping_path).resolve() if not Path(mapping_path).is_absolute() else Path(mapping_path).resolve()
    mapping = _json(mapping_file)
    approved = _approved_mapping_index(mapping)
    if not approved:
        raise ICPHistoryError("At least one explicitly approved ICP country mapping is required before proposing an import")
    return build_application_artifact(
        domain=DOMAIN,
        inputs=[Path(manifest_path) if Path(manifest_path).is_absolute() else root / manifest_path,
                data_path, metadata_path, mapping_file, root / ASSET_COUNTRIES, root / WPP_CROSSWALK],
        metadata={
            "source_key": "world_bank_icp",
            "export_id": manifest.get("export_id"),
            "approved_country_mapping_count": len(approved),
            "observation_period": "2017-2023",
            "indicator_codes": sorted(INDICATOR_NAMES),
            "history_table": "icp_historical_observations",
        },
    )


def propose_icp_application(
    *, approval_id: str, manifest_path: str | Path, mapping_path: str | Path = DEFAULT_MAPPING,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    artifact = build_icp_application_artifact(manifest_path=manifest_path, mapping_path=mapping_path)
    connection = connect_database(database_path)
    try:
        apply_migrations(connection)
        connection.execute("BEGIN IMMEDIATE")
        propose_application(connection, approval_id=approval_id, artifact=artifact)
        connection.commit()
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()
    return {"approval_id": approval_id, "status": "pending", "domain": DOMAIN,
            "artifact_sha256": artifact["artifact_sha256"], "approved_country_mapping_count": artifact["metadata"]["approved_country_mapping_count"]}


def import_icp_history(
    *, approval_id: str, manifest_path: str | Path, mapping_path: str | Path = DEFAULT_MAPPING,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    root = ROOT.resolve()
    manifest, data_path, metadata_path = _manifest_paths(root, Path(manifest_path))
    mapping_file = (root / mapping_path).resolve() if not Path(mapping_path).is_absolute() else Path(mapping_path).resolve()
    mapping = _json(mapping_file)
    approved = _approved_mapping_index(mapping)
    if not approved:
        raise ICPHistoryError("No explicitly approved country mappings are available")
    artifact = build_icp_application_artifact(manifest_path=manifest_path, mapping_path=mapping_path)
    headers, rows = _read_csv(data_path)
    series = _series_dictionary(metadata_path, manifest)
    series_by_code = {x["indicator_code"]: x for x in series}
    indicator_columns = {x.split(":", 1)[0]: x for x in headers if x[:1].isdigit() and ":" in x}
    connection = connect_database(database_path)
    try:
        apply_migrations(connection)
        connection.execute("BEGIN IMMEDIATE")
        require_approved_application(connection, approval_id=approval_id, artifact=artifact)
        country_status = {r["game_id"]: r["record_status"] for r in connection.execute("SELECT game_id, record_status FROM countries")}
        missing_game_ids = sorted({x["game_id"] for x in approved.values()} - set(country_status))
        if missing_game_ids:
            raise ICPHistoryError("Approved mapping references unknown canonical game IDs: " + ", ".join(missing_game_ids[:10]))
        ineligible = sorted(game_id for game_id in {x["game_id"] for x in approved.values()} if country_status[game_id] != "approved")
        if ineligible:
            raise ICPHistoryError("ICP mappings require approved canonical country identities: " + ", ".join(ineligible[:10]))
        imported_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        raw_sha = hashlib.sha256(data_path.read_bytes()).hexdigest()
        cursor = connection.execute(
            """INSERT INTO dataset_imports
               (dataset, source_version, source_url, retrieval_date, sha256, attribution, import_status, imported_at)
               VALUES (?, ?, ?, ?, ?, ?, 'approved', ?)""",
            ("world_bank_icp_databank_saved_report", manifest.get("export_id"),
             manifest.get("final_report_url") or manifest.get("report_url"),
             manifest.get("retrieved_at"), raw_sha, "World Bank International Comparison Program", imported_at),
        )
        import_id = int(cursor.lastrowid)
        inserted = 0
        for row in rows:
            code = (row.get("Country Code") or "").strip()
            if code not in approved:
                continue
            year_code = (row.get("Time Code") or "").strip()
            year = int(year_code.removeprefix("YR"))
            country = approved[code]
            for indicator_code, column in indicator_columns.items():
                raw = (row.get(column) or "").strip()
                if raw == "..":
                    value, status, missing_token = None, "source_missing", ".."
                else:
                    value = float(raw)
                    if not math.isfinite(value):
                        raise ICPHistoryError(f"Non-finite value for {code}/{year}/{indicator_code}")
                    status, missing_token = "observed", None
                info = series_by_code[indicator_code]
                connection.execute(
                    """INSERT INTO icp_historical_observations
                       (game_id, indicator_code, indicator_name, classification_code,
                        observation_year, value, value_status, missing_value_token, unit,
                        source_country_code, source_country_name, source_reference,
                        source_version, retrieved_at, import_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (country["game_id"], indicator_code, info["indicator_name"], "PPPGlob",
                     year, value, status, missing_token, UNIT, code,
                     row.get("Country Name", ""), manifest.get("report_url", ""),
                     manifest.get("export_id", ""), manifest.get("retrieved_at", ""), import_id),
                )
                inserted += 1
        issues = validate_database(connection)
        if issues:
            raise ICPHistoryError("Canonical database integrity check failed: " + "; ".join(issues))
        application_id = f"icp_history_{manifest.get('export_id')}_{import_id}"
        record_application_applied(connection, approval_id=approval_id, application_id=application_id,
                                   details={"import_id": import_id, "observation_count": inserted})
        connection.commit()
        return {"status": "applied", "import_id": import_id, "application_id": application_id,
                "historical_observation_count": inserted, "mapped_country_count": len(approved),
                "years": sorted({int((r.get("Time Code") or "").removeprefix("YR")) for r in rows if (r.get("Country Code") or "").strip() in approved}),
                "canonical_database_written": True, "game_database_written": False}
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--build-review", action="store_true", help="Build candidate country mapping and indicator reports")
    group.add_argument("--dry-run", action="store_true", help="Inspect import coverage without database writes (default)")
    group.add_argument("--propose", action="store_true", help="Create a pending canonical application approval proposal")
    group.add_argument("--apply", action="store_true", help="Apply only an exactly approved application artifact")
    parser.add_argument("--approval-id")
    args = parser.parse_args(argv)
    try:
        if args.build_review:
            result = build_country_mapping_review(manifest_path=args.manifest)
        elif args.propose:
            if not args.approval_id:
                raise ICPHistoryError("--propose requires --approval-id")
            result = propose_icp_application(approval_id=args.approval_id, manifest_path=args.manifest,
                                             mapping_path=args.mapping, database_path=args.database)
        elif args.apply:
            if not args.approval_id:
                raise ICPHistoryError("--apply requires --approval-id")
            result = import_icp_history(approval_id=args.approval_id, manifest_path=args.manifest,
                                        mapping_path=args.mapping, database_path=args.database)
        else:
            result = dry_run_icp_history(manifest_path=args.manifest, mapping_path=args.mapping)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ICPHistoryError, ApplicationApprovalError, OSError, ValueError, sqlite3.Error) as exc:
        print(f"ICP historical workflow failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
