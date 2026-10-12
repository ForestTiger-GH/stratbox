#!/usr/bin/env python3
"""Verify dated Windows Study original 0020 P0-P2 candidate route identities.

This verifies source shape and published row addresses, not product maturity,
semantic adequacy, independent review or test execution on a Windows host.
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
SCIENCE = ROOT / "docs/science/architecture/product-system-model-actors-and-repository-boundaries.md"

def verify() -> dict:
    original = read_pinned_blob(ROOT, REV, SOURCE, BLOB).decode("utf-8")
    selected = original.split("# XX. Главные слабые места и архитектурные долги", 1)[1].split(
        "# XXI. Потенциал развития", 1)[0]
    headings = re.findall(r"^## (7[1-9]|8[0-2])\. (P[012])\s", selected, re.M)
    assert [int(n) for n, _ in headings] == list(range(71, 83)), headings
    assert [grade for _, grade in headings] == ["P0"]*3+["P1"]*6+["P2"]*3, headings
    science = SCIENCE.read_text(encoding="utf-8")
    section = science.split(
        "## Original Windows Research 0020: twelve dated P0–P2 modernization choices", 1
    )[1].split("## Original topic 10: twenty ownership and integration contract boundaries", 1)[0]
    records = re.findall(
        r"^\| W20-P(\d{2}) \| (P[012]) \| ([^|]+) \| ([^|]+) \|$", section, re.M)
    assert len(records) == 12, len(records)
    for index, (number, grade, claim, boundary) in enumerate(records):
        assert int(number) == 71+index and grade == headings[index][1]
        assert len(claim.strip()) > 25 and len(boundary.strip()) > 35
    for qualifier in ("historical", "not", "tests"):
        assert qualifier.lower() in section.lower(), qualifier
    return {"verdict":"PINNED_0020_PRIORITIES_STRUCTURAL_ONLY",
            "source_id":"SB-SRC-0020","source_blob":BLOB,
            "original_proposals":12,"science_proposed_routes":len(records),
            "native_current_windows_evidence":"NOT_EXECUTED_BY_THIS_TOOL",
            "independent_semantic_verification":"UNEXECUTED",
            "material_unit_state":"unaccounted"}

if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
