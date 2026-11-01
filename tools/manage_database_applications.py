"""Create, approve, reject and inspect canonical database application proposals."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.database.application_approval import (
    ApplicationApprovalError,
    build_application_artifact,
    decide_application,
    propose_application,
)
from tools.database.connection import DEFAULT_DATABASE_PATH, connect_database
from tools.database.schema import MigrationError, apply_migrations
from tools.database.statistics_import import build_wp1_5_application_artifact
from tools.database.identity_import import (
    DEFAULT_REGISTRY_PATH, DEFAULT_CANDIDATE_DIR, build_identity_application_artifact,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(DEFAULT_DATABASE_PATH))
    commands = parser.add_subparsers(dest="command", required=True)
    propose = commands.add_parser("propose-wp1-5", help="Fingerprint and register a WP1.5 import proposal")
    propose.add_argument("--approval-id", required=True)
    propose.add_argument("--observations", required=True)
    propose.add_argument("--crosswalk", required=True)
    propose.add_argument("--manifest", required=True)
    propose.add_argument("--config")
    identity = commands.add_parser("propose-identity", help="Fingerprint and register an identity-registry import proposal")
    identity.add_argument("--approval-id", required=True)
    identity.add_argument("--registry", default=str(DEFAULT_REGISTRY_PATH))
    identity.add_argument("--candidate-dir", default=str(DEFAULT_CANDIDATE_DIR))
    for name in ("approve", "reject"):
        decision = commands.add_parser(name, help=f"Record explicit {name} decision")
        decision.add_argument("--approval-id", required=True)
        decision.add_argument("--actor", required=True)
        decision.add_argument("--note")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    connection = connect_database(args.database)
    try:
        apply_migrations(connection)
        if args.command == "propose-wp1-5":
            kwargs = {
                "observations_path": args.observations,
                "crosswalk_path": args.crosswalk,
                "manifest_path": args.manifest,
            }
            if args.config:
                kwargs["config_path"] = args.config
            artifact = build_wp1_5_application_artifact(**kwargs)
        elif args.command == "propose-identity":
            artifact = build_identity_application_artifact(args.registry, args.candidate_dir)
        if args.command in {"propose-wp1-5", "propose-identity"}:
            connection.execute("BEGIN IMMEDIATE")
            propose_application(connection, approval_id=args.approval_id, artifact=artifact)
            connection.commit()
            print(json.dumps({
                "approval_id": args.approval_id,
                "status": "pending",
                "domain": artifact["domain"],
                "artifact_sha256": artifact["artifact_sha256"],
                "inputs": artifact["inputs"],
                "metadata": artifact["metadata"],
            }, ensure_ascii=False, indent=2))
        else:
            connection.execute("BEGIN IMMEDIATE")
            decide_application(
                connection,
                approval_id=args.approval_id,
                decision="approved" if args.command == "approve" else "rejected",
                actor=args.actor,
                note=args.note,
            )
            connection.commit()
            print(json.dumps({
                "approval_id": args.approval_id,
                "status": "approved" if args.command == "approve" else "rejected",
                "actor": args.actor,
            }, ensure_ascii=False, indent=2))
        return 0
    except (ApplicationApprovalError, MigrationError, OSError, ValueError) as exc:
        if connection.in_transaction:
            connection.rollback()
        print(f"Database application {args.command} failed: {exc}")
        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
