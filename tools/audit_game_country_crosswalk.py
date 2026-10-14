#!/usr/bin/env python3
"""Read-only audit of Natural Earth metadata against legacy Godot game data."""
from __future__ import annotations
import argparse, json, re, sys, unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

REGIONS = {
 "asia": ("MapAsia_Countries.json","MapAsia_ColorMap.json","MapAsia_Questions.json"),
 "europe": ("MapEurope_Countries.json","MapEurope_ColorMap.json","MapEurope_Questions.json"),
 "america": ("MapAmerica_Countries.json","MapAmerica_ColorMap.json","MapAmerica_Questions.json"),
 "africa": ("MapAfrica_Countries.json","MapAfrica_ColorMap.json","MapAfrica_Questions.json"),
}
GLOBAL = ("Flag_Data.json","Flag_Translation.json","GeneralInfo_CountriesCapitals.json",
          "GeneralInfo_Questions.json","Country_Aliases.json")

def norm(value: Any) -> str:
    s=unicodedata.normalize("NFKC",str(value)).strip().replace("ي","ی").replace("ك","ک")
    s=s.replace("\u200c","").replace("\u200f","").replace("\u200e","")
    return re.sub(r"\s+","",s).casefold()

def load(path: Path) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e: raise ValueError(f"required file not found: {path}") from e
    except json.JSONDecodeError as e: raise ValueError(f"invalid JSON in {path}: {e}") from e

