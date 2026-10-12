#!/usr/bin/env python3
"""Pinned historical 30 security-case source spans -> self-contained LDD matrix.

Structural conformance only; no tests executed or independent audit claimed.
"""
from __future__ import annotations
import csv,json,re
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
SOURCE="_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/05_Strategy_Box_Полномочия_безопасность_и_многопользовательская_работа.md"
REV="388e3d61ec01350d3b7d35ea4a97a21db0b36f97"
SHA="68e433f98e9f660c1c5738ef8a41e077ac738a95"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/SECURITY-0558-30-NEGATIVE-ACCEPTANCE.jsonl"
LDD=ROOT/"docs/ldd/security/scoped-authority-and-privacy-vectors.md"
def check():
    lines=read_pinned_blob(ROOT,REV,SOURCE,SHA).decode("utf-8").splitlines()
    assert len(lines)==1206
    rows=[json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows)==30
    body=LDD.read_text(encoding="utf-8")
    for i,row in enumerate(rows,1):
        sid=f"SEC-{i:02d}"; original=f"T05-{i:02d}"
        assert row["unit_id"]==f"SB-MAT-0558-{sid}"
        assert row["source_id"]=="SB-SRC-0558" and row["source_commit"]==REV
        assert row["source_blob_sha"]==SHA and row["source_case_id"]==original
        assert row["source_span"]==f"L{1001+i}" and original in lines[1000+i]
        assert row["publication_test_id"]==sid and row["execution"]=="UNEXECUTED"
        assert row["design_destination"]=="docs/ldd/security/scoped-authority-and-privacy-vectors.md" and row["independent_review"]=="OPEN"
        assert body.count("| "+sid+" |")==1
        assert "UNEXECUTED" in body
    assert "| SEC-31 |" not in body
    print(json.dumps({"verdict":"SOURCE_PINNED_30_TEST_INTENTIONS_NOT_EXECUTED","source_spans":30,"published_test_vectors":30,"independent_assurance":"OPEN"}))
if __name__=="__main__":check()
