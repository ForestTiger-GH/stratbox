#!/usr/bin/env python3
"""Prove three full-read legacy public-neutral notes and bounded Science meaning."""
from __future__ import annotations
import csv,json,re
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
REV="8459dc58922b7e8df853cf1d9e8131fa9e132580"
CENSUS=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/sources/CENSUS.csv"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/CORE-LEGACY-PUBLIC-READS-05.jsonl"
SCIENCE=ROOT/"docs/science/architecture/semantic-ownership-and-contract-boundaries.md"
def check():
    with CENSUS.open(encoding="utf-8",newline="") as f:
        sources={r["source_id"]:r for r in csv.DictReader(f)}
    rows=[json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows)==5
    ids={x["source_id"] for x in rows}
    assert ids=={"SB-SRC-0065","SB-SRC-0078","SB-SRC-0079"}
    for sid in ids:
        assert sources[sid]["read_state"]=="full_read"
        assert sources[sid]["material_unit_state"]=="unaccounted"
    for i,row in enumerate(rows,1):
        assert row["unit_id"]==f"SB-MAT-CORE-LEGACY-{i:02d}"
        assert row["source_commit"]==REV and row["source_path"]==sources[row["source_id"]]["path"]
        assert row["source_blob_sha"]==sources[row["source_id"]]["blob_sha"]
        lines=read_pinned_blob(ROOT,REV,row["source_path"],row["source_blob_sha"]).decode("utf-8").splitlines()
        m=re.fullmatch(r"L(\d+)(?:-L(\d+))?",row["source_span"]);assert m
        a=int(m.group(1));z=int(m.group(2) or a)
        assert 1<=a<=z<=len(lines) and any(s.strip() for s in lines[a-1:z])
        assert row["source_material_state"]=="unaccounted" and row["independent_review"]=="OPEN"
    body=SCIENCE.read_text(encoding="utf-8")
    for word in ("notebooks","dependency direction","independent consumption","editable","source-independent"):
        # 'source-independent' is part of the publication status, not a proof.
        assert word.lower() in body.lower(),word
    print(json.dumps({"verdict":"PINNED_THREE_LEGACY_FULL_READS_AND_PRODUCER_SCIENCE_ONLY","records":3,"meaning_rows":5,"material_state":"unaccounted","independent_review":"OPEN"}))
if __name__=="__main__":check()