def audit(asset_data: Path, game_root: Path) -> dict[str, Any]:
    metadata=load(asset_data/"countries.json")
    countries=metadata.get("countries")
    if not isinstance(countries,list): raise ValueError("countries.json must contain a countries array")
    gd=game_root/"Asset"/"Data"
    data={}
    for name in GLOBAL: data[name]=load(gd/name)
    for files in REGIONS.values():
        for name in files: data[name]=load(gd/name)
    labels=defaultdict(list)
    def add(value,source,region=""):
        if isinstance(value,str) and value.strip():
            labels[norm(value)].append({"label":value,"source":source,"region":region})
    for region,(cf,mf,qf) in REGIONS.items():
        for label in data[cf]: add(label,cf,region)
        for item in data[mf].values():
            if isinstance(item,list) and item: add(item[0],mf,region)
        for i,q in enumerate(data[qf]):
            if isinstance(q,dict):
                add(q.get("answer"),f"{qf}#{i}:answer",region)
                for choice in q.get("choices",[]): add(choice,f"{qf}#{i}:choice",region)
    for tier,items in data["Flag_Data.json"].items():
        if isinstance(items,list):
            for label in items: add(label,f"Flag_Data.json:{tier}")
    for en,fa in data["Flag_Translation.json"].items():
        add(en,"Flag_Translation.json:English"); add(fa,"Flag_Translation.json:Persian")
    for i,q in enumerate(data["GeneralInfo_Questions.json"]):
        if isinstance(q,dict):
            add(q.get("answer"),f"GeneralInfo_Questions.json#{i}:answer")
            for choice in q.get("choices",[]): add(choice,f"GeneralInfo_Questions.json#{i}:choice")
    for region,tiers in data["GeneralInfo_CountriesCapitals.json"].items():
        if isinstance(tiers,dict):
            for tier,pairs in tiers.items():
                if isinstance(pairs,list):
                    for i,pair in enumerate(pairs):
                        if isinstance(pair,list) and pair: add(pair[0],f"GeneralInfo_CountriesCapitals.json:{region}:{tier}#{i}",region)
    for region,aliases in data["Country_Aliases.json"].items():
        if not region.startswith("_") and isinstance(aliases,dict):
            for alias,target in aliases.items():
                add(alias,"Country_Aliases.json:alias",region); add(target,"Country_Aliases.json:target",region)

    # English asset name -> existing game English/Persian flag translation -> Persian game labels.
    fa_to_en=defaultdict(set)
    for en,fa in data["Flag_Translation.json"].items():
        if isinstance(en,str) and isinstance(fa,str): fa_to_en[norm(fa)].add(norm(en))
    # Build a source-name index from the processed asset dataset itself. The
    # game repository contributes labels for audit only; it never defines asset
    # identities or source metadata.
    source_name_to_ids=defaultdict(set)
    asset_rows=[]
    for c in countries:
        sid=str(c.get("id",""))
        attrs=c.get("source_attributes",{})
        raw_names={c.get("name"),attrs.get("ADMIN"),attrs.get("NAME"),attrs.get("NAME_LONG")}
        if isinstance(c.get("aliases"),list): raw_names.update(c["aliases"])
        names={norm(n) for n in raw_names if isinstance(n,str) and n.strip()}
        for name in names: source_name_to_ids[name].add(sid)
        persian=set()
        for fa,ens in fa_to_en.items():
            if names & ens: persian.add(fa)
        asset_rows.append({"source_id":sid,"name":c.get("name"),"iso3_candidate":c.get("iso3"),
                           "regions":c.get("regions",[]),"source_name_candidates":sorted(names),
                           "legacy_persian_labels_from_flag_translation":sorted(persian),
                           "review_status":"needs_human_review"})
    def candidates_for_label(normalized_label):
        # Match either a normalized source name directly (including English
        # game labels) or a Persian label translated by the legacy dictionary
        # to an English name present in the source-derived asset dataset.
        ids=set(source_name_to_ids.get(normalized_label,set()))
        for english_name in fa_to_en.get(normalized_label,set()):
            ids.update(source_name_to_ids.get(english_name,set()))
        return ids
    game_rows=[]
    for n,occ in sorted(labels.items()):
        ids=sorted(candidates_for_label(n))
        game_rows.append({"normalized_label":n,"labels":sorted({o["label"] for o in occ}),
            "sources":sorted({o["source"] for o in occ}),"regions":sorted({o["region"] for o in occ if o["region"]}),
            "asset_source_id_candidates":ids,
            "match_status":"ambiguous_candidate" if len(ids)>1 else "candidate_needs_review" if ids else "unmatched"})
    region_audits={}
    for region,(cf,mf,qf) in REGIONS.items():
        catalog={norm(x):x for x in data[cf]}
        color={norm(v[0]):v[0] for v in data[mf].values() if isinstance(v,list) and v and isinstance(v[0],str)}
        answers=[q.get("answer") for q in data[qf] if isinstance(q,dict) and isinstance(q.get("answer"),str)]
        catalog_candidates=[]
        for normalized,label in sorted(catalog.items()):
            ids=sorted(candidates_for_label(normalized))
            catalog_candidates.append({"label":label,"asset_source_id_candidates":ids,
                "match_status":"ambiguous_candidate" if len(ids)>1 else "candidate_needs_review" if ids else "unmatched"})
        region_audits[region]={"catalog_entries":len(data[cf]),"color_map_entries":len(data[mf]),
            "question_count":len(data[qf]),"catalog_labels_missing_from_color_map":sorted(catalog[n] for n in catalog.keys()-color.keys()),
            "color_map_labels_missing_from_catalog":sorted(color[n] for n in color.keys()-catalog.keys()),
            "question_answers_missing_from_catalog":sorted({a for a in answers if norm(a) not in catalog}),
            "country_catalog_candidate_matches":catalog_candidates,
            "country_catalog_unmatched_labels":[row["label"] for row in catalog_candidates if row["match_status"]=="unmatched"],
            "country_catalog_ambiguous_labels":[row["label"] for row in catalog_candidates if row["match_status"]=="ambiguous_candidate"]}
    name_ids=defaultdict(set)
    for country in countries:
        attrs=country.get("source_attributes",{})
        for name in (country.get("name"),attrs.get("ADMIN"),attrs.get("NAME"),attrs.get("NAME_LONG")):
            if isinstance(name,str) and name.strip(): name_ids[norm(name)].add(str(country.get("id","")))
    duplicate_names=[{"normalized_name":name,"source_ids":sorted(ids)}
                     for name,ids in sorted(name_ids.items()) if len(ids)>1]
    return {"schema_version":1,"report_type":"read_only_game_country_crosswalk_audit",
      "asset_country_count":len(countries),"game_label_count":len(game_rows),"asset_countries":asset_rows,
      "game_labels":game_rows,"region_audits":region_audits,"duplicate_asset_name_candidates":duplicate_names,
      "summary":{"matched_candidate_labels":sum(r["match_status"]=="candidate_needs_review" for r in game_rows),
       "ambiguous_candidate_labels":sum(r["match_status"]=="ambiguous_candidate" for r in game_rows),
       "unmatched_game_labels_all_sources":sum(r["match_status"]=="unmatched" for r in game_rows),
       "country_catalog_labels_total":sum(v["catalog_entries"] for v in region_audits.values()),
       "country_catalog_labels_with_single_candidate":sum(row["match_status"]=="candidate_needs_review" for v in region_audits.values() for row in v["country_catalog_candidate_matches"]),
       "country_catalog_labels_unmatched":sum(len(v["country_catalog_unmatched_labels"]) for v in region_audits.values()),
       "country_catalog_labels_ambiguous":sum(len(v["country_catalog_ambiguous_labels"]) for v in region_audits.values()),
       "region_catalogs_with_catalog_color_differences":sum(bool(v["catalog_labels_missing_from_color_map"] or v["color_map_labels_missing_from_catalog"]) for v in region_audits.values()),
       "regions_with_question_answers_missing_from_catalog":sum(bool(v["question_answers_missing_from_catalog"]) for v in region_audits.values()),
       "warning":"All proposed matches require human review. Source IDs are not approved game country IDs; ISO syntax alone does not verify an ISO assignment."}}

