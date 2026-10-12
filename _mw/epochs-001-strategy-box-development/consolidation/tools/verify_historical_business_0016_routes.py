#!/usr/bin/env python3
"""Check exact frozen original 0016 and 15 public-safe historical Science routes."""
from __future__ import annotations
import json
import re
from pathlib import Path
from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
ORIGINAL = "_mw/epochs-001-strategy-box-development/research/01-old-notes/Рефактор бизнес-логики Stratbox.md"
REVISION = "8459dc58922b7e8df853cf1d9e8131fa9e132580"
BLOB = "d04fece78c89063c2ac2dac775179f1517c7fea9"
LEDGER = ROOT / "_mw/epochs-001-strategy-box-development/consolidation/units/HISTORICAL-BUSINESS-0016-CANONICAL-15.jsonl"
OWNERS = {
    "docs/science/capabilities/definitions-plans-and-execution-truth.md",
    "docs/science/work/admission-planning-resource-scheduling-and-recovery.md",
    "docs/science/architecture/semantic-ownership-and-contract-boundaries.md",
    "docs/science/artifacts/output-identity-publication-and-availability.md",
}


def verify() -> dict:
    raw = read_pinned_blob(ROOT, REVISION, ORIGINAL, BLOB)
    lines = raw.decode("utf-8").splitlines()
    assert len(lines) in {1926, 1927}
    entries = [json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(entries) == 15
    seen = set()
    cache = {}
    for item in entries:
        uid = item["unit_id"]
        assert uid not in seen
        seen.add(uid)
        assert item["source_id"] == "SB-SRC-0016"
        assert item["source_commit"] == REVISION
        assert item["source_blob_sha"] == BLOB
        assert item["source_material_state"] == "unaccounted"
        assert item["independent_review"] == "OPEN"
        assert item["epistemic_status"]
        m = re.fullmatch(r"L(\d+)-L(\d+)", item["source_span"])
        assert m
        start, finish = map(int, m.groups())
        assert 1 <= start <= finish <= len(lines)
        assert any(lines[i - 1].strip() for i in range(start, finish + 1))
        path = item["science_destination"]
        assert path in OWNERS
        if path not in cache:
            cache[path] = (ROOT / path).read_text(encoding="utf-8")
        doc = cache[path]
        for phrase in (
            uid.replace("SB-MAT-0016-", "SB-SRC-0016/"),
            item["english_research_meaning"],
            item["defeater_or_limit"],
            f"#L{start}-L{finish}",
        ):
            assert phrase in doc, "Missing exact historical source position"
    return {
        "verdict": "STRUCTURAL_FROZEN_SOURCE_TRANSFER_ONLY",
        "source_id": "SB-SRC-0016",
        "source_blob": BLOB,
        "rows": len(entries),
        "independent_semantic_certification": "OPEN",
        "whole_original": "unaccounted",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
