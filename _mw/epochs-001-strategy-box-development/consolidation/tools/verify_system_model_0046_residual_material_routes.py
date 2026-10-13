#!/usr/bin/env python3
"""Exact frozen 0046 residual source-to-Science *structural* proof, never semantic certification."""
from __future__ import annotations
import json
import re
from pathlib import Path
from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "_mw/epochs-001-strategy-box-development/consolidation"
PIN = "8459dc58922b7e8df853cf1d9e8131fa9e132580"
SOURCE_PATH = ("_mw/epochs-001-strategy-box-development/research/"
               "03-consolidation-research/"
               "Strategy_Box_01_System_Model_consolidated_research_2026-10-08.md")
BLOB = "2be1cfd1615bcae34375947389bd355c7c07a7ad"
SOURCE_ID = "SB-SRC-0046"
SCI = "docs/science/architecture/product-system-model-actors-and-repository-boundaries.md"
LEDGER = BASE / "units/CONSOLIDATION-SYSTEM-MODEL-0046.jsonl"
SECOND = BASE / "units/SYSTEM-OWNER-0046-ENGLISH-24.jsonl"
SPAN = re.compile(r"^L([0-9]+)(?:-L?([0-9]+))?$")
EXPECTED = {
    "SB-U-0046-111": ("L752-758", ["AppDock execution success", "Strategy Box analytical Work success"]),
    "SB-U-0046-112": ("L831-842", ["semantic color tokens", "typography roles", "light/dark/system theme"]),
    "SB-U-0046-113": ("L1059-1069", ["Banking/macro domain logic", "Extension protocol"]),
    "SB-U-0046-114": ("L1070-1081", ["Scenario/application catalog", "Product authorization", "Platform health/evidence"]),
    "SB-U-0046-115": ("L1082-1089", ["Artifact semantic output/provenance", "Physical artifact bytes", "UI visual semantics"]),
    "SB-U-0046-116": ("L1090-1097", ["Artifact/report visual styles", "User device-local preferences", "Cognitive planning"]),
}
SCIENTIFIC_MARKERS = [
    "Original system-ownership matrix: splits",
    "three distinct owners",
    "Device-local settings",
    "external cognitive planner",
    "Source-preserved split-state counterexample",
    "eight independent visual-semantic responsibilities",
    "separately released design repository",
]

def parse(path: Path) -> list[dict]:
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines()
            if s.strip()]

def run() -> dict:
    source = read_pinned_blob(ROOT, PIN, SOURCE_PATH, BLOB).decode("utf-8").split("\n")
    assert len(source) == 1878
    all_rows = parse(LEDGER) + parse(SECOND)
    chosen = {row["unit_id"]: row for row in all_rows
              if row["unit_id"] in EXPECTED}
    assert len(chosen) == len(EXPECTED)
    spans: set[int] = set()
    for row in all_rows:
        assert row["source_id"] == SOURCE_ID
        m = SPAN.fullmatch(row["source_span"])
        assert m is not None, row["unit_id"]
        start, end = int(m[1]), int(m[2] or m[1])
        assert 1 <= start <= end <= len(source)
        spans.update(range(start, end + 1))
    for key, (expected_span, markers) in EXPECTED.items():
        row = chosen[key]
        assert row["source_blob_sha"] == BLOB
        assert row["source_span"] == expected_span
        assert row["science_destination"] == SCI + (" §6" if key.endswith(("111", "112")) else " §2")
        assert row["independent_review"] == "OPEN"
        assert row["mapping_status"] == "provisional_published_not_independently_bidirectionally_verified"
        m = SPAN.fullmatch(expected_span)
        assert m
        body = "\n".join(source[int(m[1])-1:int(m[2] or m[1])])
        for phrase in markers:
            assert phrase in body, (key, phrase)
    published = (ROOT / SCI).read_text(encoding="utf-8")
    for marker in SCIENTIFIC_MARKERS:
        assert marker.lower() in published.lower(), marker
    nonblank = {i for i, line in enumerate(source, 1) if line.strip()}
    missing = sorted(nonblank - spans)
    # Remaining 0046 unmatched lines are exactly eleven top-level headings,
    # not a semantic disposition for the 0046 original.
    assert len(missing) == 11, missing
    assert all(source[n-1].startswith("# ") for n in missing), missing
    return {
        "verdict": "PRODUCER_EXACT_0046_PROSE_SPAN_ROUTE_ONLY",
        "source": SOURCE_ID,
        "source_lines": len(source),
        "new_exact_source_units": len(EXPECTED),
        "remaining_unspanned_nonblank_lines": len(missing),
        "remaining_unspanned_are_root_headings": True,
        "publication_semantic_lossless": "UNVERIFIED",
        "independent_original_first_review": "OPEN",
    }

if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
