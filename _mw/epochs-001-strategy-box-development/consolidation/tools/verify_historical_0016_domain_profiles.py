#!/usr/bin/env python3
"""Exact pinned historical 0016 domain profiles: text-route producer check only."""
from __future__ import annotations
import json,re
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
REV="8459dc58922b7e8df853cf1d9e8131fa9e132580"; BLOB="d04fece78c89063c2ac2dac775179f1517c7fea9"; ORIGINAL="_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/HISTORICAL-REFACTOR-0016-DOMAIN-PROFILES-08.jsonl"
PERMITTED=["docs/science/capabilities/definitions-plans-and-execution-truth.md","docs/science/data-and-knowledge/format-recognition-and-semantic-support.md","docs/science/artifacts/output-identity-publication-and-availability.md"]
def verify():
    lines=read_pinned_blob(ROOT,REV,ORIGINAL,BLOB).decode("utf-8").splitlines()
    assert len(lines) in (1926,1927)
    rows=[json.loads(t) for t in LEDGER.read_text(encoding="utf-8").splitlines() if t.strip()]
    assert len(rows)==8
    seen=set()
    for i,row in enumerate(rows,1):
        uid=f"SB-MAT-0016-DOMAIN-{i:02d}"
        assert row["unit_id"]==uid and uid not in seen
        seen.add(uid)
        assert row["source_commit"]==REV and row["source_blob_sha"]==BLOB
        assert row["source_id"]=="SB-SRC-0016"
        assert row["source_material_state"]=="unaccounted" and row["independent_review"]=="OPEN"
        assert row["science_destination"] in PERMITTED
        match=re.fullmatch(r"L(\d+)-L(\d+)",row["source_span"]);assert match
        a,z=map(int,match.groups())
        assert 1<=a<=z<=len(lines) and any(t.strip() for t in lines[a-1:z])
        body=(ROOT/row["science_destination"]).read_text(encoding="utf-8")
        for token in (uid.replace("SB-MAT-0016-","SB-SRC-0016/"),row["epistemic_status"],row["english_research_meaning"],row["defeater_or_limit"],f"#L{a}-L{z}"):
            assert token in body,(uid,"missing destination")
    return {"verdict":"FROZEN_HISTORIC_SOURCE_TO_SCIENCE_TEXT_ONLY","rows":8,"source":"SB-SRC-0016","material_disposition":"unaccounted","independent_assurance":"OPEN"}
if __name__=="__main__": print(json.dumps(verify(),ensure_ascii=False))
