"""Import one normalized WP1.5 source dataset into canonical SQLite."""
from __future__ import annotations

import argparse
import json

from tools.database.application_approval import (
    ApplicationApprovalError,
    approve_application,
)
from tools.database.connection import DEFAULT_DATABASE_PATH, connect_database
from tools.database.statistics_import import (
    StatisticsImportError,
    build_wp1_5_application_artifact,
    import_wp1_5_dataset,
    validate_wp1_5_dataset,
)
from tools.database.schema import MigrationError, apply_migrations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import normalized WP1.5 observations with source manifest and explicit country crosswalk."
    )
    parser.add_argument("--observations", required=True, help="Normalized WP1.5 observations JSON")
    parser.add_argument("--crosswalk", required=True, help="Explicit provider-ID to game_id crosswalk JSON")
    parser.add_argument("--manifest", required=True, help="Immutable source acquisition manifest JSON")
    parser.add_argument("--database", help="Canonical SQLite database path")
    parser.add_argument("--config", help="WP1.5 field contract JSON")
    approval = parser.add_mutually_exclusive_group(required=True)
    approval.add_argument("--approval-id", help="Previously approved application ID")
    approval.add_argument(
        "--approve-and-apply", action="store_true",
        help="Create an approval for these exact inputs and immediately apply them",
    )
    parser.add_argument("--actor", help="Reviewer identity; required with --approve-and-apply")
    parser.add_argument("--note", help="Approval rationale; required with --approve-and-apply")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    database_path = args.database or DEFAULT_DATABASE_PATH
    config_path = args.config
    kwargs = {
        "observations_path": args.observations,
        "crosswalk_path": args.crosswalk,
        "manifest_path": args.manifest,
        "database_path": database_path,
    }
    if config_path:
        kwargs["config_path"] = config_path

    try:
        approval_id = args.approval_id
        if args.approve_and_apply:
            if not args.actor or not args.actor.strip():
                raise ApplicationApprovalError("--approve-and-apply requires --actor")
            if not args.note or not args.note.strip():
                raise ApplicationApprovalError("--approve-and-apply requires --note")
            validation_kwargs = {
                "observations_path": args.observations,
                "crosswalk_path": args.crosswalk,
                "manifest_path": args.manifest,
            }
            if config_path:
                validation_kwargs["config_path"] = config_path
            validation = validate_wp1_5_dataset(**validation_kwargs)
            artifact = validation["application_artifact"]
            approval_id = "wp1-5-" + artifact["artifact_sha256"][:20]
            connection = connect_database(database_path)
            try:
                apply_migrations(connection)
                approve_application(
                    connection,
                    approval_id=approval_id,
                    artifact=artifact,
                    actor=args.actor,
                    note=args.note,
                )
            finally:
                connection.close()
            print(f"Approval created for validated inputs: {approval_id}")

        result = import_wp1_5_dataset(**kwargs, approval_id=approval_id)
    except (
        StatisticsImportError, MigrationError, ApplicationApprovalError,
        OSError, ValueError,
    ) as exc:
        print(f"WP1.5 import failed: {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.approve_and_apply:
        print(f"Approval created and applied: {approval_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
