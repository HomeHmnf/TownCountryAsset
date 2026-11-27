"""Build and validate the field-16 IMF WEO owner identity review; never approve or write databases."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "reports/sources/imf-weo-field16-identity-review/20261127T181310Z"
DEFAULT_OUTPUT = ROOT / "reports/sources/imf-weo-field16-owner-review"
EXPECTED_CODES = 195
SPECIAL_REVIEW_CODES = {
    "ABW", "AIA", "ASM", "BES", "CUW", "FLK", "FRO", "GIB", "GRL",
    "GUM", "HKG", "MAC", "MNP", "NCL", "PRI", "PYF", "SGS", "SXM",
    "TCA", "TWN", "VIR", "KOS",
}

DEFAULT_HISTORY_FILES = {
    "wdi": ROOT / "data/manual/source_crosswalks/world_bank_wdi_wp1_5_area.json",
    "wpp": ROOT / "data/manual/source_crosswalks/un_wpp.json",
    "icp": ROOT / "data/manual/source_crosswalks/world_bank_icp.json",
    "imf_weo": ROOT / "data/manual/source_crosswalks/imf_weo.json",
    "edge_cases": ROOT / "config/identity_edge_case_reconciliation.json",
}


def load_identity_history(paths: dict[str, Path]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Load source-scoped crosswalks and prior identity decisions as review evidence only."""
    by_source: dict[str, dict[str, Any]] = {}
    fingerprints: dict[str, str] = {}
    for key, path in paths.items():
        if not path.is_file():
            raise OwnerReviewError(f"Required project identity-history file is missing: {path}")
        fingerprints[key] = sha256(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        approval = payload.get("review_approval") or {}
        scope = str(approval.get("scope") or payload.get("policy", {}).get("catalogue") or "recorded project identity evidence")
        approval_status = str(approval.get("status") or "recorded")
        if key == "edge_cases":
            for item in payload.get("records", []):
                source_id = str(item.get("source_id") or "")
                if source_id:
                    by_source.setdefault(source_id, {})["prior_identity_decision"] = {
                        "game_id": item.get("game_id"),
                        "canonical_name": item.get("name"),
                        "iso": item.get("iso"),
                        "entity": item.get("entity"),
                        "catalogue": item.get("catalogue"),
                        "naming": item.get("naming"),
                        "policy_version": payload.get("policy_version"),
                        "reviewed_at": payload.get("reviewed_at"),
                    }
            continue
        for item in payload.get("mappings", []):
            source_id = str(item.get("source_id") or item.get("source_country_code") or "")
            game_id = str(item.get("game_id") or "")
            if not source_id and not game_id:
                continue
            evidence = {
                "dataset": payload.get("dataset") or key,
                "source_id": source_id or None,
                "source_name": item.get("source_name") or item.get("source_country_name"),
                "mapped_game_id": game_id or None,
                "approval_status": approval_status if key != "icp" else item.get("review_status", approval_status),
                "approval_scope": scope,
                "approval_record": approval.get("approval_record"),
                "match_method": item.get("match_method"),
                "evidence_reference": item.get("evidence_url"),
                "review_note": item.get("review_note"),
            }
            if source_id:
                by_source.setdefault(source_id, {}).setdefault("source_mappings", []).append(evidence)
            if game_id:
                by_source.setdefault(f"game_id:{game_id}", {}).setdefault("source_mappings", []).append(evidence)
        if key == "wpp":
            exception = payload.get("mapping_policy", {}).get("taiwan_exception")
            if exception:
                evidence = {
                    "dataset": payload.get("dataset"),
                    "source_id": exception.get("source_id"),
                    "source_name": exception.get("source_name"),
                    "mapped_game_id": exception.get("game_id"),
                    "approval_status": approval_status,
                    "approval_scope": exception.get("scope") or scope,
                    "approval_record": approval.get("approval_record"),
                    "match_method": exception.get("match_method"),
                    "evidence_reference": exception.get("evidence_url"),
                    "review_note": "Explicit WPP Taiwan exception; scope remains WPP only.",
                }
                by_source.setdefault(f"game_id:{exception.get('game_id')}", {}).setdefault("source_mappings", []).append(evidence)
    return by_source, fingerprints


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) if value else ""


