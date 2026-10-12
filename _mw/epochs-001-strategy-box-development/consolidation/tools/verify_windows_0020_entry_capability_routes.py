#!/usr/bin/env python3
"""Frozen original Windows-entry/catalog to Science + pinned current source structural checks.

This test establishes only revision identity, text routes and selected checked-in
declarations. It does not prove semantic losslessness or executable host readiness.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
REV = "8459dc58922b7e8df853cf1d9e8131fa9e132580"
SHA = "225128f2599f0792422c0b31cb3cbe1437991ced"
ORIGINAL = "_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md"
LEDGER = ROOT / "_mw/epochs-001-strategy-box-development/consolidation/units/WINDOWS-STUDY-0020-ENTRY-CAPABILITY-08.jsonl"
SCIENCE = ROOT / "docs/science/capabilities/definitions-plans-and-execution-truth.md"


def verify() -> dict:
    source = read_pinned_blob(ROOT, REV, ORIGINAL, SHA).decode("utf-8").splitlines()
    assert len(source) in (1741, 1742), "Unexpected frozen original length"
    rows = [json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 8
    body = SCIENCE.read_text(encoding="utf-8")
    seen = set()
    for i, row in enumerate(rows, 1):
        uid = f"SB-MAT-0020-ENTRY-{i:02d}"
        assert row["unit_id"] == uid and uid not in seen
        seen.add(uid)
        assert row["source_id"] == "SB-SRC-0020"
        assert row["source_commit"] == REV and row["source_blob_sha"] == SHA
        assert row["source_material_state"] == "unaccounted" and row["independent_review"] == "OPEN"
        assert row["epistemic_status"] and row["english_research_meaning"] and row["defeater_or_limit"]
        match = re.fullmatch(r"L(\d+)-L(\d+)", row["source_span"])
        assert match
        a, b = map(int, match.groups())
        assert 1 <= a <= b <= len(source)
        assert any(s.strip() for s in source[a-1:b])
        label = uid.replace("SB-MAT-0020-", "SB-SRC-0020/")
        for x in (label, row["epistemic_status"], row["english_research_meaning"],
                  row["defeater_or_limit"], f"#L{a}-L{b}"):
            assert x in body, "Missing original-bound Science statement: " + uid

    # This checkout is already used for synthetic Windows characterizations in CI.
    window = ROOT / "windows-pinned/src/stratbox_windows"
    if window.exists():
        entry = (window / "__main__.py").read_text(encoding="utf-8")
        registry = (window / "application/operations/catalog/registry.py").read_text(encoding="utf-8")
        scenarios = (window / "application/scenarios/registry.py").read_text(encoding="utf-8")
        assert "if args.no_gui:" in entry and "run_operation_by_id('system.diagnostics'" in entry
        assert entry.index("if args.no_gui:") < entry.index("from stratbox_windows.presentation.qt_desktop.main import run_gui")
        opids = re.findall(r"^\s*id='([^']+)'", registry, re.M)
        assert opids == ["cbr_file_collector.collect", "escrow.history.export", "system.diagnostics"], opids
        assert "for operation in operation_registry.enabled():" in scenarios
        assert "id='scenario.cbr.full_update'" in scenarios
        assert "id='step.collect_cbr_files'" in scenarios
        assert "id='step.export_escrow_history'" in scenarios
    return {
        "verdict": "FROZEN_SOURCE_TEXT_AND_PINNED_CODE_BOUNDARY_ONLY",
        "research_id": "SB-SRC-0020", "rows": len(rows),
        "direct_windows_checkout": "checked" if window.exists() else "unavailable",
        "whole_original_material_state": "unaccounted",
        "independent_assurance": "OPEN",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
