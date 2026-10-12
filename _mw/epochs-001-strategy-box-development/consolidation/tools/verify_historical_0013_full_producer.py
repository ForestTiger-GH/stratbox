#!/usr/bin/env python3
"""Full 0013 original producer section routes: structural guard, not external assurance."""
from __future__ import annotations
import json,re
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
REV="8459dc58922b7e8df853cf1d9e8131fa9e132580"
BLOB="2f2b05d1a1af3401fb402bfb43c8cc36a907d9fe"
SRC="_mw/epochs-001-strategy-box-development/research/01-old-notes/Интерфейс Strategy Box.md"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/HISTORICAL-UX-0013-FULL-RESIDUE-06.jsonl"
SCIENCE=ROOT/"docs/science/surfaces/explorer-workroom-and-operational-desktop-interaction.md"
REPORT=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/coverage/HISTORICAL-0013-WHOLE-ORIGINAL-PRODUCER-2026-10-12.md"
def check():
    lines=read_pinned_blob(ROOT,REV,SRC,BLOB).decode("utf-8").splitlines()
    assert len(lines)==178
    source="\n".join(lines)
    for i in range(1,16):
        assert re.search(rf"(?m)^## {i}\.\s",source),f"missing heading {i}"
    rows=[json.loads(t) for t in LEDGER.read_text(encoding="utf-8").splitlines() if t.strip()]
    assert len(rows)==6
    body=SCIENCE.read_text(encoding="utf-8")
    for i,row in enumerate(rows,1):
        uid=f"SB-MAT-0013-UX-RESIDUE-{i:02d}"
        assert row["unit_id"]==uid
        assert row["source_id"]=="SB-SRC-0013" and row["source_commit"]==REV and row["source_blob_sha"]==BLOB
        assert row["source_material_state"]=="unaccounted" and row["independent_review"]=="OPEN"
        m=re.fullmatch(r"L(\d+)-L(\d+)",row["source_span"]);assert m
        a,z=map(int,m.groups());assert 1<=a<=z<=len(lines)
        for token in (uid.replace("SB-MAT-0013-","SB-SRC-0013/"),row["epistemic_status"],row["english_research_meaning"],row["defeater_or_limit"],f"#L{a}-L{z}"):
            assert token in body,("missing public Science claim",uid,token)
    report=REPORT.read_text(encoding="utf-8")
    for name in ("Visual style","Scenario chat","Background process visuals","Minimum desktop composition","User journey"):
        assert name in report
    assert "PRODUCER_EXHAUSTIVE_REVIEW_WITH_MAPPED_MATERIAL" in report
    return {"scope":"SB-SRC-0013","verdict":"PRODUCER_SOURCE_SECTIONS_AND_TEXT_ONLY","rows_new":6,"old_rows_reused":36,"full_source_review_claim":"PRODUCER_ONLY","material_unit_state":"unaccounted","independent":"OPEN"}
if __name__=="__main__":
    print(json.dumps(check(),ensure_ascii=False))