def markdown(r: dict[str,Any]) -> str:
    s=r["summary"]; lines=["# Game country crosswalk audit","","Read-only report. Candidate matches are not approved mappings.","",
      "## Summary","",f"- Asset records: {r['asset_country_count']}",f"- Distinct normalized game labels: {r['game_label_count']}",
      f"- Single-candidate labels requiring review: {s['matched_candidate_labels']}",f"- Ambiguous candidate labels: {s['ambiguous_candidate_labels']}",
      f"- Unmatched labels across all collected game text (includes quiz text, aliases, capitals, and other labels): {s['unmatched_game_labels_all_sources']}",
      f"- Regional country-catalog labels: {s['country_catalog_labels_total']}",
      f"- Country-catalog labels with a single candidate requiring review: {s['country_catalog_labels_with_single_candidate']}",
      f"- Country-catalog labels unmatched by the current bridge: {s['country_catalog_labels_unmatched']}",
      f"- Country-catalog labels with ambiguous candidates: {s['country_catalog_labels_ambiguous']}",
      f"- Regions with catalog/color-map differences: {s['region_catalogs_with_catalog_color_differences']}",
      f"- Regions with question answers absent from catalog: {s['regions_with_question_answers_missing_from_catalog']}","",
      f"Warning: {s['warning']}","","## Per-region checks","","| Region | Catalog | Color map | Questions | Catalog labels absent from map | Map labels absent from catalog | Answers absent from catalog |",
      "|---|---:|---:|---:|---:|---:|---:|"]
    for region,v in r["region_audits"].items():
        lines.append(f"| {region} | {v['catalog_entries']} | {v['color_map_entries']} | {v['question_count']} | {len(v['catalog_labels_missing_from_color_map'])} | {len(v['color_map_labels_missing_from_catalog'])} | {len(v['question_answers_missing_from_catalog'])} |")
    lines += ["","## Exact regional country-catalog/color-map differences",""]
    for region,v in r["region_audits"].items():
        lines.append(f"### {region.title()}")
        lines.append(f"- Country catalog labels absent from color map: {', '.join(v['catalog_labels_missing_from_color_map']) or 'none'}")
        lines.append(f"- Color-map labels absent from country catalog: {', '.join(v['color_map_labels_missing_from_catalog']) or 'none'}")
        lines.append(f"- Unmatched country-catalog labels: {', '.join(v['country_catalog_unmatched_labels']) or 'none'}")
        lines.append(f"- Ambiguous country-catalog labels: {', '.join(v['country_catalog_ambiguous_labels']) or 'none'}")
        lines.append("")
    lines += ["## Unmatched and ambiguous labels across all game text","",
      "This section includes quiz choices/answers, aliases, capitals, translations, and map labels; an unmatched item is not necessarily a country.",""]
    for row in r["game_labels"]:
        if row["match_status"] in ("unmatched","ambiguous_candidate"):
            lines.append(f"- {', '.join(row['labels'])} ({', '.join(row['regions']) or 'global'}): {row['match_status']}; candidate source IDs: {', '.join(row['asset_source_id_candidates']) or 'none'}")
    lines += ["","## Single-candidate suggestions","",
      "These are exact normalized Persian matches reached through Flag_Translation.json. They are suggestions only.","",
      "| Game label | Region | Candidate source ID |","|---|---|---|"]
    for row in r["game_labels"]:
        if row["match_status"]=="candidate_needs_review":
            lines.append(f"| {', '.join(row['labels'])} | {', '.join(row['regions']) or 'global'} | {', '.join(row['asset_source_id_candidates'])} |")
    lines += ["","## Interpretation","",
      "- The source-derived asset ID is not automatically a game country ID.",
      "- ISO candidates require independent assignment/provenance review.",
      "- Catalog, color-map, and question discrepancies are reported, not repaired.",
      "- Iran's province/city dataset is intentionally excluded from country matching.",
      "- Review territories, dependencies, constituent countries, and disputed entities explicitly.",""]
    return "\n".join(lines)

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--asset-data",type=Path,default=Path("generated/town_country_asset"))
    p.add_argument("--game-root",type=Path,required=True,help="TownCountryGame checkout root")
    p.add_argument("--output-dir",type=Path,default=Path("reports/country-crosswalk-audit"))
    a=p.parse_args()
    try:
        r=audit(a.asset_data,a.game_root); a.output_dir.mkdir(parents=True,exist_ok=True)
        (a.output_dir/"country-crosswalk-audit.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (a.output_dir/"country-crosswalk-audit.md").write_text(markdown(r),encoding="utf-8")
    except Exception as e:
        print(f"Country crosswalk audit failed: {e}",file=sys.stderr); return 1
    print(f"Country crosswalk audit written to {a.output_dir}")
    print(json.dumps(r["summary"],ensure_ascii=False,indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
