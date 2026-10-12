#!/usr/bin/env python3
"""Verify bounded frozen automation ontology source routes, not semantic losslessness."""
from __future__ import annotations
import json
import re
from pathlib import Path
from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
REV = "8459dc58922b7e8df853cf1d9e8131fa9e132580"
BLOB = "dee8958b16b3fe08042b5212d35fcc8424db28e3"
ORIGINAL = "_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md"
LEDGER = ROOT / "_mw/epochs-001-strategy-box-development/consolidation/units/AUTOMATION-0041-ONTOLOGY-AUTHORITY-10.jsonl"
SCIENCE = ROOT / "docs/science/automation/bounded-agent-routing-and-evidence-safe-automation.md"
HOST = ROOT / "docs/what/strategy-box/host-deployment-commitment.md"


def verify() -> dict:
    lines = read_pinned_blob(ROOT, REV, ORIGINAL, BLOB).decode("utf-8").splitlines()
    assert len(lines) in (2386, 2387)
    source_body = "\n".join(lines[206:338])
    assert "пять разных сущностей" in source_body
    for name in ("Operation", "Scenario", "Automation", "Job", "Case", "AgentRun"):
        assert name in source_body
    records = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(records) == 10
    body = SCIENCE.read_text(encoding="utf-8")
    seen = set()
    for i, row in enumerate(records, 1):
        expected = f"SB-MAT-0041-ONT-{i:02d}"
        assert row["unit_id"] == expected and expected not in seen
        seen.add(expected)
        assert row["source_id"] == "SB-SRC-0041"
        assert row["source_commit"] == REV and row["source_blob_sha"] == BLOB
        assert row["source_material_state"] == "unaccounted" and row["independent_review"] == "OPEN"
        m = re.fullmatch(r"L(\d+)-L(\d+)", row["source_span"])
        assert m
        a, b = map(int, m.groups())
        assert 1 <= a <= b <= len(lines) and any(t.strip() for t in lines[a-1:b])
        for token in (expected.replace("SB-MAT-0041-","SB-SRC-0041/"),row["epistemic_status"],row["english_research_meaning"],row["defeater_or_limit"],f"#L{a}-L{b}"):
            assert token in body, "Unrouted original content: " + expected
    assert "PD-SB-HOST-2026-10-12-01" in HOST.read_text(encoding="utf-8")
    return {"verdict":"ORIGINAL_IDENTITY_AND_TEXT_ONLY_NOT_SEMANTIC_CERTIFICATION","source":"SB-SRC-0041","rows":len(records),"internal_enumeration_mismatch":"observed","material_state":"unaccounted","independent_assurance":"OPEN"}


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
