#!/usr/bin/env python3
"""Generate, validate, and explicitly apply the owner-reviewed IMF WEO field-15 package."""
from __future__ import annotations
import argparse, csv, hashlib, io, json, re, sqlite3, sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.build_imf_weo_historical_candidate import build_candidate
from tools.database.connection import DEFAULT_DATABASE_PATH
from tools.database.imf_weo_import import WEOImportError, apply_application, decide_application_for_weo, prepare_application
from tools.database.project_connection import DEFAULT_PROJECT_DATABASE_PATH

AUTO = ROOT / "reports/sources/imf-weo-field15-identity-review/automatic/20261126T101015Z"
REVIEW = ROOT / "reports/sources/imf-weo-field15-identity-review/field_15_owner_review.md"
CANDIDATE_ROOT = ROOT / "reports/sources/imf-weo-field15-reviewed-candidate"
DERIVED_CROSSWALK = CANDIDATE_ROOT / "reviewed_imf_weo_crosswalk.json"
RAW = ROOT / "raw_data/sources/imf_weo/october_2026/dataset_2026-11-02T07_37_00.482492506Z_DEFAULT_INTEGRATION_IMF.RES_WEO_9.0.0.csv"
PDF = ROOT / "raw_data/sources/imf_weo/october_2026/October 2026 WEO Database Appendix.pdf"
TEXT = ROOT / "derived_data/pdf_text/sources/imf_weo/october_2026/October 2026 WEO Database Appendix.pdf.txt"
TEXT_META = ROOT / "derived_data/pdf_text/sources/imf_weo/october_2026/October 2026 WEO Database Appendix.pdf.txt.json"
M49 = ROOT / "raw_data/sources/un_m49/country_area_overview_html/2026-10-current/m49-country-area-overview.html"
M49_MANIFEST = ROOT / "data_manifests/sources/un_m49/country_area_overview_html/2026-10-current.json"
REGISTRY = ROOT / "config/country_identity_registry.json"
CROSSWALK = ROOT / "data/manual/source_crosswalks/imf_weo.json"
ACQUISITION = ROOT / "docs/data-sources/imf-weo-october-2026-manual-acquisition.md"
PRIOR_DECISIONS_DOC = ROOT / "docs/data-sources/wp1-5-review-approval-application-workflow.md"
MIGRATION = ROOT / "migrations/008_imf_weo_historical_observations.sql"
RELEASE = "October 2026 / IMF.RES_WEO_9.0.0"
META_OPEN = "<!-- REVIEW-METADATA-JSON"
META_CLOSE = "REVIEW-METADATA-JSON -->"
HEADER = "| Batch | Source ID | Source name | Series | Populated years (count / range) | Proposed game_id | Registry name | M49 | Evidence | Proposal basis | Decision | Approved game_id | Owner rationale |"
SEPARATOR = "|---:|---|---|---|---|---|---|---|---|---|---|---|---|"

class ReviewError(RuntimeError):
    pass

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def fingerprint_inputs(auto: Path) -> dict[str, dict[str, Any]]:
    files = {
        "weo_csv": RAW, "imf_appendix_pdf": PDF, "imf_appendix_text": TEXT,
        "imf_appendix_text_metadata": TEXT_META, "un_m49_html": M49,
        "un_m49_manifest": M49_MANIFEST,
        "m49_faq_snapshot": auto / "m49_faq_snapshot.html",
        "m49_faq_provenance": auto / "m49_faq_provenance.json",
        "identity_registry": REGISTRY, "approved_wbg_crosswalk": CROSSWALK,
        "automatic_summary": auto / "summary.json",
        "automatic_inventory": auto / "field_15_identity_inventory.csv",
        "automatic_identity_exceptions": auto / "identity_exceptions.csv",
        "automatic_final_register": auto / "field_15_identity_review_register_final.csv",
        "automatic_exclusion_register": auto / "field_15_exclusion_register.csv",
        "manual_acquisition_record": ACQUISITION, "prior_decisions_doc": PRIOR_DECISIONS_DOC,
        "import_migration": MIGRATION,
    }
    result = {}
    for key, path in files.items():
        if not path.is_file():
            raise ReviewError(f"Required source evidence missing: {path}")
        result[key] = {"path": relative(path), "sha256": sha(path), "byte_count": path.stat().st_size}
    return result

def cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()

