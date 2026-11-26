#!/usr/bin/env python3
"""Bulk owner-approve all validated IMF WEO field-15 proposals and apply them.

Dry-run is the default. Preparation requires --prepare-only and application requires --apply, each with --confirm-all-proposals,
an identified owner, and a decision note. The original review Markdown is
never modified; a fingerprinted, generated approval copy is retained.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.manage_imf_weo_field15_review import (
    CANDIDATE_ROOT,
    HEADER,
    REVIEW,
    ReviewError,
    apply_review,
    cell,
    parse_review,
    validate_fingerprints,
    validate_review,
    validate_review_against_source_register,
)
from tools.database.application_approval import ApplicationApprovalError
from tools.database.imf_weo_import import WEOImportError
from tools.database.connection import DEFAULT_DATABASE_PATH
from tools.database.project_connection import DEFAULT_PROJECT_DATABASE_PATH


def build_bulk_approved_document(document: str, *, actor: str, note: str, approval_date: str) -> tuple[str, int]:
    """Create an immutable copy recording one explicit owner decision for all proposals."""
    if not actor.strip() or len(note.strip()) < 20:
        raise ReviewError("A non-empty owner actor and decision note of at least 20 characters are required")
    try:
        date.fromisoformat(approval_date)
    except ValueError as exc:
        raise ReviewError("Approval date must be YYYY-MM-DD") from exc

    lines = document.splitlines()
    in_table = False
    proposal_count = 0
    rebuilt: list[str] = []
    for line in lines:
        if line == HEADER:
            in_table = True
            rebuilt.append(line)
            continue
        if in_table and line.startswith("|"):
            if line.startswith("|---"):
                rebuilt.append(line)
                continue
            parts = [part.strip().replace("\\|", "|") for part in line.strip().strip("|").split("|")]
            if len(parts) != 13:
                raise ReviewError("Malformed field-15 review table row; refusing bulk approval")
            source_id = parts[1]
            if source_id != "KOS":
                if parts[5] in {"", "-"} or not parts[5].startswith("tc_"):
                    raise ReviewError(f"{source_id}: proposal has no persistent target game_id")
                parts[10] = "APPROVE"
                parts[11] = parts[5]
                parts[12] = note.strip()
                proposal_count += 1
            rebuilt.append("| " + " | ".join(cell(part) for part in parts) + " |")
            continue
        if in_table:
            in_table = False
        rebuilt.append(line)

    if proposal_count != 195:
        raise ReviewError(f"Expected exactly 195 proposals for bulk approval; found {proposal_count}")
    result = "\n".join(rebuilt) + "\n"
    replacements = {
        "Owner actor": actor.strip(),
        "Approval date (YYYY-MM-DD)": approval_date,
        "Approval statement": (
            "I explicitly approve all 195 source-derived IMF WEO October 2026 NGDPD identity proposals "
            "for WP1.5 field 15 only. " + note.strip()
        ),
    }
    for label, value in replacements.items():
        pattern = re.compile(r"(?m)^- " + re.escape(label) + r": .*?$")
        result, count = pattern.subn("- " + label + ": " + value, result, count=1)
        if count != 1:
            raise ReviewError(f"Could not set owner approval declaration: {label}")
    return result, proposal_count


def run(*, review: Path, actor: str | None, note: str | None, apply: bool,
        prepare_only: bool, confirm_all: bool, database: Path, project_database: Path) -> dict:
    meta, rows, document = parse_review(review, False)
    validate_fingerprints(meta)
    validate_review_against_source_register(meta, rows, document)
    pending = [row for row in rows if row["decision"].upper() == "PENDING"]
    if len(pending) != 195 or len(rows) != 195:
        raise ReviewError(
            f"Bulk approval expects the untouched 195-pending-proposal review; "
            f"found {len(pending)} pending proposals across {len(rows)} rows"
        )
    if apply and prepare_only:
        raise ReviewError("Choose either --apply or --prepare-only, not both")
    if not apply and not prepare_only:
        return {
            "status": "dry_run",
            "proposal_rows_to_approve": len(pending),
            "existing_wbg_mapping_reused": True,
            "existing_kos_mapping_reused": True,
            "aggregate_exclusions_reused": 13,
            "aggregate_populated_values_excluded": 665,
            "kos_mapping_approved_and_reused": True,
            "fingerprints_valid": True,
            "database_written": False,
            "approval_created": False,
            "next_step": "Run with --prepare-only --confirm-all-proposals --actor and --note to build and preflight the candidate without database writes.",
        }
    if not confirm_all:
        raise ReviewError("--apply/--prepare-only requires --confirm-all-proposals as explicit owner authorization")
    if not actor or not note:
        raise ReviewError("--apply/--prepare-only requires --actor and --note")
    approval_date = date.today().isoformat()
    approved_document, count = build_bulk_approved_document(
        document, actor=actor, note=note, approval_date=approval_date
    )
    digest = hashlib.sha256(approved_document.encode("utf-8")).hexdigest()
    output = CANDIDATE_ROOT / "bulk-owner-approvals" / f"field_15_bulk_approval_{digest[:16]}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if output.read_text(encoding="utf-8") != approved_document:
            raise ReviewError("Existing bulk approval artifact differs; refusing overwrite")
    else:
        output.write_text(approved_document, encoding="utf-8")
    validation = validate_review(output, True)
    result = apply_review(output, actor, database, project_database, prepare_only=prepare_only)
    return {
        "status": "prepared" if prepare_only else "applied",
        "bulk_approved_proposals": count,
        "owner_actor": actor,
        "owner_approval_date": approval_date,
        "decision_note": note,
        "generated_approval_review": output.resolve().relative_to(ROOT.resolve()).as_posix(),
        "review_validation": validation,
        "application": result,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=REVIEW)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--project-database", type=Path, default=DEFAULT_PROJECT_DATABASE_PATH)
    parser.add_argument("--actor", help="Owner identity recorded in the approval ledger")
    parser.add_argument("--note", help="Owner decision rationale for approving the complete proposal set")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Create database approval and apply observations")
    mode.add_argument("--prepare-only", action="store_true", help="Build candidate and run read-only preflight; create no database approval or writes")
    parser.add_argument(
        "--confirm-all-proposals", action="store_true",
        help="Explicitly attest that all 195 generated identity proposals are approved for field 15",
    )
    args = parser.parse_args(argv)
    try:
        result = run(
            review=args.review, actor=args.actor, note=args.note, apply=args.apply,
            prepare_only=args.prepare_only, confirm_all=args.confirm_all_proposals, database=args.database,
            project_database=args.project_database,
        )
    except (OSError, ValueError, ReviewError, WEOImportError, ApplicationApprovalError, sqlite3.Error, csv.Error, json.JSONDecodeError) as exc:
        parser.exit(1, f"IMF WEO field-15 bulk approval failed: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["status"] == "dry_run":
        print("Dry run only. No approval or database changes were made.")
    elif result["status"] == "prepared":
        print("Candidate prepared and read-only preflight completed. No database approval or database writes were made.")
    else:
        print("Bulk owner approval and field-15 application completed; inspect the verification report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
