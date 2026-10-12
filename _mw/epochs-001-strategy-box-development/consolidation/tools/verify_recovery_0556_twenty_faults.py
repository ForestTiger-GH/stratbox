#!/usr/bin/env python3
"""Verify exact 20 Topic-03 source recovery rows are routed to Science.

Source/row presence only: no proof of semantic equality, actual fsync
durability, SQLite crash behavior or independent original review.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
REV = "388e3d61ec01350d3b7d35ea4a97a21db0b36f97"
BLOB = "f919df034a2e15ae8947d51aaec9cd564fe462ad"
SRC = ("_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/"
       "03_state_persistence_recovery_strategy_box_2026-10-10.md")
DEST = ROOT / "docs/science/state-and-recovery/authority-durability-and-recovery.md"
EXPECTED = list(range(1, 21))


def main() -> dict:
    origin = read_pinned_blob(ROOT, REV, SRC, BLOB).decode("utf-8")
    assert origin.count("## 13. Recovery failure matrix") == 1
    source_matrix = origin.split("## 13. Recovery failure matrix", 1)[1].split(
        "## 14. ", 1)[0]
    source_ids = [int(m.group(1)) for m in re.finditer(
        r"^\|\s*(\d{1,2})\s*\|", source_matrix, re.M)]
    assert source_ids == EXPECTED, source_ids

    science = DEST.read_text(encoding="utf-8")
    assert science.count("## Original Topic 03 — twenty distinct recovery") == 1
    matrix = science.split("## Original Topic 03 — twenty distinct recovery", 1)[1]
    rows = [(int(m.group(1)), m.group(2)) for m in re.finditer(
        r"^\| R03-(\d{2}) \|([^\n]+)$", matrix, re.M)]
    assert [num for num, _ in rows] == EXPECTED
    assert all(len(row.split("|")) >= 2 and
               all(len(value.strip()) >= 12 for value in row.split("|")[:2])
               for _, row in rows)
    assert all(science.count(f"| R03-{i:02d} |") == 1 for i in EXPECTED)
    assert "UNEXECUTED" in matrix and "Product/Platform decisions" in matrix
    return {
        "verdict": "TWENTY_RECOVERY_PROPOSALS_ROUTED_STRUCTURALLY",
        "source_id": "SB-SRC-0556",
        "source_blob": BLOB,
        "origin_rows": len(source_ids),
        "science_rows": len(rows),
        "executed_native_storage_tests_here": 0,
        "independent_whole_original_assurance": "OPEN",
        "source_material_state": "unaccounted",
    }


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False))
