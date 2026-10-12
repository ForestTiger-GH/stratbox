#!/usr/bin/env python3
"""Historical original 0014 producer whole-source route check; structural only."""
from __future__ import annotations
import json,re
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
REV="8459dc58922b7e8df853cf1d9e8131fa9e132580"; SHA="c10ee7d96f24996f6480d95adf2b005c0651122e"; SRC="_mw/epochs-001-strategy-box-development/research/01-old-notes/О приложении Strategy Box.md"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/HISTORICAL-APPLICATION-0014-ROADMAP-DETAIL-05.jsonl"
SCIENCE=ROOT/"docs/science/deployment/headless-host-web-security-and-persistence-tradeoffs.md"
REPORT=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/coverage/HISTORICAL-0014-WHOLE-ORIGINAL-PRODUCER-2026-10-12.md"
def check():
    lines=read_pinned_blob(ROOT,REV,SRC,SHA).decode("utf-8").splitlines()
    assert len(lines)==124
    assert lines[0].startswith("# 1.") and "# 2." in "\n".join(lines)
    for k in range(1,17):
        assert f"Этап {k}." in "\n".join(lines),k
    ls=LEDGER.read_text(encoding="utf-8").splitlines()
    entries=[json.loads(x) for x in ls if x.strip()]
    assert len(entries)==5
    sci=SCIENCE.read_text(encoding="utf-8")
    for k,e in enumerate(entries,1):
        uid=f"SB-MAT-0014-ROAD-DETAIL-{k:02d}"
        assert e["unit_id"]==uid and e["source_id"]=="SB-SRC-0014"
        assert e["source_commit"]==REV and e["source_blob_sha"]==SHA
        assert e["source_material_state"]=="unaccounted" and e["independent_review"]=="OPEN"
        match=re.fullmatch(r"L(\d+)-L(\d+)",e["source_span"]);assert match
        a,z=map(int,match.groups());assert 1<=a<=z<=len(lines)
        for v in (uid.replace("SB-MAT-0014-","SB-SRC-0014/"),e["epistemic_status"],e["english_research_meaning"],e["defeater_or_limit"],f"#L{a}-L{z}"):
            assert v in sci,("missing Science",uid)
    txt=REPORT.read_text(encoding="utf-8")
    for x in ("PRODUCER_EXHAUSTIVE_REVIEW_WITH_MAPPED_MATERIAL","Stages 14–15","Stage 16","independent"):
        assert x in txt
    return {"status":"WHOLE_SOURCE_PRODUCER_REVIEW_ONLY","source":"SB-SRC-0014","old_rows_reused":16,"new_rows":5,"source_material_state":"unaccounted","independent":"OPEN"}
if __name__=="__main__":print(json.dumps(check(),ensure_ascii=False))
