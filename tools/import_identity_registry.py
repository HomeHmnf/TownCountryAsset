"""Import the persistent identity registry into the local canonical SQLite database."""

from __future__ import annotations

import argparse
import json

from tools.database.application_approval import ApplicationApprovalError, approve_application
from tools.database.connection import DEFAULT_DATABASE_PATH, connect_database
from tools.database.identity_import import (
    DEFAULT_CANDIDATE_DIR,
    DEFAULT_REGISTRY_PATH,
    IdentityImportError,
    build_identity_application_artifact,
    import_identity_registry,
)
from tools.database.schema import apply_migrations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import identity registry and source provenance into canonical SQLite."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE_PATH))
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY_PATH))
    parser.add_argument("--candidate-dir", default=str(DEFAULT_CANDIDATE_DIR))
    approval = parser.add_mutually_exclusive_group(required=True)
    approval.add_argument("--approval-id", help="Previously approved identity application ID")
    approval.add_argument(
        "--approve-and-apply", action="store_true",
        help="Create approval for these exact identity inputs and immediately apply them",
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
            artifact = build_identity_application_artifact(args.registry, args.candidate_dir)
            approval_id = "identity-registry-" + artifact["artifact_sha256"][:20]
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
        result = import_identity_registry(
            args.database, args.registry, args.candidate_dir, approval_id=approval_id
        )
    except (OSError, ValueError, ApplicationApprovalError, IdentityImportError) as exc:
        print(f"Identity registry import failed: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.approve_and_apply:
        print(f"Approval created and applied: {approval_id}")
    print("Identity registry import completed; database integrity and foreign-key checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
