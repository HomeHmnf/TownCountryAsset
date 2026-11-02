"""Semantic validator for UN WPP 2024 Medium WP1.5 candidates."""
from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any

from tools.database.connection import REPOSITORY_ROOT

AGE_GROUPS = tuple([f"{start}-{start + 4}" for start in range(0, 100, 5)] + ["100+"])
FIELD_KEYS = {
    1: ("population", "scalar", "people"),
    2: ("population_growth", "scalar", "percent_per_year"),
    6: ("median_age", "scalar", "years"),
    12: ("age_distribution", "structured", "age_band_share_or_count"),
    13: ("sex_distribution", "structured", "people_or_share"),
    14: ("net_migration", "scalar", "people_or_rate"),
}

def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))

class UNWPPValidator:
    def validate(self, *, connection: sqlite3.Connection, candidate_dir: Path,
                 manifest: dict[str, Any], observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        errors: list[str] = []
        grouped: dict[tuple[str, int], dict[str, Any]] = {}
        for row in observations:
            key = (row.get("game_id"), row.get("field_id"))
            if not isinstance(key[0], str) or key[1] not in FIELD_KEYS:
                errors.append(f"Invalid identity or unexpected field in observation: {key}")
                continue
            if key in grouped:
                errors.append(f"Duplicate country/field observation: {key}")
            grouped[key] = row
        game_ids = {game_id for game_id, _ in grouped}
        expected = {(game_id, field_id) for game_id in game_ids for field_id in FIELD_KEYS}
        missing = sorted(expected - set(grouped))
        extra = sorted(set(grouped) - expected)
        if missing or extra:
            errors.append(f"Candidate field coverage mismatch: missing={len(missing)}, extra={len(extra)}")
        checks.append({"name": "candidate_field_coverage", "status": "FAIL" if errors else "PASS",
                       "detail": f"{len(game_ids)} countries; {len(grouped)} unique country-field rows; expected six fields per country"})

        by_country = {game_id: {field_id: grouped.get((game_id, field_id)) for field_id in FIELD_KEYS}
                      for game_id in game_ids}
        age_max_total = age_max_sex = sex_max = 0.0
        age_count = 0
        for game_id, fields in by_country.items():
            for field_id, (key, storage, unit) in FIELD_KEYS.items():
                row = fields.get(field_id)
                if row is None:
                    continue
                if row.get("unit") != unit or row.get("value_status") != "projected" or row.get("observation_period") != "2026":
                    errors.append(f"{game_id}/{key}: unexpected unit, status or observation period")
            pop_row = fields.get(1)
            pop = pop_row.get("value") if pop_row else None
            age_row, sex_row, migration = fields.get(12), fields.get(13), fields.get(14)
            if pop_row and (not _finite(pop) or pop <= 0):
                errors.append(f"{game_id}: population must be a positive finite number")
            if age_row:
                bands = age_row.get("value")
                if not isinstance(bands, list) or len(bands) != 21:
                    errors.append(f"{game_id}: age distribution must contain exactly 21 bands")
                else:
                    labels = [item.get("age_band") if isinstance(item, dict) else None for item in bands]
                    if tuple(labels) != AGE_GROUPS:
                        errors.append(f"{game_id}: age-band labels/order differ from WPP contract")
                    sums = {"population_male": 0.0, "population_female": 0.0, "population_total": 0.0}
                    for item in bands:
                        if not isinstance(item, dict):
                            errors.append(f"{game_id}: malformed age-band record")
                            continue
                        vals = [item.get(name) for name in sums]
                        if not all(_finite(v) and v >= 0 for v in vals):
                            errors.append(f"{game_id}: age-band values must be finite and non-negative")
                            continue
                        for name, value in zip(sums, vals):
                            sums[name] += float(value)
                        age_max_sex = max(age_max_sex, abs(vals[0] + vals[1] - vals[2]))
                    age_count += 1
                    if _finite(pop):
                        age_max_total = max(age_max_total, abs(sums["population_total"] - float(pop)))
                    if sex_row and isinstance(sex_row.get("value"), dict):
                        sv = sex_row["value"]
                        if _finite(sv.get("male")) and _finite(sv.get("female")):
                            age_max_sex = max(age_max_sex, abs(sums["population_male"] - sv["male"]),
                                              abs(sums["population_female"] - sv["female"]))
            if sex_row:
                value = sex_row.get("value")
                if not isinstance(value, dict) or set(value) != {"male", "female"} or not all(_finite(value.get(k)) and value[k] >= 0 for k in ("male", "female")):
                    errors.append(f"{game_id}: sex distribution must contain non-negative male/female counts")
                elif _finite(pop):
                    sex_max = max(sex_max, abs(value["male"] + value["female"] - float(pop)))
            if migration:
                if not _finite(migration.get("value")):
                    errors.append(f"{game_id}: net migration must be a finite absolute count")
                method = str(migration.get("methodology", "")).lower()
                if "not the net migration rate" not in method and "not a rate" not in method:
                    errors.append(f"{game_id}: net migration methodology must explicitly identify an absolute count")
        # WPP values are rounded in thousands before conversion to people.
        if age_max_sex > 10:
            errors.append(f"Age-band/sex reconciliation exceeds 10 people: {age_max_sex}")
        if age_max_total > 10:
            errors.append(f"Age-band total/population reconciliation exceeds 10 people: {age_max_total}")
        if sex_max > 1.1:
            errors.append(f"Sex totals/population reconciliation exceeds 1.1 people: {sex_max}")
        checks.append({"name": "wpp_age_sex_population_semantics", "status": "FAIL" if errors else "PASS",
                       "detail": f"age countries={age_count}; max age-total delta={age_max_total:.3f}; max age/sex delta={age_max_sex:.3f}; max sex-total delta={sex_max:.3f}"})

        # Verify persisted canonical values against the candidate for this source/release.
        imports = connection.execute(
            "SELECT import_id FROM dataset_imports WHERE dataset = ? AND source_version = ? ORDER BY import_id DESC",
            ("un_wpp", manifest.get("release")),
        ).fetchall()
        if not imports:
            checks.append({"name": "canonical_database_comparison", "status": "WARNING",
                           "detail": "No applied import for this candidate release; database integrity was checked, but value parity is not applicable."})
        else:
            import_id = imports[0]["import_id"]
            scalar_map = {1: "population", 2: "population_growth", 6: "median_age", 14: "net_migration"}
            db_errors = []
            for (game_id, field_id), row in grouped.items():
                if field_id in scalar_map:
                    stored = connection.execute(
                        "SELECT value, unit, value_status, observation_period, source_reference, methodology FROM current_statistics WHERE game_id = ? AND statistic_key = ? AND import_id = ?",
                        (game_id, scalar_map[field_id], import_id),
                    ).fetchone()
                    if stored is None or row.get("value") is None or abs(float(stored["value"]) - float(row["value"])) > 1e-7:
                        db_errors.append(f"{game_id}/{scalar_map[field_id]} differs or is missing in canonical DB")
                elif field_id in {12, 13}:
                    category = "wp1_5"
                    data_key = "age_distribution" if field_id == 12 else "sex_distribution"
                    stored = connection.execute(
                        "SELECT payload_json, unit, value_status, observation_period, source_reference FROM selected_game_data WHERE game_id = ? AND data_category = ? AND data_key = ? AND import_id = ?",
                        (game_id, category, data_key, import_id),
                    ).fetchone()
                    if stored is None:
                        db_errors.append(f"{game_id}/{data_key} missing in canonical DB")
                    else:
                        payload = json.loads(stored["payload_json"])
                        if payload.get("value") != row.get("value"):
                            db_errors.append(f"{game_id}/{data_key} differs in canonical DB")
            checks.append({"name": "canonical_database_value_parity", "status": "FAIL" if db_errors else "PASS",
                           "detail": f"Compared {len(grouped)} candidate country-field records against import_id={import_id}; mismatches={len(db_errors)}"})
            checks.extend({"name": "canonical_parity_exception", "status": "FAIL", "detail": item} for item in db_errors[:100])

        # Expose Togo provenance separately because the update is a scoped supplement.
        togo = next((row for row in observations if row.get("source_id") == "768"), None)
        if togo:
            togo_refs = sorted({row.get("source_reference", "") for row in observations if row.get("source_id") == "768"})
            checks.append({"name": "togo_supplement_provenance_review", "status": "WARNING",
                           "detail": "Togo observations cite these source references: " + " || ".join(togo_refs) +
                           ". Confirm each reference matches the actual source member supplying that field."})
        return checks
