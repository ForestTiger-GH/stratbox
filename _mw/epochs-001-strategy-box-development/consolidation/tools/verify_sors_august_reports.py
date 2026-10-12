#!/usr/bin/env python3
"""Recheck three historical SORS implementation reports' pinned complete reads."""
from __future__ import annotations
import csv,json,re
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
REV="8459dc58922b7e8df853cf1d9e8131fa9e132580"
CENSUS=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/sources/CENSUS.csv"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/SORS-AUGUST-REPORTS-12.jsonl"
SCIENCE=ROOT/"docs/science/data-and-knowledge/sors-evidence-surfaces-crosswalk-and-audit.md"
def verify():
    with CENSUS.open(encoding="utf-8",newline="") as f:
        refs={x["source_id"]:x for x in csv.DictReader(f)}
    rows=[json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows)==12
    assert {x["source_id"] for x in rows}=={"SB-SRC-0071","SB-SRC-0072","SB-SRC-0073"}
    for sid in ("SB-SRC-0071","SB-SRC-0072","SB-SRC-0073"):
        assert refs[sid]["read_state"]=="full_read" and refs[sid]["material_unit_state"]=="unaccounted"
    for i,x in enumerate(rows,1):
        assert x["unit_id"]==f"SB-MAT-SORS-REPORT-{i:02d}"
        assert x["source_commit"]==REV and x["source_path"]==refs[x["source_id"]]["path"]
        assert x["source_blob_sha"]==refs[x["source_id"]]["blob_sha"]
        lines=read_pinned_blob(ROOT,REV,x["source_path"],x["source_blob_sha"]).decode("utf-8").splitlines()
        match=re.fullmatch(r"L(\d+)(?:-L(\d+))?",x["source_span"]);assert match
        a=int(match.group(1));z=int(match.group(2) or a)
        assert 1<=a<=z<=len(lines) and any(t.strip() for t in lines[a-1:z])
        assert x["science_destination"]=="docs/science/data-and-knowledge/sors-evidence-surfaces-crosswalk-and-audit.md"
        assert x["source_material_state"]=="unaccounted" and x["independent_review"]=="OPEN"
    text=SCIENCE.read_text(encoding="utf-8")
    for token in ("135 touches","global feasible set","Udmurtia","1,571,680","not a deployment service-level objective","64 unit/domain","highspy"):
        assert token.lower() in text.lower(),token
    print(json.dumps({"verdict":"THREE_COMPLETE_HISTORIC_SORS_REPORT_READS_AND_SOURCE_TIER_CLAIMS","sources":3,"units":12,"independent_review":"OPEN"}))
if __name__=="__main__":verify()
