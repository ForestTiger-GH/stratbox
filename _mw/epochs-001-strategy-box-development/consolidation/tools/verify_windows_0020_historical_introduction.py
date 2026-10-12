#!/usr/bin/env python3
"""Pinned whole introductory Windows Research 0020 source position bounds, producer."""
from __future__ import annotations
import json,re
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
REV="8459dc58922b7e8df853cf1d9e8131fa9e132580"
SHA="225128f2599f0792422c0b31cb3cbe1437991ced"
SOURCE="_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/WINDOWS-0020-HISTORICAL-SNAPSHOT-10.jsonl"
SCIENCE=ROOT/"docs/science/surfaces/semantic-portability-and-client-authority.md"
HOW=ROOT/"docs/current-how/windows-application.md"
def check():
    lines=read_pinned_blob(ROOT,REV,SOURCE,SHA).decode("utf-8").splitlines()
    entries=[json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(entries)==10
    for i,r in enumerate(entries,1):
        assert r["unit_id"]==f"SB-MAT-0020-SNAPSHOT-CONTEXT-20261012-{i:02d}"
        assert r["source_id"]=="SB-SRC-0020" and r["source_commit"]==REV and r["source_blob_sha"]==SHA
        m=re.fullmatch(r"L(\d+)-L(\d+)",r["source_span"]); assert m
        a,z=map(int,m.groups()); assert 1<=a<=z<=len(lines) and any(x.strip() for x in lines[a-1:z])
        assert r["source_material_state"]=="unaccounted" and r["independent_review"]=="OPEN"
        assert r["science_destination"]=="docs/science/surfaces/semantic-portability-and-client-authority.md" and r["current_how_destination"]=="docs/current-how/windows-application.md"
    txt=HOW.read_text(encoding="utf-8")
    sci=SCIENCE.read_text(encoding="utf-8")
    for required in ("198 tracked files","149 Python","1.34 MB","six historical labels","standalone-dev-root"):
        if required=="six historical labels":
            assert "six historical labels" in txt or "six desktop navigation" in txt.lower()
        elif required=="standalone-dev-root":
            assert "development root" in txt
        else: assert required in txt
    assert "historical file tree size" in sci
    print(json.dumps({"verdict":"FROZEN_WINDOWS_SURVEY_TOP_LEVEL_SOURCE_GEOMETRY_ONLY","producer_rows":10,"original_independent_review":"OPEN","whole_original_status":"unaccounted"}))
if __name__=="__main__":check()
