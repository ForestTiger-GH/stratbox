#!/usr/bin/env python3
"""Check seven frozen automation original flows and Science statements (structural)."""
from __future__ import annotations
import json
import re
from pathlib import Path
from pinned_source import read_pinned_blob

ROOT=Path(__file__).resolve().parents[4]
REV="8459dc58922b7e8df853cf1d9e8131fa9e132580"
SHA="dee8958b16b3fe08042b5212d35fcc8424db28e3"
SRC="_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/AUTOMATION-0041-CROSS-CLIENT-FLOWS-07.jsonl"
SCIENCE=ROOT/"docs/science/automation/bounded-agent-routing-and-evidence-safe-automation.md"

def verify():
    lines=read_pinned_blob(ROOT,REV,SRC,SHA).decode("utf-8").splitlines()
    assert len(lines) in (2386,2387)
    entries=[json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(entries)==7
    body=SCIENCE.read_text(encoding="utf-8")
    required=["AIConversationService","AutomationDraft","source.check","frg.cleanup.plan"]
    original_body="\n".join(lines)
    assert all(token in original_body for token in required)
    seen=set()
    for i,entry in enumerate(entries,1):
        uid=f"SB-MAT-0041-FLOW-{i:02d}"
        assert uid==entry["unit_id"] and uid not in seen
        seen.add(uid)
        assert entry["source_id"]=="SB-SRC-0041"
        assert entry["source_commit"]==REV and entry["source_blob_sha"]==SHA
        assert entry["source_material_state"]=="unaccounted" and entry["independent_review"]=="OPEN"
        match=re.fullmatch(r"L(\d+)-L(\d+)",entry["source_span"])
        assert match
        a,z=map(int,match.groups())
        assert 1<=a<=z<=len(lines) and any(v.strip() for v in lines[a-1:z])
        label=uid.replace("SB-MAT-0041-","SB-SRC-0041/")
        for token in (label,entry["epistemic_status"],entry["english_research_meaning"],entry["defeater_or_limit"],f"#L{a}-L{z}"):
            assert token in body,("science source route missing",uid,token)
    return {"verdict":"FROZEN_SOURCE_SPANS_AND_SCIENCE_TEXT_ONLY","source":"SB-SRC-0041","rows":len(entries),"complete_source_disposition":"unaccounted","independent_review":"OPEN"}

if __name__=="__main__":
    print(json.dumps(verify(),ensure_ascii=False))
