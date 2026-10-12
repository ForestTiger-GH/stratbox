#!/usr/bin/env python3
"""Confirm 18 Topic 09 original row identities map to published independent LDD."""
from __future__ import annotations
import json
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
REV="388e3d61ec01350d3b7d35ea4a97a21db0b36f97"
SHA="6de2bc8010216554ea7550d17bb03cee48cf7dd7"
SRC="_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/09_Источники_данных_версии_и_воспроизводимость_Strategy_Box_2026-10-10.md"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/SOURCE-VINTAGE-0562-EIGHTEEN-CASES.jsonl"
LDD=ROOT/"docs/ldd/data/used-source-receipt-boundary.md"
SCIENCE=ROOT/"docs/science/data-and-knowledge/source-observation-vintages-and-replay.md"
def verify():
    lines=read_pinned_blob(ROOT,REV,SRC,SHA).decode("utf-8").splitlines()
    rows=[json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows)==18
    full=LDD.read_text(encoding="utf-8")
    for i,item in enumerate(rows,1):
        assert item["unit_id"]==f"SB-MAT-0562-VINTAGE-20261012-{i:02d}"
        assert item["source_id"]=="SB-SRC-0562" and item["source_commit"]==REV and item["source_blob_sha"]==SHA
        assert item["source_span"]==f"L{566+i}" and f"| T{i:02d}:" in lines[565+i]
        assert item["design_destination"]=="docs/ldd/data/used-source-receipt-boundary.md" and item["independent_review"]=="OPEN"
        assert item["source_material_state"]=="unaccounted" and item["execution"]=="UNEXECUTED"
        assert full.count("| "+item["publication_test_id"]+" |")==1
    assert "PR-27" in SCIENCE.read_text(encoding="utf-8") and "PR-28" in SCIENCE.read_text(encoding="utf-8")
    print(json.dumps({"verdict":"ALL_EIGHTEEN_DATE_SOURCE_VINTAGE_TEST_INTENTIONS_ROUTED","routed":18,"new_published_negative_cases":2,"executed":0,"independent_assurance":"OPEN"}))
if __name__=="__main__":verify()
