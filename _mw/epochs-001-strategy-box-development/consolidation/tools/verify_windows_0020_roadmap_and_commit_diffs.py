#!/usr/bin/env python3
"""Compare five dated original Windows roadmap stage labels with maintained Science.

Structural producer assurance only; does not execute Windows, Android or a host.
The independent Windows Git commit diffs in Current HOW were inspected externally,
and are NOT independently re-fetched or certified by this test.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
REV = "8459dc58922b7e8df853cf1d9e8131fa9e132580"
BLOB = "225128f2599f0792422c0b31cb3cbe1437991ced"
SOURCE = ("_mw/epochs-001-strategy-box-development/research/02-base-study/"
          "stratbox-windows_current_state_full_research_2026-10-06.md")
SCIENCE = ROOT / "docs/science/surfaces/semantic-portability-and-client-authority.md"
CURRENT = ROOT / "docs/current-how/windows-application.md"
COMMITS = ("d6518394639a5b3e4dcb1d4934f18e9d4126f269",
           "959e9c4ce1441124af5111c1e025041714e04d3b")

def verify() -> dict:
    original = read_pinned_blob(ROOT, REV, SOURCE, BLOB).decode("utf-8")
    source_segment = original.split("# XXIII. Приоритетный roadmap", 1)[1].split(
        "# XXIV. Что сейчас уже является продуктом", 1)[0]
    stages = re.findall(r"^## Этап ([1-5]) — (.+)$", source_segment, re.M)
    assert [int(n) for n, _ in stages] == [1, 2, 3, 4, 5], stages
    assert len({title.strip() for _, title in stages}) == 5

    science = SCIENCE.read_text(encoding="utf-8")
    section = science.split("## Dated Windows study 0020: five proposed implementation stages", 1)[1].split(
        "## Original application note 0014", 1)[0]
    records = re.findall(r"^\\| W20-RM([1-5]) \\| ([^|]+) \\| ([^|]+) \\|$", section, re.M)
    assert [int(n) for n, _, _ in records] == [1, 2, 3, 4, 5], records
    for _, meaning, countercase in records:
        assert len(meaning.strip()) > 85 and len(countercase.strip()) > 65
    assert "pyside6-android-deploy" in section
    assert "four different tests" in section
    current = CURRENT.read_text(encoding="utf-8")
    assert "Direct Git-commit provenance falsifier" in current
    for sha in COMMITS:
        assert "https://github.com/ForestTiger-GH/stratbox-windows/commit/" + sha in current
    assert "no Python source diff" in current
    return {
        "verdict": "SOURCE_ROUTING_STRUCTURAL_ONLY",
        "source_id": "SB-SRC-0020", "source_blob": BLOB,
        "dated_stage_labels": len(stages), "science_source_proposals": len(records),
        "git_commit_links_structural": len(COMMITS),
        "actual_commit_diff_reverification_by_tool": "NOT_PERFORMED",
        "native_windows_android_host_tests": "UNEXECUTED",
        "independent_source_semantic_verification": "UNEXECUTED",
        "material_unit_state": "unaccounted"
    }

if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
