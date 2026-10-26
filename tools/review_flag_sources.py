#!/usr/bin/env python3
"""Review available flag-source coverage and report every unresolved flag decision.

This command discovers and reports candidates only. It never edits the identity
registry or flag mapping and never marks a mapping reviewed.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from tools.generate_country_flags import load_latest_source, load_source_svgs, resolve_path
from tools.run_data_pipeline import DEFAULTS, load_dotenv, select_manual_iso_reference

ROOT = Path(__file__).resolve().parents[1]
EDGE_CASES = (
    ("Falkland Islands", "The lipis source is expected to contain fk. Verify the territorial flag and add FK/FLK ISO metadata only from authoritative evidence."),
    ("Somaliland", "No official ISO 3166-1 alpha-2/alpha-3 assignment. Use a source flag only if the artwork is explicitly Somaliland's flag; otherwise review a manual SVG."),
    ("Kosovo", "XK/XKX are user-assigned conventions, not official ISO 3166-1 assignments. Verify a Kosovo-specific flag and record the source identifier separately from ISO metadata."),
    ("Northern Cyprus", "No official ISO 3166-1 assignment. Verify the artwork and political/territorial representation before mapping a source or manual SVG."),
    ("Indian Ocean Territories", "Resolve the exact entity represented by this Natural Earth record before choosing a flag. Do not assume it means the British Indian Ocean Territory."),
    ("Ashmore and Cartier Islands", "Decide explicitly whether the game representation should use Australia's flag or another approved representation; do not infer this from geography."),
    ("Siachen Glacier", "This is a geographic feature, not an ISO 3166-1 country. Do not assign a national flag by inference; decide whether a neutral marker is appropriate."),
)

def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value

def get_record_name(record: dict) -> str:
    names = record.get("names", {})
    if isinstance(names, dict) and isinstance(names.get("en"), str):
        return names["en"]
    return str(record.get("name") or record.get("source", {}).get("current_source_id") or record.get("game_id"))

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    args = parser.parse_args()
    try:
        config = load_dotenv(args.env_file)
        source_dir = resolve_path(config["TCA_FLAG_SOURCE_DIR"])
        registry_path = resolve_path(config["TCA_IDENTITY_REGISTRY"])
        mapping_path = resolve_path(config["TCA_FLAG_MAPPING"])
        report_path = resolve_path(config.get("TCA_FLAG_REVIEW_REPORT", "reports/flag-source-review.md"))
        manual_dir = resolve_path(config.get("TCA_FLAG_MANUAL_DIR", "raw_data/flags/manual"))
        iso_csv = resolve_path(config.get("TCA_ISO_MANUAL_REFERENCE_CSV", "data/reference/iso/iso-3166-1-2026-10.csv"))
        iso_ods = resolve_path(config.get("TCA_ISO_MANUAL_REFERENCE_ODS", "data/reference/iso/iso-3166-1-2026-10.ods"))
        iso_url = config.get("TCA_ISO_OFFICIAL_REFERENCE_URL", "https://www.iso.org/iso-3166-country-codes.html")

        print("Manual ISO reference check")
        print(f"Official ISO information page: {iso_url}")
        print(f"Expected CSV: {iso_csv}")
        print(f"Optional ODS: {iso_ods}")
        answer = input("Have you manually downloaded/reviewed the ISO reference and saved it at one of those paths? [y/N] ").strip().casefold()
        manual_iso_confirmed = answer in {"y", "yes"}
        selected = select_manual_iso_reference(ROOT, {
            **config,
            "TCA_ISO_MANUAL_REFERENCE_CSV": str(iso_csv),
            "TCA_ISO_MANUAL_REFERENCE_ODS": str(iso_ods),
        })
        iso_note = ""
        if not manual_iso_confirmed:
            iso_note = (
                "NOT CONFIRMED by operator. Open the official ISO page above, obtain the current ISO 3166-1 reference "
                "through the access offered by ISO, save/export the table as UTF-8 CSV with English name, French name, "
                "alpha-2, alpha-3 and numeric columns, then rerun this command. Do not treat third-party mirrors as "
                "an official ISO download."
            )
            print("\nACTION REQUIRED: " + iso_note)
        elif not selected["path"]:
            iso_note = "Operator confirmed a download, but neither configured local reference file passed validation."
            print("\nWARNING: " + iso_note, file=sys.stderr)
        else:
            iso_note = f"Operator confirmed the manual reference; validated {len(selected['rows'])} rows from {selected['path']}."
            print(iso_note)

        refresh = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "refresh_flag_source.py"), "--env-file", str(args.env_file)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        if refresh.stdout:
            print(refresh.stdout.rstrip())
        if refresh.stderr:
            print(refresh.stderr.rstrip(), file=sys.stderr)
        if refresh.returncode:
            raise RuntimeError(f"flag source refresh failed with exit code {refresh.returncode}")

        registry = read_json(registry_path)
        mapping = read_json(mapping_path)
        _, provenance = load_latest_source(source_dir)
        source_svgs = load_source_svgs(source_dir / str(json.loads((source_dir / "latest.json").read_text(encoding="utf-8"))["archive_file"]))
        source_codes = set(source_svgs)
        mapping_by_id = {row.get("game_id"): row for row in mapping.get("records", []) if isinstance(row, dict)}
        records = [row for row in registry.get("records", []) if isinstance(row, dict)]
        unresolved = []
        for record in records:
            game_id = record.get("game_id")
            decision = mapping_by_id.get(game_id, {})
            code = decision.get("source_flag_code")
            manual_path = decision.get("manual_svg_path")
            valid_source = isinstance(code, str) and code in source_codes
            valid_manual = isinstance(manual_path, str) and (manual_dir / manual_path).is_file()
            if decision.get("status") != "reviewed" or not (valid_source or valid_manual):
                unresolved.append((get_record_name(record), game_id, code, manual_path, decision.get("status", "missing mapping")))

        manual_files = sorted(p.relative_to(manual_dir).as_posix() for p in manual_dir.rglob("*.svg")) if manual_dir.exists() else []
        edge_lines = []
        for name, note in EDGE_CASES:
            found = [r for r in records if get_record_name(r).casefold() == name.casefold()]
            if found:
                for record in found:
                    decision = mapping_by_id.get(record.get("game_id"), {})
                    code = decision.get("source_flag_code")
                    status = decision.get("status", "missing mapping")
                    availability = f"source code available: {code in source_codes}" if isinstance(code, str) else "no source code selected"
                    edge_lines.append(f"| {name} | {record.get('game_id')} | {status} | {availability} | {note} |")
            else:
                edge_lines.append(f"| {name} | not found in current registry | unresolved | unknown | {note} |")

        report_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Flag source discovery and review", "",
            f"- Run time (UTC): {datetime.now(timezone.utc).isoformat()}",
            f"- Status: {'REVIEW REQUIRED' if unresolved else 'MAPPING COVERAGE READY FOR AUDIT'}",
            f"- Source repository: {provenance.get('source_url')}",
            f"- Configured ref: {provenance.get('configured_ref')}",
            f"- Resolved commit: {provenance.get('resolved_commit')}",
            f"- Retrieved (UTC): {provenance.get('retrieved_at_utc')}",
            f"- Archive SHA-256: {provenance.get('archive_sha256')}",
            f"- Available source SVG codes: {len(source_codes)}",
            f"- Registry records: {len(records)}",
            f"- Unconfirmed/unusable mappings: {len(unresolved)}",
            f"- Manual SVG directory: {manual_dir}",
            f"- Manual SVG files found: {len(manual_files)}",
            f"- ISO operator confirmation: {'yes' if manual_iso_confirmed else 'no'}",
            f"- ISO reference selected: {selected['path'] if selected.get('path') else 'none'}",
            f"- ISO note: {iso_note}",
            "", "## Seven edge cases", "",
            "| Territory | game_id | Mapping status | Source availability | Review guidance |",
            "|---|---|---|---|---|",
            *edge_lines,
            "", "## Unconfirmed or unusable mappings", "",
            "A mapping is unresolved when it is not marked reviewed or its selected source SVG/manual SVG is unavailable. This report does not approve or edit any mapping.", "",
            "| Territory | game_id | Source code | Manual SVG path | Status |",
            "|---|---|---|---|---|",
        ]
        lines.extend(
            f"| {name.replace('|', '\\|')} | {game_id} | {code or '—'} | {manual_path or '—'} | {status} |"
            for name, game_id, code, manual_path, status in unresolved
        )
        if not unresolved:
            lines.append("| None | — | — | — | — |")
        lines += ["", "## Source catalogue", "", "Source codes available in the refreshed archive:", "", ", ".join(f"`{code}`" for code in sorted(source_codes)), "", "## Manual SVG instructions", "",
            f"1. Put a reviewed SVG in `{manual_dir}` (prefer a descriptive filename such as `somaliland.svg`).",
            "2. Keep the original source/evidence URL and licensing details in the mapping record's evidence/decision note.",
            "3. In config/country_flag_mapping.json, set manual_svg_path to the relative filename under the manual directory, source_flag_code to null, and status to reviewed only after human review.",
            "4. Never set status to reviewed just because the file parses; confirm its identity, provenance, and usage rights.",
            "5. Run the separate game-asset build command only after decisions are reviewed.",
            "", "## ISO manual reference instructions", "", iso_note or "No ISO note.", "",
            "## Safety", "", "- No identity registry or mapping records were modified.", "- No mapping was auto-approved.", "- Candidate assets were not generated by this review command.", ""]
        report_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\nFlag source review report: {report_path}")
        print(f"Available source SVGs: {len(source_codes)}; unresolved mappings: {len(unresolved)}")
        print("\nEDGE CASES")
        for name, note in EDGE_CASES:
            print(f"- {name}: {note}")
        print("\nUNCONFIRMED / UNUSABLE MAPPINGS")
        if unresolved:
            for name, game_id, code, manual_path, status in unresolved:
                print(f"- {name} [{game_id}]: status={status}; source_code={code or 'none'}; manual_svg={manual_path or 'none'}")
        else:
            print("- None")
        print("\nNo mappings were approved or changed.")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"Flag source review failed: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