def extract_metadata(document: str) -> dict[str, Any]:
    start = document.find(META_OPEN)
    if start < 0:
        raise ReviewError("Review metadata block is missing")
    start += len(META_OPEN)
    end = document.find(META_CLOSE, start)
    if end < 0:
        raise ReviewError("Review metadata block terminator is missing")
    try:
        data = json.loads(document[start:end].strip())
    except json.JSONDecodeError as exc:
        raise ReviewError(f"Invalid review metadata JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ReviewError("Review metadata must be a JSON object")
    return data

def generate_review(auto: Path, output: Path) -> dict[str, Any]:
    final = auto / "field_15_identity_review_register_final.csv"
    exclusions = auto / "field_15_exclusion_register.csv"
    summary_path = auto / "summary.json"
    if not all(p.is_file() for p in (final, exclusions, summary_path)):
        raise ReviewError("Automatic source-derived review package is incomplete")
    rows, aggregates = read_csv(final), read_csv(exclusions)
    if len(rows) != 196 or sum(bool(r["reviewed_proposed_game_id"]) for r in rows) != 195:
        raise ReviewError("Expected 195 proposal rows plus the KOS hold")
    if len(aggregates) != 13 or sum(int(r["populated_year_count"]) for r in aggregates) != 665:
        raise ReviewError("Expected 13 previously approved aggregate exclusions / 665 values")
    if any(r.get("disposition") != "excluded" or not r.get("rationale", "").strip() for r in aggregates):
        raise ReviewError("Aggregate source register must preserve an explicit excluded disposition and rationale for every series")
    registry_doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry = {r.get("game_id"): r for r in registry_doc.get("records", []) if isinstance(r, dict)}
    metadata = {
        "schema_version": 1, "field_id": 15, "indicator_code": "NGDPD",
        "source_release": "october_2026", "source_sha256": sha(RAW),
        "automatic_review_directory": relative(auto),
        "input_fingerprints": fingerprint_inputs(auto),
        "fixed_decisions": {
            "WBG": "Reuse existing owner-approved WBG to Palestine mapping; field 15 only.",
            "aggregates": "Reuse 13 owner-approved excluded dispositions; 665 populated values.",
            "KOS": "Preserve hold_for_evidence; no identity mapping.",
        },
    }
    lines = [
        "# IMF WEO October 2026 — field 15 / NGDPD owner review", "",
        "This is the single authoritative review document for all ten batches.", "",
        "- Scope: WP1.5 field 15 / NGDPD / IMF WEO October 2026 only.",
        "- 195 proposed mappings in ten batches (20 identities per batch, final batch 10 has 16).",
        "- Existing WBG approval, 13 aggregate exclusions and KOS hold are carried forward.",
        "- Every new identity requires an explicit owner decision and rationale.",
        "- APPROVE requires Approved game_id to equal Proposed game_id exactly.",
        "- EXCLUDE and HOLD require Approved game_id to be -.", "",
        "## Owner approval of the complete review", "",
        "- Owner actor: PENDING",
        "- Approval date (YYYY-MM-DD): PENDING",
        "- Approval statement: PENDING",
        "", "## Reused prior decisions", "",
        "### WBG — existing approved crosswalk", "",
        "- imf_weo / WBG / West Bank and Gaza maps to tc_50c420df8b2c4c6eaae47d795f9a1ea2 (Palestine).",
        "- Match method reviewed_manual; owner approval dated 2026-11-25; field 15 / NGDPD only.",
        "- The original manual crosswalk will not be modified.", "",
        "### Aggregate exclusions — existing owner decision", "",
        "| Source ID | Source name | Series | Populated values | Years | Disposition |",
        "|---|---|---|---:|---|---|",
    ]
    for r in aggregates:
        vals = [r["source_country_code"], r["source_country_name"], r["series_code"],
                r["populated_year_count"], f'{r["first_populated_year"]}–{r["last_populated_year"]}',
                "EXCLUDED — prior owner approval"]
        lines.append("| " + " | ".join(cell(v) for v in vals) + " |")
    lines += [
        "", "Total: 13 aggregate series and 665 populated annual values; excluded from country observations.",
        "", "### KOS — existing hold", "",
        "Keep KOS on HOLD with no target. The IMF source code / Appendix UVK discrepancy remains unresolved; M49 statistical-use code 412 does not resolve it.",
        "", "## New identity decisions — all ten batches", "", HEADER, SEPARATOR,
    ]
    proposal_index = 0
    for source_index, row in enumerate(rows):
        batch = source_index // 20 + 1
        if row["source_id"] == "KOS":
            years = f'{row["populated_year_count"]} ({row["first_populated_year"]}–{row["last_populated_year"]})'
            vals = [f"{batch:02d}", "KOS", row["source_name"], row["series_code"],
                    years, "-", "-", "-", row["independent_evidence_reference"], row["review_notes"],
                    "HOLD", "-", row["review_notes"]]
            lines.append("| " + " | ".join(cell(v) for v in vals) + " |")
            continue
        game_id = row["reviewed_proposed_game_id"]
        target = registry.get(game_id)
        if not target:
            raise ReviewError(f"Proposed target is absent from the canonical registry: {row['source_id']}")
        registry_name = (target.get("names") or {}).get("en", "")
        if registry_name != row["proposed_registry_name"]:
            raise ReviewError(f"Registry-name mismatch for {row['source_id']}")
        proposal_index += 1
        years = f'{row["populated_year_count"]} ({row["first_populated_year"]}–{row["last_populated_year"]})'
        vals = [
            f"{batch:02d}", row["source_id"], row["source_name"], row["series_code"],
            years, game_id, registry_name, row["un_m49_code"],
            row["independent_evidence_reference"], row["review_notes"], "PENDING", "-", "",
        ]
        lines.append("| " + " | ".join(cell(v) for v in vals) + " |")
    if proposal_index != 195:
        raise ReviewError(f"Expected 195 proposal rows, found {proposal_index}")
    lines += [
        "", "## Decision rules", "",
        "- APPROVE: review the identity evidence; enter APPROVE, copy the exact proposed game_id into Approved game_id, and write a specific rationale.",
        "- EXCLUDE: explicitly exclude this source economy from field 15; leave Approved game_id as - and explain why.",
        "- HOLD: keep unresolved; leave Approved game_id as - and explain the missing evidence.",
        "- A name resemblance alone is not sufficient. Do not modify global ISO/M49 assignments.",
        "- No PENDING decisions may remain when applying.", "",
        "## Immutable input fingerprints", "", META_OPEN,
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True), META_CLOSE, "",
        "Generation is review-only: no approval record, database write, registry change, or original crosswalk change.",
    ]
    output = output.resolve()
    if output.exists():
        raise ReviewError(f"Refusing to overwrite existing review file: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"review_file": relative(output), "proposal_rows": proposal_index,
            "aggregate_exclusions": len(aggregates), "aggregate_values": 665,
            "database_written": False, "approval_created": False}

