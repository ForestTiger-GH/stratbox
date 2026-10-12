#!/usr/bin/env python3
"""Exact 22 Topic-10 source-vector IDs against maintained Science.

Source→destination STRUCTURAL conservation check only. Wording, test validity,
implementation support and reverse completeness require separate review.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
REV = "388e3d61ec01350d3b7d35ea4a97a21db0b36f97"
BLOB = "bc8ed2e00a554b36bf624a4f0f8b4ac8b3501af6"
SOURCE = (
    "_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/"
    "10_Границы_ответственности_и_интеграционные_контракты_Strategy_Box.md"
)
SCIENCE = ROOT / "docs/science/architecture/semantic-ownership-and-contract-boundaries.md"
ROW = re.compile(r"^\|\s*(T10-\d{2})\s*\|([^\n]*)$", re.MULTILINE)
EXPECTED = [f"T10-{i:02d}" for i in range(1, 23)]


def check() -> dict:
    original = read_pinned_blob(ROOT, REV, SOURCE, BLOB).decode("utf-8")
    lines = original.splitlines()
    source_rows = [(line_no, row.group(1), row.group(2))
                   for line_no, text in enumerate(lines, 1)
                   if (row := ROW.match(text)) is not None]
    assert 568 <= source_rows[0][0] < 598, source_rows[0]
    assert 568 < source_rows[-1][0] <= 598, source_rows[-1]
    assert [r[1] for r in source_rows] == EXPECTED
    assert len(set(x[1] for x in source_rows)) == 22
    science = SCIENCE.read_text(encoding="utf-8")
    beginning = science.index("## 10. Negative cases and verification obligations")
    end = science.index("## 11. Open questions", beginning)
    section = science[beginning:end]
    destination_rows = [(m.group(1), m.group(2))
                        for m in ROW.finditer(section)]
    assert [r[0] for r in destination_rows] == EXPECTED
    # Each row must have both a described adverse input and a proposed
    # consequence; empty checkboxes are not material transfer.
    assert all(len(columns.split("|")) >= 3 and
               all(len(value.strip()) >= 12 for value in columns.split("|")[:2])
               for _, columns in destination_rows)
    assert "not measured passes" in section and "P0" in section and "P3" in section
    assert all(science.count(f"| {name} |") == 1 for name in EXPECTED)
    return {
        "verdict": "ALL_22_INTEGRATION_SOURCE_TEST_IDS_PRESENT_IN_KNOWLEDGE",
        "source_id": "SB-SRC-0563",
        "original_blob": BLOB,
        "source_rows": 22,
        "dest_rows": 22,
        "original_line_range": [source_rows[0][0], source_rows[-1][0]],
        "artifact_role": "source_scoped_structure_only",
        "independent_whole_original_semantic_check": "UNEXECUTED",
        "native_host_platform_acceptance_tests": "UNEXECUTED",
        "source_material_state": "unaccounted",
    }


if __name__ == "__main__":
    print(json.dumps(check(), ensure_ascii=False))
