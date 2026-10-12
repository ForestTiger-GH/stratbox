#!/usr/bin/env python3
"""Exact pinned Topic 06 machine scenario routes, never a runtime pass."""
from __future__ import annotations
import json,re
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
REV="388e3d61ec01350d3b7d35ea4a97a21db0b36f97"
SOURCE="_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/06_machine_interfaces_capability_catalog_Strategy_Box_2026-10-10.md"
SHA="0d2cc9226bbc5791143a655c2e304341ef9b9e82"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/MACHINE-0559-CONFORMANCE-25.jsonl"
DEST=ROOT/"docs/ldd/capabilities/machine-operation-adapter-conformance.md"
def verify():
    original=read_pinned_blob(ROOT,REV,SOURCE,SHA).decode("utf-8").splitlines()
    assert len(original)==1165
    entries=[json.loads(v) for v in LEDGER.read_text(encoding="utf-8").splitlines() if v.strip()]
    assert len(entries)==25
    body=DEST.read_text(encoding="utf-8")
    for i,x in enumerate(entries,1):
        id=f"MAC-{i:02d}"
        assert x["unit_id"]==f"SB-MAT-0559-MAC-20261012-{i:02d}"
        assert x["source_id"]=="SB-SRC-0559" and x["source_commit"]==REV and x["source_blob_sha"]==SHA
        line=(1008+i-1) if i<=10 else (1023+i-11)
        assert x["source_span"]==f"L{line}" and f"| T{i:02d} |" in original[line-1]
        assert x["publication_test_id"]==id and x["execution"]=="UNEXECUTED"
        assert x["design_destination"]=="docs/ldd/capabilities/machine-operation-adapter-conformance.md" and x["independent_review"]=="OPEN"
        assert body.count("| "+id+" |")==1
    assert "BLOCKED_NOT_IMPLEMENTED" in body and "| MAC-26 |" not in body
    print(json.dumps({"verdict":"TWENTY_FIVE_PINNED_MACHINE_ACCEPTANCE_CASES_ONLY","source_rows":25,"published_vectors":25,"executed_vectors":0,"independent_review":"OPEN"}))
if __name__=="__main__":verify()