def parse_review(path: Path, complete: bool) -> tuple[dict[str, Any], list[dict[str, str]], str]:
    document = path.read_text(encoding="utf-8")
    meta = extract_metadata(document)
    if meta.get("field_id") != 15 or meta.get("indicator_code") != "NGDPD":
        raise ReviewError("Wrong field or indicator scope")
    if not document.startswith("# IMF WEO October 2026 — field 15 / NGDPD owner review"):
        raise ReviewError("Unexpected review document")
    rows, inside = [], False
    fields = ("batch", "source_id", "source_name", "series_code", "populated_years",
              "proposed_game_id", "registry_name", "m49", "evidence", "proposal_basis",
              "decision", "approved_game_id", "rationale")
    for line in document.splitlines():
        if line == HEADER:
            inside = True
            continue
        if inside:
            if not line.startswith("|"):
                break
            if line == SEPARATOR:
                continue
            parts = [p.strip().replace("\\|", "|") for p in line.strip().strip("|").split("|")]
            if len(parts) != len(fields):
                raise ReviewError(f"Malformed review row: {line}")
            rows.append(dict(zip(fields, parts)))
    if len(rows) != 196 or len({r["source_id"] for r in rows}) != 196:
        raise ReviewError(f"Expected 195 proposals plus KOS hold; found {len(rows)} rows")
    if meta.get("fixed_decisions") != {
        "WBG": "Reuse existing owner-approved WBG to Palestine mapping; field 15 only.",
        "aggregates": "Reuse 13 owner-approved excluded dispositions; 665 populated values.",
        "KOS": "Preserve hold_for_evidence; no identity mapping.",
    }:
        raise ReviewError("Fixed prior-decision manifest was changed")
    counts = [sum(r["batch"] == f"{n:02d}" for r in rows) for n in range(1, 11)]
    if counts != [20,20,20,20,20,20,20,20,20,16]:
        raise ReviewError(f"Batch membership is invalid: {counts}")
    kos_rows = [r for r in rows if r["source_id"] == "KOS"]
    if len(kos_rows) != 1 or kos_rows[0]["decision"] != "HOLD" or kos_rows[0]["approved_game_id"] != "-":
        raise ReviewError("The existing KOS hold must remain explicit and unmapped")
    if sum(r["source_id"] != "KOS" for r in rows) != 195:
        raise ReviewError("Expected exactly 195 new identity proposals")
    if "tc_50c420df8b2c4c6eaae47d795f9a1ea2" not in document or "665 populated annual values" not in document:
        raise ReviewError("Reused WBG approval or aggregate exclusion section is missing")
    for row in rows:
        if row["series_code"] != row["source_id"] + ".NGDPD.A":
            raise ReviewError(f"Wrong series code for {row['source_id']}")
        decision = row["decision"].upper()
        if decision == "PENDING":
            if complete:
                raise ReviewError(f"Decision pending for {row['source_id']}")
            continue
        if decision not in {"APPROVE", "EXCLUDE", "HOLD"}:
            raise ReviewError(f"Invalid decision {decision} for {row['source_id']}")
        if len(row["rationale"].strip()) < 12:
            raise ReviewError(f"Rationale missing for {row['source_id']}")
        if decision == "APPROVE" and row["approved_game_id"] != row["proposed_game_id"]:
            raise ReviewError(f"Approved target differs from proposal for {row['source_id']}")
        if decision != "APPROVE" and row["approved_game_id"] not in {"", "-"}:
            raise ReviewError(f"{decision} must not have an approved target for {row['source_id']}")
    if complete:
        def field_value(label: str) -> str:
            match = re.search(r"^- " + re.escape(label) + r": (.+)$", document, re.M)
            return match.group(1).strip() if match else ""
        owner, approval_date, statement = (field_value("Owner actor"), field_value("Approval date (YYYY-MM-DD)"),
                                           field_value("Approval statement"))
        if not owner or owner == "PENDING" or not statement or statement == "PENDING" or len(statement) < 20:
            raise ReviewError("Owner actor and explicit approval statement must be completed")
        try:
            date.fromisoformat(approval_date)
        except ValueError as exc:
            raise ReviewError("Owner approval date must be YYYY-MM-DD") from exc
    return meta, rows, document

