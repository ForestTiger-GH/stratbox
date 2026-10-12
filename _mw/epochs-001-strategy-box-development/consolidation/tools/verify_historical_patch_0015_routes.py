#!/usr/bin/env python3
"""Public-safe source-position check for original May 2026 domain patch.

Reads exact original Git object by immutable revision, without disclosing or
reproducing any excluded historical deployment source content.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
ORIGINAL = "_mw/epochs-001-strategy-box-development/research/01-old-notes/Патч stratbox Май 2026.md"
REVISION = "8459dc58922b7e8df853cf1d9e8131fa9e132580"
BLOB = "a2339ebc79f72a075d290b761fda7b8997b15710"
LEDGER = ROOT / "_mw/epochs-001-strategy-box-development/consolidation/units/HISTORICAL-PATCH-0015-PUBLIC-DOMAINS-12.jsonl"
DESTINATIONS = {
    "docs/science/data-and-knowledge/format-recognition-and-semantic-support.md",
    "docs/science/data-and-knowledge/dataset-versions-lineage-currentness-and-retention.md",
    "docs/science/artifacts/output-identity-publication-and-availability.md",
    "docs/science/data-and-knowledge/source-observation-vintages-and-replay.md",
}


def verify() -> dict:
    lines = read_pinned_blob(ROOT, REVISION, ORIGINAL, BLOB).decode("utf-8").splitlines()
    rows = [json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 12
    assert len(lines) == 106 or len(lines) == 107
    seen = set()
    cache = {}
    for row in rows:
        uid = row["unit_id"]
        assert uid not in seen
        seen.add(uid)
        assert row["source_id"] == "SB-SRC-0015"
        assert row["source_commit"] == REVISION and row["source_blob_sha"] == BLOB
        assert row["source_material_state"] == "unaccounted"
        assert row["independent_review"] == "OPEN"
        dest = row["science_destination"]
        assert dest in DESTINATIONS
        match = re.fullmatch(r"L(\d+)-L(\d+)", row["source_span"])
        assert match
        first, last = map(int, match.groups())
        assert 1 <= first <= last <= len(lines)
        assert any(lines[i - 1].strip() for i in range(first, last + 1))
        if dest not in cache:
            cache[dest] = (ROOT / dest).read_text(encoding="utf-8")
        text = cache[dest]
        for fragment in (
            uid.replace("SB-MAT-0015-", "SB-SRC-0015/"),
            row["english_research_meaning"],
            row["defeater_or_limit"],
            f"#L{first}-L{last}",
        ):
            assert fragment in text, "Public domain trace content missing"
    return {
        "verdict": "STRUCTURAL_PUBLIC_SOURCE_TRANSFER_ONLY",
        "source_id": "SB-SRC-0015",
        "rows": len(rows),
        "whole_source_disposition": "unaccounted",
        "independent_review": "OPEN",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
