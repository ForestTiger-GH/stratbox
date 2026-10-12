#!/usr/bin/env python3
"""Bounded safe 0015 domain source assertions; never emit restricted original text."""
from __future__ import annotations
import json,re
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
REV="8459dc58922b7e8df853cf1d9e8131fa9e132580";BLOB="a2339ebc79f72a075d290b761fda7b8997b15710"
SRC="_mw/epochs-001-strategy-box-development/research/01-old-notes/Патч stratbox Май 2026.md"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/HISTORICAL-PATCH-0015-PUBLIC-SAFE-RESIDUE-04.jsonl"
PERMITTED=["docs/science/data-and-knowledge/format-recognition-and-semantic-support.md","docs/science/data-and-knowledge/source-observation-vintages-and-replay.md"]
def check():
    lines=read_pinned_blob(ROOT,REV,SRC,BLOB).decode("utf-8").splitlines()
    rows=[json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows)==4
    for i,row in enumerate(rows,1):
        uid=f"SB-MAT-0015-PUBLIC-SAFE-{i:02d}"
        assert row["unit_id"]==uid and row["source_id"]=="SB-SRC-0015"
        assert row["source_commit"]==REV and row["source_blob_sha"]==BLOB
        assert row["science_destination"] in PERMITTED
        assert row["source_material_state"]=="unaccounted" and row["independent_review"]=="OPEN"
        m=re.fullmatch(r"L(\d+)-L(\d+)",row["source_span"]);assert m
        a,z=map(int,m.groups());assert a>0 and z<=len(lines) and any(x.strip() for x in lines[a-1:z])
        body=(ROOT/row["science_destination"]).read_text(encoding="utf-8")
        for token in (uid.replace("SB-MAT-0015-","SB-SRC-0015/"),row["epistemic_status"],row["english_research_meaning"],row["defeater_or_limit"],row["source_span"]):
            assert token in body
    return {"verdict":"BOUNDED_PUBLIC_SAFE_TEXT_ONLY","source_id":"SB-SRC-0015","rows":4,"whole_material_state":"unaccounted","independent":"OPEN"}
if __name__=="__main__":print(json.dumps(check(),ensure_ascii=False))