def validate_fingerprints(meta: dict[str, Any]) -> None:
    for key, item in meta.get("input_fingerprints", {}).items():
        path = ROOT / item["path"]
        if not path.is_file() or sha(path) != item["sha256"] or path.stat().st_size != item["byte_count"]:
            raise ReviewError(f"Reviewed source changed or missing: {key}")

def validate_review_against_source_register(meta: dict[str, Any], rows: list[dict[str, str]], document: str) -> None:
    auto_dir = ROOT / meta["automatic_review_directory"]
    source_rows = read_csv(auto_dir / "field_15_identity_review_register_final.csv")
    if len(source_rows) != 196:
        raise ReviewError("Fingerprint-bound automatic register must contain 196 identities")
    proposals = {r["source_id"]: r for r in source_rows}
    if len(proposals) != 196:
        raise ReviewError("Automatic source register contains duplicate source IDs")
    registry_doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry = {r.get("game_id"): r for r in registry_doc.get("records", []) if isinstance(r, dict)}
    for index, row in enumerate(rows):
        source = proposals.get(row["source_id"])
        if source is None:
            raise ReviewError(f"Unknown source identity in Markdown: {row['source_id']}")
        expected_batch = f"{index // 20 + 1:02d}"
        if row["batch"] != expected_batch:
            raise ReviewError(f"Batch number changed for {row['source_id']}")
        expected = {
            "source_name": source["source_name"], "series_code": source["series_code"],
            "populated_years": f'{source["populated_year_count"]} ({source["first_populated_year"]}–{source["last_populated_year"]})',
            "evidence": source["independent_evidence_reference"],
            "proposal_basis": source["review_notes"],
        }
        for field, value in expected.items():
            if row[field] != value:
                raise ReviewError(f"Source-derived {field} changed for {row['source_id']}")
        if row["source_id"] == "KOS":
            if row["proposed_game_id"] != "-" or row["registry_name"] != "-" or row["m49"] != "-":
                raise ReviewError("KOS must remain held with no proposed identity or M49 code")
            continue
        game_id = source["reviewed_proposed_game_id"]
        target = registry.get(game_id)
        registry_name = (target.get("names") or {}).get("en", "") if target else ""
        if not game_id or row["proposed_game_id"] != game_id:
            raise ReviewError(f"Proposed game_id changed for {row['source_id']}")
        if row["registry_name"] != registry_name or row["m49"] != source["un_m49_code"]:
            raise ReviewError(f"Registry target or M49 evidence changed for {row['source_id']}")
    if set(proposals) != {r["source_id"] for r in rows}:
        raise ReviewError("Markdown source identities differ from the automatic source register")
    exclusion_rows = read_csv(auto_dir / "field_15_exclusion_register.csv")
    aggregate_section = document.split("### Aggregate exclusions — existing owner decision", 1)[-1].split("### KOS — existing hold", 1)[0]
    for item in exclusion_rows:
        values = [item["source_country_code"], item["source_country_name"], item["series_code"],
                  item["populated_year_count"],
                  f'{item["first_populated_year"]}–{item["last_populated_year"]}',
                  "EXCLUDED — prior owner approval"]
        expected_line = "| " + " | ".join(cell(v) for v in values) + " |"
        if expected_line not in aggregate_section:
            raise ReviewError(f"Previously approved aggregate exclusion changed in Markdown: {item['source_country_code']}")
    if "Total: 13 aggregate series and 665 populated annual values" not in aggregate_section:
        raise ReviewError("Aggregate exclusion total changed in Markdown")
    if "WBG / West Bank and Gaza maps to tc_50c420df8b2c4c6eaae47d795f9a1ea2 (Palestine)" not in document:
        raise ReviewError("Previously approved WBG mapping changed in Markdown")


