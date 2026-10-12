#!/usr/bin/env python3
"""Pinned Topic 08 thirty-minus-two observations: 28 candidate cases, never executed."""
from __future__ import annotations
import json
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
REV="388e3d61ec01350d3b7d35ea4a97a21db0b36f97"
SHA="2bca524da78d844b49aa1e12e1a7ce70d2acd944"
SOURCE="_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/08_Наблюдаемость_и_диагностика_исполнения_Strategy_Box_2026-10-10.md"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/OBSERVABILITY-0561-TWENTY-EIGHT-CASES.jsonl"
SCIENCE=ROOT/"docs/science/execution-and-diagnostics/causal-observability-and-failure-truth.md"
DEST=ROOT/"docs/ldd/observability/execution-truth-and-recovery-vectors.md"
def verify():
    orig=read_pinned_blob(ROOT,REV,SOURCE,SHA).decode("utf-8").splitlines()
    rows=[json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows)==28
    body=DEST.read_text(encoding="utf-8")
    for i,x in enumerate(rows,1):
        token=f"OBS-{i:02d}"
        assert x["unit_id"]==f"SB-MAT-0561-OBS-COMPLETE-20261012-{i:02d}"
        assert x["source_commit"]==REV and x["source_id"]=="SB-SRC-0561" and x["source_blob_sha"]==SHA
        assert x["source_span"]==f"L{1069+i}" and f"| O-{i:02d} |" in orig[1068+i]
        assert x["design_destination"]=="docs/ldd/observability/execution-truth-and-recovery-vectors.md" and x["independent_review"]=="OPEN"
        assert x["source_material_state"]=="unaccounted" and x["execution"]=="UNEXECUTED"
        assert body.count("| "+token+" |")==1
    for t in ("torn journal","clock skew","mandatory audit","reconciliation"):
        assert t in body.lower(),t
    print(json.dumps({"verdict":"TWENTY_EIGHT_SOURCE_SPANNED_PROPOSED_OBSERVABILITY_FAULTS","intentions":28,"executed":0,"independent_semantic_assurance":"OPEN"}))
if __name__=="__main__":verify()
