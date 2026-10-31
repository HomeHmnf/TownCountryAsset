"""Transactional WP1.5 import of normalized observations with explicit identity mapping."""
from __future__ import annotations
import hashlib, json, math
from pathlib import Path
from typing import Any
from tools.database.connection import REPOSITORY_ROOT, connect_database
from tools.database.schema import apply_migrations, validate_database
from tools.database.source_crosswalk import CrosswalkError, load_crosswalk

DEFAULT_CONTRACT = REPOSITORY_ROOT / "config" / "wp1_5_data_sources.json"

class WP15ImportError(RuntimeError):
    """Invalid, incomplete, or conflicting normalized WP1.5 import."""

def _json(path, label):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WP15ImportError(f"Cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WP15ImportError(f"{label} must be a JSON object")
    return value

def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise WP15ImportError(f"{label} must be non-empty text")
    return value.strip()

def _canonical(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise WP15ImportError(f"Structured value is not finite JSON: {exc}") from exc

def _manifest_snapshot(manifest, manifest_path, source_key, release):
    if manifest.get("manifest_schema_version") != 1 or manifest.get("work_package") != "WP1.5":
        raise WP15ImportError("Unsupported WP1.5 acquisition manifest")
    if manifest.get("source_key") != source_key or manifest.get("release") != release:
        raise WP15ImportError("Normalized source/release does not match acquisition manifest")
    _text(manifest.get("final_url"), "manifest.final_url")
    _text(manifest.get("retrieved_at"), "manifest.retrieved_at")
    digest = _text(manifest.get("sha256"), "manifest.sha256")
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise WP15ImportError("manifest.sha256 must be lowercase SHA-256")
    raw_path = Path(_text(manifest.get("local_raw_path"), "manifest.local_raw_path"))
    if not raw_path.is_absolute():
        raw_path = (REPOSITORY_ROOT / raw_path).resolve()
    else:
        raw_path = raw_path.resolve()
    try:
        raw_path.relative_to(REPOSITORY_ROOT.resolve())
    except ValueError as exc:
        raise WP15ImportError("Raw snapshot must be inside the repository") from exc
    if "raw_data" not in raw_path.parts:
        raise WP15ImportError("Raw snapshot must be under raw_data")
    try:
        raw = raw_path.read_bytes()
    except OSError as exc:
        raise WP15ImportError(f"Cannot read raw snapshot {raw_path}: {exc}") from exc
    if not raw or len(raw) != manifest.get("byte_count") or hashlib.sha256(raw).hexdigest() != digest:
        raise WP15ImportError("Raw snapshot byte count or checksum does not match manifest")
    return digest

def _validate_row(row, index, fields, source_key, source_ids):
    label = f"observations[{index}]"
    if not isinstance(row, dict):
        raise WP15ImportError(f"{label} must be an object")
    source_id = _text(row.get("source_id"), f"{label}.source_id")
    if source_id not in source_ids:
        raise WP15ImportError(f"{label}.source_id is absent from crosswalk")
    field_id = row.get("field_id")
    if isinstance(field_id, bool) or not isinstance(field_id, int) or field_id not in fields:
        raise WP15ImportError(f"{label}.field_id is not an approved field ID")
    field = fields[field_id]
    if field["primary_source"] != source_key:
        raise WP15ImportError(f"{label}.field_id {field_id} is assigned to {field['primary_source']}, not {source_key}")
    unit = _text(row.get("unit"), f"{label}.unit")
    if unit not in {x.strip() for x in field["unit"].split("_or_")}:
        raise WP15ImportError(f"{label}.unit {unit!r} is outside contract unit {field['unit']!r}")
    period = _text(row.get("observation_period"), f"{label}.observation_period")
    reference = _text(row.get("source_reference"), f"{label}.source_reference")
    status = row.get("value_status")
    value = row.get("value")
    if field["storage"] == "scalar":
        if value is None:
            if status not in {"unavailable", "not_applicable"}:
                raise WP15ImportError(f"{label}.NULL requires unavailable/not_applicable status")
        elif isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or status not in {"observed", "estimated", "projected"}:
            raise WP15ImportError(f"{label} scalar value/status is invalid")
    else:
        if value is None or status not in {"observed", "estimated", "projected"}:
            raise WP15ImportError(f"{label} structured value/status is invalid")
        _canonical(value)
    return {"source_id":source_id,"field_id":field_id,"field":field,"value":value,
            "unit":unit,"status":status,"period":period,"reference":reference,
            "method":_text(row.get("methodology",field["method"]),f"{label}.methodology")}

def import_wp1_5_observations(database_path, *, normalized_path, manifest_path,
                               crosswalk_path, contract_path=DEFAULT_CONTRACT):
    normalized = _json(normalized_path,"normalized observations")
    manifest = _json(manifest_path,"acquisition manifest")
    contract = _json(contract_path,"WP1.5 contract")
    if normalized.get("schema_version") != 1:
        raise WP15ImportError("Unsupported normalized observations schema_version")
    source_key = _text(normalized.get("source_key"),"normalized.source_key")
    release = _text(normalized.get("release"),"normalized.release")
    if source_key not in contract.get("sources",{}):
        raise WP15ImportError(f"Unknown source key: {source_key}")
    digest = _manifest_snapshot(manifest,Path(manifest_path),source_key,release)
    try:
        crosswalk = load_crosswalk(crosswalk_path,expected_dataset=source_key)
    except CrosswalkError as exc:
        raise WP15ImportError(f"Invalid crosswalk: {exc}") from exc
    if crosswalk.source_key != source_key:
        raise WP15ImportError("Crosswalk source_key mismatch")
    fields_list = contract.get("fields")
    if not isinstance(fields_list,list) or len(fields_list)!=41:
        raise WP15ImportError("WP1.5 contract must contain exactly 41 fields")
    fields = {f["id"]:f for f in fields_list}
    source_to_game = {m.source_id:m.game_id for m in crosswalk.mappings}
    rows = normalized.get("observations")
    if not isinstance(rows,list) or not rows:
        raise WP15ImportError("observations must be a non-empty array")
    valid = [_validate_row(r,i,fields,source_key,set(source_to_game)) for i,r in enumerate(rows)]
    keys=set()
    for row in valid:
        key=(source_to_game[row["source_id"]],row["field_id"])
        if key in keys:
            raise WP15ImportError(f"Duplicate country/field observation: {key}")
        keys.add(key)

    from datetime import datetime, timezone
    retrieved = manifest["retrieved_at"]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
    con=connect_database(database_path)
    try:
        apply_migrations(con)
        con.execute("BEGIN IMMEDIATE")
        known={r["game_id"] for r in con.execute("SELECT game_id FROM countries")}
        unknown=sorted(set(source_to_game.values())-known)
        if unknown:
            raise WP15ImportError(f"Crosswalk game IDs absent from canonical database: {unknown}")
        found=con.execute("SELECT * FROM dataset_imports WHERE dataset=? AND sha256=?",(source_key,digest)).fetchall()
        metadata=(release,manifest["final_url"],retrieved,manifest.get("attribution"),manifest.get("license_status"),"candidate")
        if len(found)>1:
            raise WP15ImportError("Duplicate dataset import rows for source checksum")
        if found:
            import_id=int(found[0]["import_id"])
            actual=tuple(found[0][k] for k in ("source_version","source_url","retrieval_date","attribution","license","import_status"))
            if actual!=metadata:
                raise WP15ImportError("Existing dataset provenance conflicts with manifest")
        else:
            cur=con.execute("""INSERT INTO dataset_imports
                (dataset,source_version,source_url,retrieval_date,sha256,attribution,license,import_status,imported_at)
                VALUES (?,?,?,?,?,?,?,'candidate',?)""",
                (source_key,release,manifest["final_url"],retrieved,digest,manifest.get("attribution"),manifest.get("license_status"),now))
            import_id=int(cur.lastrowid)
        mapping_count=0
        for m in crosswalk.mappings:
            old=con.execute("SELECT game_id,is_current FROM country_sources WHERE dataset=? AND source_id=?",(source_key,m.source_id)).fetchone()
            if old is None:
                con.execute("INSERT INTO country_sources(game_id,dataset,source_id,is_current,import_id) VALUES(?,?,?,1,?)",(m.game_id,source_key,m.source_id,import_id))
            elif old["game_id"]!=m.game_id or old["is_current"]!=1:
                raise WP15ImportError(f"Existing provider mapping conflicts for {source_key}/{m.source_id}")
            mapping_count+=1
        scalar=structured=0
        for r in valid:
            game_id=source_to_game[r["source_id"]]; field=r["field"]; key=field["key"]
            if field["storage"]=="scalar":
                expected=(r["value"],r["unit"],r["period"],r["status"],r["reference"],release,r["method"],retrieved,import_id)
                old=con.execute("""SELECT value,unit,observation_period,value_status,source_reference,source_version,methodology,retrieved_at,import_id
                    FROM current_statistics WHERE game_id=? AND statistic_key=?""",(game_id,key)).fetchone()
                if old is None:
                    con.execute("""INSERT INTO current_statistics(game_id,statistic_key,value,unit,observed_at,observation_period,value_status,source_reference,source_version,methodology,retrieved_at,import_id)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",(game_id,key,r["value"],r["unit"],r["period"],r["period"],r["status"],r["reference"],release,r["method"],retrieved,import_id))
                elif tuple(old)!=expected:
                    raise WP15ImportError(f"Existing scalar observation conflicts for {game_id}/{key}")
                scalar+=1
            else:
                payload=_canonical(r["value"])
                expected=(payload,r["status"],r["period"],r["reference"],release,r["method"],retrieved,import_id)
                old=con.execute("""SELECT payload_json,value_status,observation_period,source_reference,source_version,methodology,retrieved_at,import_id
                    FROM selected_game_data WHERE game_id=? AND data_category='wp1_5' AND data_key=?""",(game_id,key)).fetchone()
                if old is None:
                    con.execute("""INSERT INTO selected_game_data(game_id,data_category,data_key,payload_json,import_id,value_status,observation_period,source_reference,source_version,methodology,retrieved_at)
                        VALUES(?,'wp1_5',?,?,?,?,?,?,?,?,?)""",(game_id,key,payload,import_id,r["status"],r["period"],r["reference"],release,r["method"],retrieved))
                elif tuple(old)!=expected:
                    raise WP15ImportError(f"Existing structured observation conflicts for {game_id}/{key}")
                structured+=1
        issues=validate_database(con)
        if issues:
            raise WP15ImportError("Database validation failed: "+"; ".join(issues))
        con.commit()
        return {"source_key":source_key,"release":release,"import_id":import_id,"raw_sha256":digest,
                "country_mappings":mapping_count,"scalar_observations":scalar,"structured_observations":structured}
    except Exception:
        if con.in_transaction: con.rollback()
        raise
    finally:
        con.close()