def validate_review(path: Path, complete: bool) -> dict[str, Any]:
    meta, rows, document = parse_review(path, complete)
    validate_fingerprints(meta)
    validate_review_against_source_register(meta, rows, document)
    return {"proposal_rows": len(rows), "approved": sum(r["decision"].upper()=="APPROVE" for r in rows),
            "excluded": sum(r["decision"].upper()=="EXCLUDE" for r in rows),
            "held": sum(r["decision"].upper()=="HOLD" for r in rows),
            "pending": sum(r["decision"].upper()=="PENDING" for r in rows),
            "fingerprints_valid": True, "database_written": False}

def verify_project_acquisition(path: Path, expected_source_sha: str) -> dict[str, Any]:
    if not path.is_file():
        raise ReviewError(f"Project DB not found: {path}")
    con = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        fk = [tuple(r) for r in con.execute("PRAGMA foreign_key_check")]
        if integrity != "ok" or fk:
            raise ReviewError(f"Project DB integrity/FK failure: {integrity}; {fk[:5]}")
        row = con.execute(
            """SELECT a.acquisition_id, a.status, a.integrity_status, a.provider_release_id,
                      a.evidence_json, a.metadata_json, s.stream_id, d.dataset_key, src.source_key
               FROM acquisitions a
               JOIN acquisition_streams s ON s.stream_id=a.stream_id
               JOIN datasets d ON d.dataset_id=s.dataset_id
               JOIN sources src ON src.source_key=d.source_key
               WHERE a.acquisition_id=5"""
        ).fetchone()
        if row is None or row["source_key"] != "imf_weo":
            raise ReviewError("Project DB acquisition ID 5 is not registered to imf_weo")
        if row["status"] != "acquired" or row["integrity_status"] != "verified":
            raise ReviewError("Project DB acquisition ID 5 is not acquired/integrity-verified")
        if "october_2026" not in str(row["provider_release_id"]).lower() and "2026" not in str(row["provider_release_id"]):
            raise ReviewError("Project DB acquisition ID 5 release is not October 2026")
        acquisition_text = ACQUISITION.read_text(encoding="utf-8")
        if expected_source_sha not in acquisition_text or RAW.name not in acquisition_text:
            raise ReviewError("Manual acquisition record does not corroborate the exact IMF CSV checksum and filename")
        if sha(RAW) != expected_source_sha:
            raise ReviewError("Local IMF WEO CSV differs from the reviewed source fingerprint")
        artifact_rows = con.execute(
            """SELECT artifact_role, relative_path, sha256, byte_count
               FROM acquisition_artifacts WHERE acquisition_id=5 ORDER BY relative_path"""
        ).fetchall()
        expected_artifacts = {
            relative(RAW): (sha(RAW), RAW.stat().st_size),
            relative(PDF): (sha(PDF), PDF.stat().st_size),
        }
        actual_artifacts = {
            item["relative_path"]: (item["sha256"], int(item["byte_count"]))
            for item in artifact_rows
        }
        if actual_artifacts != expected_artifacts or len(artifact_rows) != 2:
            raise ReviewError(
                "Project DB acquisition 5 artifact records do not exactly match the IMF CSV and Appendix PDF"
            )
        return {
            "acquisition_id": 5, "source_key": row["source_key"], "dataset_key": row["dataset_key"],
            "provider_release_id": row["provider_release_id"], "status": row["status"],
            "integrity_status": row["integrity_status"], "source_sha256_verified": True,
            "artifact_count": len(artifact_rows), "artifacts_sha256_and_bytes_verified": True,
            "sqlite_integrity": integrity, "foreign_key_violations": len(fk),
            "database_written": False,
        }
    finally:
        con.close()

def verify_existing_observations_are_candidate_subset(candidate: Path, database: Path) -> dict[str, Any]:
    candidate_rows = read_csv(candidate / "observations.csv")
    summary = json.loads((candidate / "candidate.json").read_text(encoding="utf-8"))
    expected = {
        (r["game_id"], r["indicator_code"], int(r["observation_year"]))
        for r in candidate_rows
    }
    con = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        existing = con.execute(
            """SELECT game_id, source_country_code, indicator_code, observation_year
               FROM imf_weo_historical_observations
               WHERE source_version=? AND source_sha256=? AND field_id=15""",
            (RELEASE, summary["source_sha256"]),
        ).fetchall()
        extras = [
            row for row in existing
            if (row["game_id"], row["indicator_code"], int(row["observation_year"])) not in expected
        ]
        if extras:
            by_code: dict[str, int] = {}
            for row in extras:
                code = row["source_country_code"]
                by_code[code] = by_code.get(code, 0) + 1
            detail = ", ".join(f"{code}:{count}" for code, count in sorted(by_code.items()))
            raise ReviewError(
                "Existing field-15 WEO observations fall outside the newly approved candidate "
                f"({len(extras)} rows: {detail}). No approval or database write was made. "
                "Resolve these legacy rows explicitly; this workflow will not delete or remap them."
            )
        return {
            "existing_observation_rows": len(existing),
            "existing_rows_outside_candidate": 0,
            "preflight_passed": True,
        }
    finally:
        con.close()