class OwnerReviewError(RuntimeError):
    """Invalid, incomplete, or altered owner-review evidence."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise OwnerReviewError("Refusing to write an empty owner-review CSV")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def enrich_proposal(proposal: dict[str, str], registry_record: dict[str, Any], history: dict[str, dict[str, Any]]) -> dict[str, Any]:
    names = registry_record.get("names") or {}
    registry_name = str(names.get("en") or "")
    source_name = proposal["source_name"]
    aliases = [str(value) for value in names.get("aliases_en", []) if value]
    source_norm = normalize_name(source_name)
    if source_norm == normalize_name(registry_name):
        name_comparison = "exact_normalized_match"
    elif any(source_norm == normalize_name(alias) for alias in aliases):
        name_comparison = "registry_alias_match"
    else:
        name_comparison = "name_difference_requires_review"

    iso = registry_record.get("iso") or {}
    source = registry_record.get("source") or {}
    flags = []
    if registry_record.get("status") != "approved":
        flags.append("registry_status_not_approved")
    if registry_record.get("entity_type") == "unreviewed":
        flags.append("registry_entity_type_unreviewed")
    if name_comparison == "name_difference_requires_review":
        flags.append("source_registry_name_difference")
    if proposal["source_id"] in SPECIAL_REVIEW_CODES:
        flags.append("territory_or_disputed_identity_manual_review")
    if iso.get("assignment_status") != "approved":
        flags.append("iso_assignment_not_approved")

    prior = history.get(proposal["source_id"], {})
    game_history = history.get(f"game_id:{proposal['proposed_game_id']}", {})
    mappings = list(prior.get("source_mappings", [])) + [
        item for item in game_history.get("source_mappings", [])
        if item not in prior.get("source_mappings", [])
    ]
    identity_decision = prior.get("prior_identity_decision") or game_history.get("prior_identity_decision") or {}
    for item in mappings:
        mapped_game_id = item.get("mapped_game_id")
        item["proposal_game_id_match"] = (
            "same_game_id" if mapped_game_id == proposal["proposed_game_id"]
            else "different_game_id" if mapped_game_id else "no_game_id_in_mapping"
        )
    if identity_decision:
        identity_decision = {
            **identity_decision,
            "proposal_game_id_match": (
                "same_game_id" if identity_decision.get("game_id") == proposal["proposed_game_id"]
                else "different_game_id"
            ),
        }
    if any(item["proposal_game_id_match"] == "different_game_id" for item in mappings):
        flags.append("existing_project_crosswalk_targets_different_game_id")
    return {
        **proposal,
        "existing_project_source_mappings": compact_json(mappings),
        "prior_project_identity_decision": compact_json(identity_decision),
        "registry_aliases_en": "; ".join(aliases),
        "registry_previous_source_ids": "; ".join(source.get("previous_source_ids") or []),
        "registry_iso_alpha2": iso.get("alpha2") or "",
        "registry_iso_alpha3": iso.get("alpha3") or "",
        "registry_iso_assignment_status": iso.get("assignment_status") or "",
        "registry_regions": "; ".join(registry_record.get("regions") or []),
        "registry_geometry_key": registry_record.get("geometry_key") or "",
        "name_comparison": name_comparison,
        "manual_review_flags": ";".join(flags),
        "owner_decision": "",
        "approved_game_id": "",
        "owner_rationale": "",
        "owner_evidence_reference": "",
    }


def build_owner_review(input_dir: Path, registry_path: Path, history_paths: dict[str, Path] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest_path = input_dir / "review_manifest.json"
    proposals_path = input_dir / "identity_proposals.csv"
    unresolved_path = input_dir / "unresolved_identities.csv"
    if not all(path.is_file() for path in (manifest_path, proposals_path, unresolved_path, registry_path)):
        raise OwnerReviewError("Original review manifest, proposals, unresolved identities and registry are required")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("field_id") != 16 or manifest.get("indicator_code") != "NGDPDPC":
        raise OwnerReviewError("Input package is not the field-16 NGDPDPC review")
    if manifest.get("database_written") is not False or manifest.get("approval_created") is not False:
        raise OwnerReviewError("Input package does not prove prepare-only status")
    checks = (
        (proposals_path, "identity_proposals_sha256", "proposal checksum"),
        (unresolved_path, "unresolved_identities_sha256", "unresolved checksum"),
        (registry_path, "registry_sha256", "registry checksum"),
    )
    for path, key, label in checks:
        if sha256(path) != manifest.get(key):
            raise OwnerReviewError(f"Original {label} mismatch")

    proposals = read_csv(proposals_path)
    history, history_fingerprints = load_identity_history(history_paths or DEFAULT_HISTORY_FILES)
    if len(proposals) != EXPECTED_CODES or len({row["source_id"] for row in proposals}) != EXPECTED_CODES:
        raise OwnerReviewError("Expected exactly 195 unique source identity proposals")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    records = registry.get("records")
    if not isinstance(records, list) or len(records) != 242:
        raise OwnerReviewError("Expected exactly 242 identity registry records")
    by_game_id = {str(record.get("game_id", "")): record for record in records}
    if len(by_game_id) != len(records):
        raise OwnerReviewError("Registry contains duplicate game IDs")
    by_source: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        source = record.get("source") or {}
        source_id = source.get("current_source_id")
        if isinstance(source_id, str) and source_id:
            by_source.setdefault(source_id, []).append(record)

    rows = []
    for proposal in proposals:
        record = by_game_id.get(proposal["proposed_game_id"])
        if record is None:
            raise OwnerReviewError(f"Proposed game ID is absent from registry: {proposal['proposed_game_id']}")
        source = record.get("source") or {}
        if source.get("current_source_id") != proposal["source_id"]:
            raise OwnerReviewError(f"Source/game identity mismatch for {proposal['source_id']}")
        if len(by_source.get(proposal["source_id"], [])) != 1:
            raise OwnerReviewError(f"Registry source ID is not unique for {proposal['source_id']}")
        if proposal.get("proposal_basis") != "exact_unique_registry_current_source_id_match_only":
            raise OwnerReviewError(f"Unexpected proposal basis for {proposal['source_id']}")
        if proposal.get("decision") != "PENDING" or proposal.get("approved_game_id") != "-":
            raise OwnerReviewError("Original proposal decisions are not in their untouched pending state")
        rows.append(enrich_proposal(proposal, record, history))

    rows.sort(key=lambda row: row["source_id"])
    return rows, {
        "schema_version": 1,
        "field_id": 16,
        "indicator_code": "NGDPDPC",
        "source_release": manifest.get("source_release"),
        "input_review_directory": manifest.get("review_directory"),
        "input_manifest_sha256": sha256(manifest_path),
        "input_proposals_sha256": sha256(proposals_path),
        "registry_path": manifest.get("registry_path"),
        "registry_sha256": sha256(registry_path),
        "identity_history_files": {key: {"path": str(path), "sha256": history_fingerprints[key]} for key, path in (history_paths or DEFAULT_HISTORY_FILES).items()},
        "identity_history_policy": "source-scoped review evidence only; approval scope is displayed and never promoted to IMF field-16 approval",
        "proposal_count": len(rows),
        "batch_sizes": [sum(row["batch"] == f"{n:02d}" for row in rows) for n in range(1, 11)],
        "name_comparison_counts": {
            key: sum(row["name_comparison"] == key for row in rows)
            for key in ("exact_normalized_match", "registry_alias_match", "name_difference_requires_review")
        },
        "existing_project_mapping_rows": sum(bool(row["existing_project_source_mappings"]) for row in rows),
        "prior_identity_decision_rows": sum(bool(row["prior_project_identity_decision"]) for row in rows),
        "crosswalk_game_id_conflict_rows": sum("existing_project_crosswalk_targets_different_game_id" in row["manual_review_flags"] for row in rows),
        "manual_review_flag_counts": {
            key: sum(key in row["manual_review_flags"].split(";") for row in rows)
            for key in (
                "registry_status_not_approved",
                "registry_entity_type_unreviewed",
                "source_registry_name_difference",
                "territory_or_disputed_identity_manual_review",
                "iso_assignment_not_approved",
            )
        },
        "decision_vocabulary": ["APPROVE", "REJECT", "HOLD"],
        "approval_created": False,
        "database_written": False,
    }


def write_owner_review(rows: list[dict[str, Any]], metadata: dict[str, Any], output_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output_root / stamp
    suffix = 1
    while target.exists():
        target = output_root / f"{stamp}-{suffix}"
        suffix += 1
    target.mkdir(parents=True, exist_ok=False)
    write_csv(target / "owner_review_baseline.csv", rows)
    write_csv(target / "owner_review.csv", rows)
    metadata["review_directory"] = target.relative_to(ROOT).as_posix()
    metadata["owner_review_baseline_sha256"] = sha256(target / "owner_review_baseline.csv")
    metadata["owner_review_template_sha256"] = sha256(target / "owner_review.csv")
    (target / "owner_review_manifest.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def validate_owner_decisions(review_dir: Path) -> dict[str, Any]:
    manifest_path = review_dir / "owner_review_manifest.json"
    review_path = review_dir / "owner_review.csv"
    baseline_path = review_dir / "owner_review_baseline.csv"
    if not manifest_path.is_file() or not review_path.is_file() or not baseline_path.is_file():
        raise OwnerReviewError("Owner-review manifest, editable CSV and immutable baseline are required")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("field_id") != 16 or manifest.get("approval_created") is not False:
        raise OwnerReviewError("Owner-review manifest is not a prepare-only field-16 package")
    if sha256(baseline_path) != manifest.get("owner_review_baseline_sha256"):
        raise OwnerReviewError("Immutable owner-review baseline checksum mismatch")
    rows = read_csv(review_path)
    baseline = read_csv(baseline_path)
    if len(rows) != EXPECTED_CODES or len({row["source_id"] for row in rows}) != EXPECTED_CODES:
        raise OwnerReviewError("Owner decisions must cover exactly 195 unique source identities")
    decision_fields = {"owner_decision", "approved_game_id", "owner_rationale", "owner_evidence_reference"}
    baseline_by_source = {row["source_id"]: row for row in baseline}
    if set(baseline_by_source) != {row["source_id"] for row in rows}:
        raise OwnerReviewError("Owner-review source identity set differs from the immutable baseline")
    for row in rows:
        original = baseline_by_source[row["source_id"]]
        if any(row.get(key, "") != value for key, value in original.items() if key not in decision_fields):
            raise OwnerReviewError(f"Immutable identity evidence changed for {row['source_id']}")
    decisions = []
    for row in rows:
        decision = row.get("owner_decision", "").strip().upper()
        rationale = row.get("owner_rationale", "").strip()
        evidence = row.get("owner_evidence_reference", "").strip()
        approved_game_id = row.get("approved_game_id", "").strip()
        if decision not in {"APPROVE", "REJECT", "HOLD"}:
            raise OwnerReviewError(f"Missing or invalid owner decision for {row.get('source_id')}")
        if not rationale:
            raise OwnerReviewError(f"Owner rationale is required for {row.get('source_id')}")
        if decision == "APPROVE":
            if approved_game_id != row.get("proposed_game_id"):
                raise OwnerReviewError(f"APPROVE must name the exact proposed game ID for {row.get('source_id')}")
            if not evidence:
                raise OwnerReviewError(f"APPROVE requires an evidence reference for {row.get('source_id')}")
        elif approved_game_id:
            raise OwnerReviewError(f"REJECT/HOLD must not set approved_game_id for {row.get('source_id')}")
        decisions.append({
            "source_id": row["source_id"],
            "series_code": row["series_code"],
            "proposed_game_id": row["proposed_game_id"],
            "batch": row["batch"],
            "decision": decision,
            "approved_game_id": approved_game_id or None,
            "rationale": rationale,
            "evidence_reference": evidence or None,
        })
    counts = {key: sum(item["decision"] == key for item in decisions) for key in ("APPROVE", "REJECT", "HOLD")}
    return {
        "schema_version": 1,
        "record_type": "field16_owner_decision_proposal_not_approval",
        "field_id": 16,
        "indicator_code": "NGDPDPC",
        "source_release": manifest.get("source_release"),
        "owner_review_directory": manifest.get("review_directory"),
        "owner_review_manifest_sha256": sha256(manifest_path),
        "owner_review_csv_sha256": sha256(review_path),
        "owner_review_baseline_sha256": manifest.get("owner_review_baseline_sha256"),
        "decision_counts": counts,
        "decisions": decisions,
        "approval_created": False,
        "database_written": False,
        "next_gate": "separate owner approval record and guarded application design; no automatic application",
    }


def write_decision_proposal(payload: dict[str, Any], output_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output_root / stamp
    suffix = 1
    while target.exists():
        target = output_root / f"{stamp}-{suffix}"
        suffix += 1
    target.mkdir(parents=True, exist_ok=False)
    path = target / "owner_decision_proposal.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    build.add_argument("--identity-registry", type=Path, default=ROOT / "config/country_identity_registry.json")
    build.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    build.add_argument("--wdi-crosswalk", type=Path, default=DEFAULT_HISTORY_FILES["wdi"])
    build.add_argument("--wpp-crosswalk", type=Path, default=DEFAULT_HISTORY_FILES["wpp"])
    build.add_argument("--icp-crosswalk", type=Path, default=DEFAULT_HISTORY_FILES["icp"])
    build.add_argument("--imf-weo-crosswalk", type=Path, default=DEFAULT_HISTORY_FILES["imf_weo"])
    build.add_argument("--identity-edge-cases", type=Path, default=DEFAULT_HISTORY_FILES["edge_cases"])
    validate = sub.add_parser("validate")
    validate.add_argument("--review-dir", type=Path, required=True)
    validate.add_argument("--output-root", type=Path, default=ROOT / "reports/sources/imf-weo-field16-owner-decision-proposals")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            history_paths = {"wdi": args.wdi_crosswalk, "wpp": args.wpp_crosswalk, "icp": args.icp_crosswalk, "imf_weo": args.imf_weo_crosswalk, "edge_cases": args.identity_edge_cases}
            rows, metadata = build_owner_review(args.input_dir, args.identity_registry, history_paths)
            target = write_owner_review(rows, metadata, args.output_root)
            print(json.dumps({**metadata, "review_directory": str(target)}, ensure_ascii=False, indent=2))
        else:
            payload = validate_owner_decisions(args.review_dir)
            path = write_decision_proposal(payload, args.output_root)
            print(json.dumps({
                "decision_proposal": str(path),
                "decision_counts": payload["decision_counts"],
                "approval_created": False,
                "database_written": False,
            }, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, OwnerReviewError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
