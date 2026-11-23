"""Import Natural Earth country attributes and geometries into canonical SQLite."""

from __future__ import annotations

import argparse
import json
import sqlite3

from tools.database.application_approval import ApplicationApprovalError, approve_application
from tools.database.connection import DEFAULT_DATABASE_PATH, connect_database
from tools.database.country_data_import import (
    DEFAULT_CANDIDATE_DIR,
    CountryDataImportError,
    build_country_data_application_artifact,
    import_country_data,
)
from tools.database.schema import MigrationError, apply_migrations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import Natural Earth source attributes and game-ID geometry profiles into canonical SQLite."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE_PATH))
    parser.add_argument("--candidate-dir", default=str(DEFAULT_CANDIDATE_DIR))
    approval = parser.add_mutually_exclusive_group(required=True)
    approval.add_argument("--approval-id", help="Previously approved country-data application ID")
    approval.add_argument(
        "--approve-and-apply", action="store_true",
        help="Create approval for these exact candidate files and immediately apply them",
    )
    parser.add_argument("--actor", help="Reviewer identity; required with --approve-and-apply")
    parser.add_argument("--note", help="Approval rationale; required with --approve-and-apply")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        approval_id = args.approval_id
        if args.approve_and_apply:
            if not args.actor or not args.actor.strip():
                raise ApplicationApprovalError("--approve-and-apply requires --actor")
            if not args.note or not args.note.strip():
                raise ApplicationApprovalError("--approve-and-apply requires --note")
            artifact = build_country_data_application_artifact(args.candidate_dir)
            approval_id = "country-data-" + artifact["artifact_sha256"][:20]
            connection = connect_database(args.database)
            try:
                apply_migrations(connection)
                approve_application(
                    connection, approval_id=approval_id, artifact=artifact,
                    actor=args.actor, note=args.note,
                )
                print(f"Approval created for validated inputs: {approval_id}")
            finally:
                connection.close()
        result = import_country_data(
            args.database, args.candidate_dir, approval_id=approval_id
        )
    except (OSError, ValueError, sqlite3.Error, MigrationError, ApplicationApprovalError, CountryDataImportError) as exc:
        print(f"Country data import failed: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.approve_and_apply:
        print(f"Approval created and applied: {approval_id}")
    print("Country metadata and geometry import completed; database integrity and foreign-key checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