def verify_candidate_game_ids(observations: list[dict[str, Any]], database: Path) -> dict[str, Any]:
    expected = {row["game_id"] for row in observations}
    con = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
    try:
        present = {row[0] for row in con.execute(
            "SELECT game_id FROM countries WHERE game_id IN (" + ",".join("?" for _ in expected) + ")",
            tuple(sorted(expected)),
        )} if expected else set()
        missing = sorted(expected - present)
        if missing:
            raise ReviewError("Candidate targets are absent from canonical Game DB countries: " + ", ".join(missing[:20]))
        return {"candidate_game_ids": len(expected), "canonical_game_ids_present": len(present), "missing_game_ids": []}
    finally:
        con.close()


def verify_game_database(candidate: Path, database: Path, approval_id: str) -> dict[str, Any]:
    expected = read_csv(candidate / "observations.csv")
    summary = json.loads((candidate / "candidate.json").read_text(encoding="utf-8"))
    con = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        fk = [tuple(r) for r in con.execute("PRAGMA foreign_key_check")]
        if integrity != "ok" or fk:
            raise ReviewError(f"SQLite integrity/FK failure: {integrity}; {fk[:5]}")
        actual = con.execute(
            """SELECT game_id, source_country_code, source_country_name, indicator_code, field_id,
                      observation_year, value, unit, scale, value_status, latest_actual_annual_data,
                      reporting_year_months, source_reference, source_version, source_sha256,
                      acquired_on, acquisition_time_precision, import_id
               FROM imf_weo_historical_observations
               WHERE source_version=? AND source_sha256=? AND field_id=15""",
            (RELEASE, summary["source_sha256"]),
        ).fetchall()
        imports = con.execute(
            "SELECT import_id, import_status FROM dataset_imports WHERE dataset=? AND sha256=?",
            ("world_economic_outlook", summary["source_sha256"]),
        ).fetchall()
        if len(imports) != 1:
            raise ReviewError(f"Expected one dataset_imports record for this WEO snapshot; found {len(imports)}")
        if imports[0]["import_status"] != "candidate":
            raise ReviewError(f"Unexpected dataset_imports status: {imports[0]['import_status']}")
        import_id = int(imports[0]["import_id"])
        e = {(r["game_id"], r["indicator_code"], int(r["observation_year"])): r for r in expected}
        a = {(r["game_id"], r["indicator_code"], int(r["observation_year"])): r for r in actual}
        if len(actual) != len(expected) or set(e) != set(a):
            raise ReviewError(f"Imported key/count mismatch: expected {len(expected)}, got {len(actual)}")
        for key, want in e.items():
            got = a[key]
            checks = {
                "source_country_code": want["source_country_code"], "source_country_name": want["source_country_name"],
                "field_id": int(want["field_id"]), "value": float(want["value"]),
                "unit": want["unit"] or None, "scale": want["scale"] or None,
                "value_status": "unclassified",
                "latest_actual_annual_data": want["latest_actual_annual_data"] or None,
                "reporting_year_months": want["reporting_year_months"] or None,
                "source_reference": want["source_reference"],
                "source_version": want["source_version"], "source_sha256": want["source_sha256"],
                "acquired_on": want["acquired_on"], "acquisition_time_precision": want["acquisition_time_precision"],
                "import_id": import_id,
            }
            for field, value in checks.items():
                if got[field] != value:
                    raise ReviewError(f"Imported row {key} differs at {field}")
        approval = con.execute("SELECT domain, status, artifact_sha256 FROM application_approvals WHERE approval_id=?",
                               (approval_id,)).fetchone()
        events = [r["event_type"] for r in con.execute(
            "SELECT event_type FROM database_application_events WHERE approval_id=? ORDER BY rowid",
            (approval_id,))]
        if approval is None or approval["domain"] != "imf_weo_historical_observations" or approval["status"] != "applied":
            raise ReviewError("Application approval ledger is not in applied state")
        if not {"proposed", "approved", "applied"}.issubset(set(events)):
            raise ReviewError(f"Application approval event history is incomplete: {events}")
        return {"integrity_check": integrity, "foreign_key_violations": len(fk),
                "expected_observations": len(expected), "actual_observations": len(actual),
                "distinct_game_ids": len({r["game_id"] for r in expected}),
                "import_id": import_id, "dataset_import_status": imports[0]["import_status"],
                "approval_status": approval["status"], "approval_events": events,
                "all_statuses_unclassified": all(r["value_status"] == "unclassified" for r in actual)}
    finally:
        con.close()

