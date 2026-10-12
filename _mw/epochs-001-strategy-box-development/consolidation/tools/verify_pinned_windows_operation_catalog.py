#!/usr/bin/env python3
"""Direct pinned Windows catalog verification; static evidence, never installed release."""
from __future__ import annotations
import json,re
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/"windows-pinned/src/stratbox_windows/application"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/WINDOWS-0020-PINNED-CATALOG-03.jsonl"
PUB=ROOT/"docs/current-how/windows-application.md"
def check():
    ops=(BASE/"operations/catalog/registry.py").read_text(encoding="utf-8")
    scenarios=(BASE/"scenarios/registry.py").read_text(encoding="utf-8")
    assert ops.count("OperationSpec(")==3
    for name in ("cbr_file_collector.collect","escrow.history.export","system.diagnostics"):
        assert f"id='{name}'" in ops
        assert name in PUB.read_text(encoding="utf-8")
    assert "for operation in operation_registry.enabled()" in scenarios
    assert "id='scenario.cbr.full_update'" in scenarios
    assert "error_policy='fail_fast'" in scenarios
    body=PUB.read_text(encoding="utf-8");assert "three atomic Scenarios" in body
    text=read_pinned_blob(ROOT,"8459dc58922b7e8df853cf1d9e8131fa9e132580","_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md","225128f2599f0792422c0b31cb3cbe1437991ced").decode("utf-8").splitlines()
    records=[json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(records)==3
    for i,row in enumerate(records,1):
        assert row["unit_id"]==f"SB-MAT-0020-PINNED-CATALOG-20261012-{i}"
        match=re.fullmatch(r"L(\d+)-L(\d+)",row["source_span"]);assert match
        lo,hi=map(int,match.groups());assert 1<=lo<=hi<=len(text) and any(s.strip() for s in text[lo-1:hi])
        assert row["source_material_state"]=="unaccounted" and row["independent_review"]=="OPEN"
    print(json.dumps({"verdict":"DIRECT_PINNED_WINDOWS_OPERATION_SCENARIO_CATALOG","operations":3,"default_atomic_scenarios":3,"conditional_composite":1,"actual_native_conformance":"UNEXECUTED"}))
if __name__=="__main__":check()
