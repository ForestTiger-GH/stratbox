#!/usr/bin/env python3
"""Verify six fully read SORS legacy notes map bounded scientific claims."""
from __future__ import annotations
import csv,json,re
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
REV="8459dc58922b7e8df853cf1d9e8131fa9e132580"
CENSUS=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/sources/CENSUS.csv"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/SORS-LEGACY-TECHNICAL-NOTES-08.jsonl"
SCIENCE=ROOT/"docs/science/data-and-knowledge/sors-evidence-surfaces-crosswalk-and-audit.md"
def check():
    with CENSUS.open(encoding="utf-8",newline="") as f:
        census={r["source_id"]:r for r in csv.DictReader(f)}
    rows=[json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows)==8
    source_ids={x["source_id"] for x in rows}
    assert len(source_ids)==6
    for sid in source_ids:
        assert census[sid]["read_state"]=="full_read"
        assert census[sid]["material_unit_state"]=="unaccounted"
    body=SCIENCE.read_text(encoding="utf-8")
    for i,r in enumerate(rows,1):
        assert r["unit_id"]==f"SB-MAT-SORS-LEGACY-{i:02d}"
        assert r["source_commit"]==REV and r["source_id"] in source_ids
        assert r["source_path"]==census[r["source_id"]]["path"]
        assert r["source_blob_sha"]==census[r["source_id"]]["blob_sha"]
        lines=read_pinned_blob(ROOT,REV,r["source_path"],r["source_blob_sha"]).decode("utf-8").splitlines()
        span=re.fullmatch(r"L(\d+)(?:-L(\d+))?",r["source_span"])
        assert span is not None
        a=int(span.group(1)); z=int(span.group(2) or a)
        assert 1<=a<=z<=len(lines) and any(s.strip() for s in lines[a-1:z])
        assert r["science_destination"]=="docs/science/data-and-knowledge/sors-evidence-surfaces-crosswalk-and-audit.md"
        assert r["source_material_state"]=="unaccounted" and r["independent_review"]=="OPEN"
    for phrase in ("June 1, 2026","fixed point","global feasibility","primary facts","supersede","upper-open interval"):
        assert phrase.lower() in body.lower(),phrase
    return {"verdict":"SIX_FULL_READ_LEGACY_SOURCE_BLOBS_AND_8_BOUNDED_SCIENCE_ROUTES","legacy_sources":len(source_ids),"meaning_rows":len(rows),"whole_material_disposition":"unaccounted","independent_review":"OPEN"}
if __name__=="__main__":print(json.dumps(check()))
