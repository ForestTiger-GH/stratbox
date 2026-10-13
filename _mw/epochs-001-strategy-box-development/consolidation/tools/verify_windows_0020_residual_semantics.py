#!/usr/bin/env python3
"""Prove exact source-0020 provenance geometry, not meaning or release readiness."""
from __future__ import annotations
import json
import re
from pathlib import Path
from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "_mw/epochs-001-strategy-box-development/consolidation"
SOURCE = "_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md"
BLOB = "225128f2599f0792422c0b31cb3cbe1437991ced"
PIN = "8459dc58922b7e8df853cf1d9e8131fa9e132580"
NEW = "WINDOWS-0020-RESIDUAL-CANDIDATES-07.jsonl"
OLD = (
    "BASE-STUDY-0020.jsonl",
    "WINDOWS-0020-HISTORICAL-SNAPSHOT-10.jsonl",
    "WINDOWS-0020-PINNED-CATALOG-03.jsonl",
    "WINDOWS-STATE-0020-ENGLISH-16.jsonl",
    "WINDOWS-STUDY-0020-DATED-PRIORITIES-AND-ROADMAP-17.jsonl",
    "WINDOWS-STUDY-0020-DIRECT-RECONCILIATION-09.jsonl",
    "WINDOWS-STUDY-0020-ENTRY-CAPABILITY-08.jsonl",
    "WINDOWS-STUDY-0020-EXECUTION-STATE-12.jsonl",
    "WINDOWS-STUDY-0020-FUTURE-AND-PORTABILITY-15.jsonl",
    "WINDOWS-STUDY-0020-RUNTIME-WORKROOM-18.jsonl",
)
EXACT = {
    "01": ("L897-935", ("Node view", "BackgroundProcessStore")),
    "02": ("L939-962", ("PresenceService", "real-time presence")),
    "03": ("L966-991", ("Assignment", "JSON history")),
    "04": ("L995-1029", ("locality = local", "launch_mode = foreground")),
    "05": ("L1242-1297", ("Branch/release", "Scenario-first UX")),
    "06": ("L1520-1591", ("presentation/common", "stratbox-android")),
    "07": ("L1737-1741", ("полный checkout", "не запускались")),
}
SPAN = re.compile(r"^L(\d+)(?:-L?(\d+))?$")

def rows(filename: str) -> list[dict]:
    path = BASE / "units" / filename
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

def run() -> dict:
    source = read_pinned_blob(ROOT, PIN, SOURCE, BLOB).decode("utf-8").split("\n")
    assert len(source) == 1742
    added = rows(NEW)
    assert len(added) == 7
    assert {x["unit_id"] for x in added} == {
        "SB-MAT-0020-RESIDUAL-"+key for key in EXACT}
    scientific = (ROOT / "docs/science/surfaces/semantic-portability-and-client-authority.md").read_text(encoding="utf-8")
    for phrase in ("Windows original 0020: the dated local scaffolds",
                   "No remotely authenticated directory", "recipient delivery",
                   "local, foreground, Windows surface",
                   "Preserved historical alternative",
                   "physical tree is a research sketch",
                   "no full native Qt acceptance run"):
        assert phrase.lower() in scientific.lower(), phrase
    newly = set()
    for row in added:
        key = row["unit_id"][-2:]
        expected, phrases = EXACT[key]
        assert row["source_id"] == "SB-SRC-0020"
        assert row["source_blob_sha"] == BLOB and row["source_span"] == expected
        assert row["material_unit_state"] == "unaccounted"
        assert row["independent_review"] == "OPEN"
        assert (ROOT / row["science_destination"]).is_file()
        assert (ROOT / row["current_how_route"]).is_file()
        match = SPAN.fullmatch(expected)
        assert match
        lo, hi = int(match[1]), int(match[2])
        body = "\n".join(source[lo-1:hi])
        assert all(phrase.casefold() in body.casefold() for phrase in phrases), key
        newly.update(range(lo, hi + 1))
    covered_prior = set()
    covered = set()
    for fname in OLD + (NEW,):
        for row in rows(fname):
            if row.get("source_id") != "SB-SRC-0020":
                continue
            m = SPAN.fullmatch(str(row.get("source_span") or row.get("span") or ""))
            if m:
                lo, hi = int(m[1]), int(m[2] or m[1])
                assert 1 <= lo <= hi <= len(source)
                selected = set(range(lo, hi + 1))
                covered.update(selected)
                if fname != NEW:
                    covered_prior.update(selected)
    nonblank = {i for i, line in enumerate(source, 1) if line.strip()}
    before = nonblank - covered_prior
    assert newly <= covered
    after = nonblank - covered
    assert len(before) == 234, len(before)
    assert len(after) == 72, len(after)
    return {
        "verdict": "PRODUCER_FROZEN_0020_SOURCE_ROUTES_STRUCTURAL_ONLY",
        "original_source_lines": len(source),
        "new_exact_span_units": len(added),
        "prior_unspanned_nonblank_lines": len(before),
        "remaining_unspanned_nonblank_lines": len(after),
        "independent_semantic_review": "OPEN",
        "source_material_state": "unaccounted",
        "native_runtime_conformance": "UNEXECUTED",
    }

if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
