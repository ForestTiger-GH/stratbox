#!/usr/bin/env python3
"""Historic refactor 0016 whole-original producer sections and exact source routes."""
from __future__ import annotations
import json,re
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
REV="8459dc58922b7e8df853cf1d9e8131fa9e132580";BLOB="d04fece78c89063c2ac2dac775179f1517c7fea9";SRC="_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/HISTORICAL-REFACTOR-0016-WHOLE-RESIDUE-06.jsonl"
REPORT=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/coverage/HISTORICAL-0016-WHOLE-ORIGINAL-PRODUCER-2026-10-12.md"
PERMITTED=["docs/science/architecture/semantic-ownership-and-contract-boundaries.md","docs/science/capabilities/definitions-plans-and-execution-truth.md","docs/science/surfaces/semantic-portability-and-client-authority.md","docs/science/engineering/semantic-ownership-method-transfer-and-proportional-materialization.md"]
def check():
    lines=read_pinned_blob(ROOT,REV,SRC,BLOB).decode("utf-8").splitlines()
    assert len(lines) in (1926,1927)
    assert lines[0].startswith("# ")
    for name in ("# Общий план работ","# Переработка бизнес-логики"):
        assert name in "\n".join(lines)
    entries=[json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(entries)==6
    seen=set()
    for i,e in enumerate(entries,1):
        uid=f"SB-MAT-0016-COMPLETE-{i:02d}"
        assert e["unit_id"]==uid and uid not in seen;seen.add(uid)
        assert e["source_commit"]==REV and e["source_blob_sha"]==BLOB and e["source_id"]=="SB-SRC-0016"
        assert e["science_destination"] in PERMITTED
        assert e["source_material_state"]=="unaccounted" and e["independent_review"]=="OPEN"
        m=re.fullmatch(r"L(\d+)-L(\d+)",e["source_span"]);assert m
        a,z=map(int,m.groups());assert 1<=a<=z<=len(lines) and any(t.strip() for t in lines[a-1:z])
        text=(ROOT/e["science_destination"]).read_text(encoding="utf-8")
        for v in (uid.replace("SB-MAT-0016-","SB-SRC-0016/"),e["epistemic_status"],e["english_research_meaning"],e["defeater_or_limit"],f"#L{a}-L{z}"):
            assert v in text,("public Science missing",uid)
    r=REPORT.read_text(encoding="utf-8")
    for term in ("L1-L199","L1843-L1926","PRODUCER_EXHAUSTIVE_REVIEW_WITH_MAPPED_MATERIAL","different"):
        assert term in r
    return {"verdict":"WHOLE_HISTORICAL_ORIGINAL_PRODUCER_ROUTE_ONLY","source":"SB-SRC-0016","new_rows":6,"source_material_state":"unaccounted","independent_assurance":"OPEN"}
if __name__=="__main__": print(json.dumps(check(),ensure_ascii=False))
