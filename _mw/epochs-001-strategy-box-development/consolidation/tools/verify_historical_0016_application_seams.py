#!/usr/bin/env python3
"""Historic 0016 seven source-bound semantic seam assertions: structural only."""
from __future__ import annotations
import json,re
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
REV="8459dc58922b7e8df853cf1d9e8131fa9e132580";BLOB="d04fece78c89063c2ac2dac775179f1517c7fea9";SOURCE="_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/HISTORICAL-REFACTOR-0016-APPLICATION-SEAMS-07.jsonl"
PERMITTED=["docs/science/architecture/semantic-ownership-and-contract-boundaries.md","docs/science/capabilities/definitions-plans-and-execution-truth.md","docs/science/work/admission-planning-resource-scheduling-and-recovery.md"]
def verify():
    lines=read_pinned_blob(ROOT,REV,SOURCE,BLOB).decode("utf-8").splitlines()
    assert len(lines) in (1926,1927)
    rows=[json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows)==7
    for i,row in enumerate(rows,1):
        unit=f"SB-MAT-0016-SEAM-{i:02d}"
        assert row["unit_id"]==unit and row["source_id"]=="SB-SRC-0016"
        assert row["source_commit"]==REV and row["source_blob_sha"]==BLOB
        assert row["source_material_state"]=="unaccounted" and row["independent_review"]=="OPEN"
        assert row["science_destination"] in PERMITTED
        m=re.fullmatch(r"L(\d+)-L(\d+)",row["source_span"]);assert m
        a,z=map(int,m.groups());assert 1<=a<=z<=len(lines)
        text=(ROOT/row["science_destination"]).read_text(encoding="utf-8")
        for token in (unit.replace("SB-MAT-0016-","SB-SRC-0016/"),row["english_research_meaning"],row["epistemic_status"],row["defeater_or_limit"],f"#L{a}-L{z}"):
            assert token in text
    return {"source":"SB-SRC-0016","verdict":"FROZEN_HISTORICAL_SOURCE_TEXT_ONLY","rows":len(rows),"whole_source_material_state":"unaccounted","independent":"OPEN"}
if __name__=="__main__":print(json.dumps(verify(),ensure_ascii=False))
