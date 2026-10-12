#!/usr/bin/env python3
"""Source-pinned 26 Topic-02 failures vs maintained Scientific Knowledge.

This verifies case identity/row presence and nonempty input/evidence wording,
NOT behavioral conformance, semantic equality or independent full-source PASS.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
REV = "388e3d61ec01350d3b7d35ea4a97a21db0b36f97"
SHA = "8f26612eabd683a8868d821852c51774d74db257"
SRC = ("_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/"
       "02_Жизненный_цикл_задач_и_управление_исполнением_2026-10-10.md")
DOC = ROOT / "docs/science/execution-and-diagnostics/interruption-cancellation-retry-and-checkpoints.md"
EXPECTED = list(range(1, 27))


def verify() -> dict:
    original = read_pinned_blob(ROOT, REV, SRC, SHA).decode("utf-8")
    assert original.count("## 17. Приёмочные сценарии отказов") == 1
    section = original.split("## 17. Приёмочные сценарии отказов", 1)[1].split(
        "## 18. ", 1)[0]
    originals = [int(m.group(1)) for m in
                 re.finditer(r"^\|\s*(\d{1,2})\s*\|", section, re.M)]
    assert originals == EXPECTED, originals
    dest = DOC.read_text(encoding="utf-8")
    assert dest.count("## Original Topic 02 — twenty-six") == 1
    section = dest.split("## Original Topic 02 — twenty-six", 1)[1]
    rows = [(int(m.group(1)), m.group(2))
            for m in re.finditer(r"^\| E02-(\d{2}) \|([^\n]+)$",
                                 section, re.M)]
    assert [num for num, _ in rows] == EXPECTED, [num for num, _ in rows]
    assert all(len(row.split("|")) >= 2
               and all(len(item.strip()) >= 15 for item in row.split("|")[:2])
               for _, row in rows)
    assert all(dest.count(f"| E02-{n:02d} |") == 1 for n in EXPECTED)
    # Differentiating lost ACK from precommit failure is source material,
    # not prose decoration or a test that every unknown is a known failure.
    assert "E02-04" in section and "UNKNOWN" in section
    assert "E02-22" in section and "E02-23" in section
    return {
        "verdict": "ALL_26_ORIGINAL_TOPIC02_FAULT_CASES_ROUTED_STRUCTURALLY",
        "original_source": "SB-SRC-0555",
        "original_blob": SHA,
        "case_count": 26,
        "candidate_tests_executed_by_this_verifier": 0,
        "whole_source_independent_assurance": "UNEXECUTED",
        "native_storage_host_domain_conformance": "UNEXECUTED",
        "census_material_state": "unaccounted",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