def write_deterministic_candidate(observations: list[dict[str, Any]], exceptions: list[dict[str, Any]], summary: dict[str, Any], target: Path) -> Path:
    """Write a stable review-specific candidate path; never overwrite changed bytes."""
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)
    def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
        fields = list(dict.fromkeys(key for row in rows for key in row))
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return stream.getvalue().encode("utf-8")
    obs_bytes, exc_bytes = csv_bytes(observations), csv_bytes(exceptions)
    candidate_summary = dict(summary)
    candidate_summary["candidate_directory"] = relative(target)
    candidate_summary["observations_sha256"] = hashlib.sha256(obs_bytes).hexdigest()
    candidate_summary["exceptions_sha256"] = hashlib.sha256(exc_bytes).hexdigest()
    summary_bytes = (json.dumps(candidate_summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    expected = {"observations.csv": obs_bytes, "identity_exceptions.csv": exc_bytes, "candidate.json": summary_bytes}
    for name, payload in expected.items():
        output = target / name
        if output.exists():
            if output.read_bytes() != payload:
                raise ReviewError(f"Existing deterministic candidate differs: {output}; refusing overwrite")
        else:
            output.write_bytes(payload)
    return target


def apply_review(path: Path, actor: str, database: Path, project_database: Path) -> dict[str, Any]:
    meta, rows, document = parse_review(path, True)
    validate_fingerprints(meta)
    validate_review_against_source_register(meta, rows, document)
    project_preflight = verify_project_acquisition(project_database, meta["source_sha256"])
    approved = [r for r in rows if r["decision"].upper() == "APPROVE"]
    if not approved:
        raise ReviewError("No new identity mappings approved; refusing an empty application")
    def field_value(label: str) -> str:
        m = re.search(r"^- " + re.escape(label) + r": (.+)$", document, re.M)
        return m.group(1).strip() if m else ""
    owner, approval_date = field_value("Owner actor"), field_value("Approval date (YYYY-MM-DD)")
    if actor != owner:
        raise ReviewError("CLI actor must match the owner recorded in the review Markdown")
    original = json.loads(CROSSWALK.read_text(encoding="utf-8"))
    if len(original.get("mappings", [])) != 1 or original["mappings"][0].get("source_id") != "WBG":
        raise ReviewError("Original WBG crosswalk has changed; expected its sole existing WBG mapping")
    crosswalk = dict(original)
    crosswalk["mappings"] = list(original["mappings"]) + [{
        "game_id": r["approved_game_id"], "source_id": r["source_id"],
        "match_method": "reviewed_manual", "evidence_url": r["evidence"].split(";")[0].strip(),
        "source_name": r["source_name"], "review_note": r["rationale"],
    } for r in approved]
    crosswalk["reused_prior_approval"] = original.get("review_approval", {})
    crosswalk["review_approval"] = {
        "status": "approved", "approved_on": approval_date, "approver_role": "project_owner",
        "approval_record": relative(path),
        "scope": "Field 15 / NGDPD only; existing WBG mapping plus explicitly approved rows in the owner review.",
    }
    crosswalk["review_document"] = {"path": relative(path), "sha256": sha(path)}
    review_sha = sha(path)
    review_root = CANDIDATE_ROOT / review_sha[:16]
    review_root.mkdir(parents=True, exist_ok=True)
    derived_crosswalk = review_root / "reviewed_imf_weo_crosswalk.json"
    crosswalk_bytes = (json.dumps(crosswalk, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if derived_crosswalk.exists():
        if derived_crosswalk.read_bytes() != crosswalk_bytes:
            raise ReviewError("Existing derived crosswalk differs from this exact review; refusing overwrite")
    else:
        derived_crosswalk.write_bytes(crosswalk_bytes)
    observations, exceptions, summary = build_candidate(
        RAW, REGISTRY, verify_snapshot=True, crosswalk_path=derived_crosswalk, field_ids={15})
    decisions = {r["source_id"]: r for r in rows}
    aggregate_rows = read_csv((ROOT / meta["automatic_review_directory"]) / "field_15_exclusion_register.csv")
    aggregate_by_code = {r["source_country_code"]: r for r in aggregate_rows}
    if len(aggregate_by_code) != 13 or sum(int(r["populated_year_count"]) for r in aggregate_rows) != 665:
        raise ReviewError("The fingerprinted aggregate exclusion evidence no longer reconciles")
    for exc in exceptions:
        source_code = exc.get("source_country_code", "")
        decision = decisions.get(source_code)
        aggregate = aggregate_by_code.get(source_code)
        if aggregate:
            exc["disposition"] = "excluded"
            exc["owner_rationale"] = aggregate["rationale"]
        elif decision:
            exc["disposition"] = "excluded" if decision["decision"].upper() == "EXCLUDE" else "hold_for_evidence"
            exc["owner_rationale"] = decision["rationale"]
    expected_codes = {"WBG"} | {r["source_id"] for r in rows if r["decision"].upper() == "APPROVE"}
    actual_codes = {r["source_country_code"] for r in observations}
    if actual_codes != expected_codes:
        raise ReviewError(f"Candidate source identities mismatch: missing={sorted(expected_codes-actual_codes)}, extra={sorted(actual_codes-expected_codes)}")
    expected_unmapped = 14 + sum(r["decision"].upper() in {"HOLD", "EXCLUDE"} for r in rows if r["source_id"] != "KOS")
    actual_unmapped = [r for r in exceptions if r.get("exception") == "unmapped_or_ambiguous_identity"]
    if len(actual_unmapped) != expected_unmapped:
        raise ReviewError(f"Candidate exceptions mismatch: expected {expected_unmapped}, got {len(actual_unmapped)}")
    expected_exception_codes = set(aggregate_by_code) | {"KOS"} | {r["source_id"] for r in rows if r["decision"].upper() in {"HOLD", "EXCLUDE"}}
    actual_exception_codes = {r.get("source_country_code") for r in actual_unmapped}
    if actual_exception_codes != expected_exception_codes:
        raise ReviewError(f"Exception dispositions do not reconcile: missing={sorted(expected_exception_codes-actual_exception_codes)}, extra={sorted(actual_exception_codes-expected_exception_codes)}")
    if any(not r.get("disposition") or not r.get("owner_rationale") for r in actual_unmapped):
        raise ReviewError("Every unmapped source identity must have an explicit disposition and rationale")
    candidate = write_deterministic_candidate(observations, exceptions, summary, review_root / "candidate")
    canonical_identity_check = verify_candidate_game_ids(observations, database)
    existing_rows_check = verify_existing_observations_are_candidate_subset(candidate, database)
    prep = prepare_application(candidate, database_path=database,
        identity_path=REGISTRY, crosswalk_path=derived_crosswalk,
        migration_path=MIGRATION, acquisition_record_path=ACQUISITION)
    approval_id, status = prep["approval_id"], prep["status"]
    if status == "pending":
        decide_application_for_weo(approval_id, decision="approved", actor=actor,
            note=f"Owner-approved Markdown review {relative(path)}; {field_value('Approval statement')}; field 15 / NGDPD only.",
            database_path=database)
        status = "approved"
    if status == "approved":
        application = apply_application(candidate, approval_id, database_path=database,
            source_path=RAW, identity_path=REGISTRY, crosswalk_path=derived_crosswalk,
            migration_path=MIGRATION, acquisition_record_path=ACQUISITION)
    elif status == "applied":
        application = {"approval_id": approval_id, "status": "already_applied"}
    else:
        raise ReviewError(f"Existing approval has incompatible status: {status}")
    game_check = verify_game_database(candidate, database, approval_id)
    project_check = project_preflight
    report = {
        "approved_new_mappings": len(approved),
        "excluded_new_identities": sum(r["decision"].upper()=="EXCLUDE" for r in rows),
        "held_new_identities": sum(r["decision"].upper()=="HOLD" for r in rows),
        "candidate_directory": relative(candidate), "derived_crosswalk": relative(derived_crosswalk),
        "candidate_observations": len(observations),
        "candidate_exceptions": len(exceptions), "approval_id": approval_id,
        "approval_status": "applied", "application": application,
        "canonical_identity_preflight": canonical_identity_check,
        "existing_observation_preflight": existing_rows_check,
        "game_database_verification": game_check,
        "project_database_acquisition_verification": project_check,
        "original_crosswalk_modified": False, "identity_registry_modified": False,
        "observation_status_policy": "unclassified",
    }
    report_path = review_root / "verification_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["verification_report"] = relative(report_path)
    return report

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate-review")
    gen.add_argument("--automatic-review-dir", type=Path, default=AUTO)
    gen.add_argument("--output", type=Path, default=REVIEW)
    val = sub.add_parser("validate-review")
    val.add_argument("--review", type=Path, default=REVIEW)
    val.add_argument("--require-complete", action="store_true")
    app = sub.add_parser("apply-reviewed")
    app.add_argument("--review", type=Path, default=REVIEW)
    app.add_argument("--actor", required=True)
    app.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    app.add_argument("--project-database", type=Path, default=DEFAULT_PROJECT_DATABASE_PATH)
    args = parser.parse_args(argv)
    try:
        if args.command == "generate-review":
            result = generate_review(args.automatic_review_dir, args.output)
        elif args.command == "validate-review":
            result = validate_review(args.review, args.require_complete)
        else:
            result = apply_review(args.review, args.actor, args.database, args.project_database)
    except (OSError, csv.Error, json.JSONDecodeError, sqlite3.Error, ReviewError, WEOImportError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
