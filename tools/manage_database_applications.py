"""Create, approve, reject and inspect canonical database application proposals."""
from __future__ import annotations

import argparse
import json
from tools.database.application_approval import (
    ApplicationApprovalError,
    decide_application,
    propose_application,
)
from tools.database.connection import DEFAULT_DATABASE_PATH, connect_database
from tools.database.schema import MigrationError, apply_migrations
from tools.database.statistics_import import (
    StatisticsImportError, build_wp1_5_application_artifact,
)
from tools.database.country_data_import import (
    CountryDataImportError, DEFAULT_CANDIDATE_DIR as DEFAULT_COUNTRY_CANDIDATE_DIR,
    build_country_data_application_artifact,
)
from tools.database.review_data_import import (
    DEFAULT_REGISTRY as DEFAULT_REVIEW_REGISTRY,
    DEFAULT_TAXONOMY, DEFAULT_FLAGS, ReviewDataImportError,
    build_review_application_artifact,
)
from tools.database.identity_import import (
    DEFAULT_REGISTRY_PATH, DEFAULT_CANDIDATE_DIR, IdentityImportError,
    build_identity_application_artifact,
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
    country = commands.add_parser("propose-country-data", help="Fingerprint country attributes and geometry import")
    country.add_argument("--approval-id", required=True)
    country.add_argument("--candidate-dir", default=str(DEFAULT_COUNTRY_CANDIDATE_DIR))
    review = commands.add_parser("propose-review-data", help="Fingerprint ISO, localization, entity and flag review import")
    review.add_argument("--approval-id", required=True)
    review.add_argument("--registry", default=str(DEFAULT_REVIEW_REGISTRY))
    review.add_argument("--iso-reference", required=True)
    review.add_argument("--iso-provenance", required=True)
    review.add_argument("--iso-proposals", required=True)
    review.add_argument("--persian-candidates", required=True)
    review.add_argument("--persian-provenance", required=True)
    review.add_argument("--entity-taxonomy", default=str(DEFAULT_TAXONOMY))
    review.add_argument("--flag-mapping", default=str(DEFAULT_FLAGS))
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
        elif args.command == "propose-country-data":
            artifact = build_country_data_application_artifact(args.candidate_dir)
        elif args.command == "propose-review-data":
            artifact = build_review_application_artifact(
                args.registry, args.iso_reference, args.iso_provenance, args.iso_proposals,
                args.persian_candidates, args.persian_provenance, args.entity_taxonomy,
                args.flag_mapping,
            )
        if args.command in {"propose-wp1-5", "propose-identity", "propose-country-data", "propose-review-data"}:
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
    except (ApplicationApprovalError, CountryDataImportError, IdentityImportError, ReviewDataImportError, StatisticsImportError, MigrationError, OSError, ValueError) as exc:
        if connection.in_transaction:
            connection.rollback()
        print(f"Database application {args.command} failed: {exc}")
        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
