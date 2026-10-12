#!/usr/bin/env python3
"""Check two full historical SORS original source texts and mapped science topics."""
from __future__ import annotations
import csv,json,re
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
REV="8459dc58922b7e8df853cf1d9e8131fa9e132580"
CENSUS=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/sources/CENSUS.csv"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/SORS-ACCEPTANCE-ARCHITECTURE-09.jsonl"
SCIENCE=ROOT/"docs/science/data-and-knowledge/sors-evidence-surfaces-crosswalk-and-audit.md"
def verify():
    with CENSUS.open(encoding="utf-8",newline="") as f:
        census={v["source_id"]:v for v in csv.DictReader(f)}
    entries=[json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(entries)==9 and {x["source_id"] for x in entries}=={"SB-SRC-0066","SB-SRC-0067"}
    for sid in ("SB-SRC-0066","SB-SRC-0067"):
        assert census[sid]["read_state"]=="full_read" and census[sid]["material_unit_state"]=="unaccounted"
    for i,record in enumerate(entries,1):
        assert record["unit_id"]==f"SB-MAT-SORS-ACCEPT-{i:02d}"
        assert record["source_commit"]==REV and record["source_path"]==census[record["source_id"]]["path"]
        assert record["source_blob_sha"]==census[record["source_id"]]["blob_sha"]
        lines=read_pinned_blob(ROOT,REV,record["source_path"],record["source_blob_sha"]).decode("utf-8").splitlines()
        match=re.fullmatch(r"L(\d+)(?:-L(\d+))?",record["source_span"]);assert match
        lo=int(match.group(1));hi=int(match.group(2) or lo)
        assert 1<=lo<=hi<=len(lines) and any(s.strip() for s in lines[lo-1:hi])
        assert record["source_material_state"]=="unaccounted" and record["independent_review"]=="OPEN"
        assert record["science_destination"]=="docs/science/data-and-knowledge/sors-evidence-surfaces-crosswalk-and-audit.md"
    body=SCIENCE.read_text(encoding="utf-8")
    for part in ("25 acceptance conditions","85 regional atoms","88 real OKVED2","Udmurtia","fixed point","zero remains possible","whole-model"):
        assert part.lower() in body.lower(),part
    print(json.dumps({"verdict":"TWO_HISTORICAL_SORS_FULL_READS_AND_SCIENCE_CLAIM_ROUTES_ONLY","full_read_records":2,"source_rows":9,"semantic_lossless":"NOT_CERTIFIED"}))
if __name__=="__main__":verify()
