"""Build a decision-readiness assessment from the semantic disposition matrix.

The assessment identifies blockers and next evidence actions. It is not an
approval, source-selection recommendation, or canonical-data write.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "reports/sources/imf-wdi-semantic-disposition/20261107T145725Z/semantic_disposition_matrix.csv"
DEFAULT_OUTPUT = ROOT / "reports/sources/imf-wdi-decision-readiness"

FIELD_DECISIONS: dict[str, dict[str, Any]] = {
    "15": {
        "concept": "Qualified comparability: nominal GDP, current USD.",
        "current_disposition": "Retain existing IMF WEO priority; do not promote WDI.",
        "readiness": "blocked_semantic_and_identity_gates",
        "blockers": [
            "IMF October 2026 and WDI rolling-API snapshot are not provider-vintage aligned.",
            "National-accounts compilation, revision vintage and USD conversion are not reconciled country by country.",
            "CAR, Guinea and Turkmenistan have material documented cases with remaining year-level gaps.",
        ],
        "next_actions": [
            "Acquire or identify an immutable WDI provider vintage aligned to the WEO release, if available.",
            "Reconstruct source national-accounts levels and USD conversion for the material country cases.",
            "Resolve the 2018 Turkmenistan divergence onset and CAR post-2021/other-year series lineage.",
        ],
        "evidence": "docs/data-sources/field-15-16-gdp-comparability-assessment.md",
    },
    "16": {
        "concept": "Qualified comparability: nominal GDP per capita.",
        "current_disposition": "Retain existing IMF WEO priority; do not promote WDI.",
        "readiness": "blocked_semantic_and_identity_gates",
        "blockers": [
            "All field 15 numerator-vintage and USD-conversion issues also apply.",
            "Population denominator vintage, reference date and universe are not independently reconstructed.",
        ],
        "next_actions": [
            "Complete the field 15 GDP numerator reconciliation.",
            "Acquire matching population series and reconstruct both providers' denominators by year.",
        ],
        "evidence": "docs/data-sources/field-15-16-gdp-comparability-assessment.md",
    },
    "18": {
        "concept": "Not demonstrated comparable: current PPP international dollars.",
        "current_disposition": "Retain existing IMF WEO priority; do not promote WDI.",
        "readiness": "blocked_semantic_and_identity_gates",
        "blockers": [
            "ICP benchmark, linking/extrapolation and nominal-GDP input pipelines are not decomposed.",
            "IMF PPPGDP has no latest-actual metadata or reporting-period classification in the acquired WEO export.",
            "Zimbabwe's 2017 special conversion is documented but exact October 2026 WEO and current WDI record-level factors remain unverified.",
        ],
        "next_actions": [
            "Acquire immutable ICP 2017/2021 benchmark records and relevant PPP time series.",
            "Reconstruct provider-implied PPP factors and underlying nominal GDP by country-year.",
            "Keep actual/estimate status and reporting period unclassified until explicit evidence is available.",
        ],
        "evidence": "docs/data-sources/field-18-ppp-gdp-comparability-assessment.md",
    },
    "20": {
        "concept": "Not demonstrated comparable: annual CPI inflation.",
        "current_disposition": "Retain existing IMF WEO priority; do not promote WDI.",
        "readiness": "blocked_semantic_and_identity_gates",
        "blockers": [
            "Period-average versus end-period definitions and calendar versus fiscal-year windows require explicit alignment.",
            "WEO reporting-period metadata is blank for the compared CPI observations.",
            "Samoa 2025 residual and earlier Tonga/Palau years remain unresolved; CPI revisions/vintages differ.",
        ],
        "next_actions": [
            "Acquire immutable WDI/IFS observations and exact country-year national/IMF fiscal-year tables.",
            "Record period start/end, annual-average or end-period convention, CPI basket and revision vintage.",
            "Resolve Samoa 2025 and the earlier Tonga/Palau observations before any full-period reconciliation.",
        ],
        "evidence": "docs/data-sources/field-20-inflation-comparability-assessment.md",
    },
    "21": {
        "concept": "Generally non-equivalent products: IMF country-desk/national series versus WDI ILO modelled estimates.",
        "current_disposition": "Retain existing IMF WEO priority; do not promote WDI modelled or national-estimate series.",
        "readiness": "blocked_semantic_and_identity_gates",
        "blockers": [
            "IMF LUR unit is blank in the acquired WEO export; reference population and period need country-level verification.",
            "WDI modelled ILO estimates and WDI national estimates are distinct products, neither automatically interchangeable with WEO.",
            "WDI observation status is unclassified for all present observations in this snapshot.",
        ],
        "next_actions": [
            "Establish IMF LUR unit, reference population and annual aggregation for each country.",
            "Keep modelled and national-estimate WDI indicators separate in any future comparison.",
            "Use country-specific national-source corroboration only within its documented years and preserve survey redesign/preliminary flags.",
        ],
        "evidence": "docs/data-sources/field-21-unemployment-comparability-assessment.md",
    },
}

GLOBAL_GATES = [
    {
        "gate": "country_identity",
        "status": "blocking",
        "finding": "Every one of the 242 project identities is still mapped_review_required; no row has verified identity mapping.",
        "action": "Resolve country identity and ISO assignment through the separate identity-governance process before any country-level canonical application.",
    },
    {
        "gate": "source_vintage",
        "status": "blocking",
        "finding": "The IMF input is the fixed October 2026 WEO export; the WDI input is a timestamped capture of the rolling API, not a provider-declared vintage.",
        "action": "Retain snapshot provenance and acquire aligned provider vintages where possible; do not describe the comparison as vintage-aligned.",
    },
    {
        "gate": "observation_status",
        "status": "blocking_for_status_sensitive_use",
        "finding": "WDI provides no explicit observation status in this capture; IMF latest-actual metadata is only a boundary hint and does not classify later years as projections.",
        "action": "Preserve unclassified/missing states; obtain explicit source status or country-specific evidence before classifying actual, estimate or projection.",
    },
    {
        "gate": "approval_and_application",
        "status": "not_started_by_design",
        "finding": "No semantic approval, source-selection change, release promotion or Game DB write has been made.",
        "action": "After blockers close, prepare a separate evidence-backed approval artifact; do not bypass the existing approval/application gate.",
    },
]


class ReadinessError(RuntimeError):
    """Invalid semantic matrix input."""


def assess(input_path: Path) -> dict[str, Any]:
    with input_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"game_id", "country_name", "field_id", "year", "identity_gate",
                    "coverage_status", "imf_observation_status", "wdi_observation_status",
                    "year_evidence_scope", "country_case_id"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ReadinessError(f"Semantic matrix missing columns: {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ReadinessError("Semantic matrix contains no rows")
    fields_seen = {row["field_id"] for row in rows}
    if fields_seen != set(FIELD_DECISIONS):
        raise ReadinessError(f"Expected fields {sorted(FIELD_DECISIONS)}, found {sorted(fields_seen)}")
    identity_counts = Counter(row["identity_gate"] for row in rows)
    field_assessments = []
    for field_id in sorted(FIELD_DECISIONS, key=int):
        subset = [row for row in rows if row["field_id"] == field_id]
        spec = FIELD_DECISIONS[field_id]
        field_assessments.append({
            "field_id": field_id,
            "row_count": len(subset),
            "country_count": len({row["game_id"] for row in subset}),
            "coverage_counts": dict(sorted(Counter(row["coverage_status"] for row in subset).items())),
            "imf_status_counts": dict(sorted(Counter(row["imf_observation_status"] for row in subset).items())),
            "wdi_status_counts": dict(sorted(Counter(row["wdi_observation_status"] for row in subset).items())),
            "year_evidence_scope_counts": dict(sorted(Counter(row["year_evidence_scope"] for row in subset).items())),
            **spec,
        })
    case_groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        case_id = row["country_case_id"]
        if case_id == "no_specific_country_case_recorded":
            continue
        key = (row["game_id"], row["country_name"], row["field_id"])
        case_groups.setdefault(key, []).append(row)
    cases = []
    for (game_id, country, field_id), items in sorted(case_groups.items()):
        cases.append({
            "game_id": game_id,
            "country": country,
            "field_id": field_id,
            "case_id": items[0]["country_case_id"],
            "year_scopes": dict(sorted(Counter(r["year_evidence_scope"] for r in items).items())),
            "years_with_bounded_evidence": sorted({int(r["year"]) for r in items if r["year_evidence_scope"] not in {
                "no_country_case_year_scope", "case_context_only_no_year_specific_support"
            }}),
            "identity_gate": "blocking" if any(r["identity_gate"] != "identity_verified" for r in items) else "passed",
            "status": "evidence_context_or_bounded_corroboration_not_semantic_approval",
        })
    return {
        "assessment": "imf_weo_wdi_decision_readiness",
        "input": str(input_path),
        "row_count": len(rows),
        "country_count": len({row["game_id"] for row in rows}),
        "identity_gate_counts": dict(sorted(identity_counts.items())),
        "global_gates": GLOBAL_GATES,
        "field_assessments": field_assessments,
        "country_case_assessments": cases,
        "decision": "not_ready_for_source_policy_change_or_canonical_application",
        "current_source_priority": "existing IMF WEO priority assignments remain unchanged for fields 15, 16, 18, 20 and 21",
        "approval_created": False,
        "policy_changed": False,
        "release_promoted": False,
        "project_database_written": False,
        "game_database_written": False,
    }


def write_report(result: dict[str, Any], output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output_root / stamp
    suffix = 1
    while target.exists():
        target = output_root / f"{stamp}-{suffix}"
        suffix += 1
    target.mkdir()
    result["report_directory"] = str(target)
    (target / "decision_readiness.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# IMF WEO–WDI decision-readiness assessment", "",
        f"- Matrix rows: {result['row_count']}",
        f"- Project identities: {result['country_count']}",
        f"- Decision: **{result['decision']}**",
        f"- Source priority: {result['current_source_priority']}",
        "", "## Global gates", "",
        "| Gate | Status | Finding | Required action |",
        "|---|---|---|---|",
    ]
    for gate in result["global_gates"]:
        lines.append(f"| {gate['gate']} | {gate['status']} | {gate['finding']} | {gate['action']} |")
    lines += ["", "## Field decisions", "", "| Field | Concept | Current disposition | Readiness |", "|---:|---|---|---|"]
    for item in result["field_assessments"]:
        lines.append(f"| {item['field_id']} | {item['concept']} | {item['current_disposition']} | {item['readiness']} |")
    for item in result["field_assessments"]:
        lines += ["", f"### Field {item['field_id']} blockers and next actions", "", "**Blockers**"]
        lines += [f"- {value}" for value in item["blockers"]]
        lines += ["", "**Next actions**"]
        lines += [f"- {value}" for value in item["next_actions"]]
        lines += [f"", f"Evidence record: `{item['evidence']}`"]
    lines += ["", "## Country evidence cases", "", f"Recorded case groups: {len(result['country_case_assessments'])}. These are context or bounded corroboration, not approvals.", ""]
    for item in result["country_case_assessments"]:
        years = ", ".join(str(y) for y in item["years_with_bounded_evidence"]) or "none"
        lines.append(f"- {item['country']} — field {item['field_id']} (`{item['case_id']}`): bounded evidence years: {years}; identity gate: {item['identity_gate']}.")
    lines += ["", "## Governance", "",
        "- No source-selection priority changed.",
        "- No identity was approved or promoted.",
        "- No semantic approval was created.",
        "- No release was promoted.",
        "- Neither SQLite database was written.",
        "- Country evidence must not be generalized beyond its bounded years; explicit missing/unclassified status is preserved.",
        ""]
    (target / "decision_readiness.md").write_text("\n".join(lines), encoding="utf-8")
    with (target / "field_decision_queue.csv").open("w", encoding="utf-8", newline="") as stream:
        fields = ["field_id", "row_count", "country_count", "readiness", "concept", "current_disposition", "evidence"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for item in result["field_assessments"]:
            writer.writerow({key: item[key] for key in fields})
    with (target / "country_case_decision_queue.csv").open("w", encoding="utf-8", newline="") as stream:
        fields = ["game_id", "country", "field_id", "case_id", "years_with_bounded_evidence", "identity_gate", "status"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for item in result["country_case_assessments"]:
            writer.writerow({**item, "years_with_bounded_evidence": ",".join(map(str, item["years_with_bounded_evidence"]))})
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        result = assess(args.input)
        target = write_report(result, args.output_root)
    except (ReadinessError, OSError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({**result, "report_directory": str(target)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
