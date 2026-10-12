#!/usr/bin/env python3
"""Exact historical source/ledger/Science routing check; NOT semantic assurance."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[4]
CONSOLIDATION = ROOT / "_mw/epochs-001-strategy-box-development/consolidation"
SOURCE = ROOT / "_mw/epochs-001-strategy-box-development/research/01-old-notes/Интерфейс Strategy Box.md"
LEDGER = CONSOLIDATION / "units/HISTORICAL-UX-0013-RESIDUAL-CONCRETE-14.jsonl"
SCIENCE = ROOT / "docs/science/surfaces/explorer-workroom-and-operational-desktop-interaction.md"
SOURCE_BLOB = "2f2b05d1a1af3401fb402bfb43c8cc36a907d9fe"
SCIENCE_SECTION = "## Residual concrete interaction claims from the original historical interface note"
EXPECTED_ROWS = 14


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\\0" + content).hexdigest()


def verify() -> dict[str, object]:
    raw = SOURCE.read_bytes()
    assert git_blob_sha(raw) == SOURCE_BLOB, "frozen research blob differs"
    source_lines = raw.decode("utf-8").splitlines()
    science = SCIENCE.read_text(encoding="utf-8")
    assert SCIENCE_SECTION in science, "canonical Science section missing"
    rows = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == EXPECTED_ROWS, f"expected {EXPECTED_ROWS}, observed {len(rows)}"
    ids: set[str] = set()
    exact_links = 0
    for row in rows:
        uid = row["unit_id"]
        assert uid not in ids, f"duplicate unit: {uid}"
        ids.add(uid)
        assert row["source_id"] == "SB-SRC-0013"
        assert row["source_blob_sha"] == SOURCE_BLOB
        assert row["independent_review"] == "OPEN"
        assert row["source_material_state"] == "unaccounted"
        assert row["epistemic_status"] == "HISTORICAL_UX_PROPOSAL_NOT_CURRENT_OR_APPROVED"
        assert row["science_destination"] == str(SCIENCE.relative_to(ROOT))
        assert uid.startswith("SB-MAT-0013-UX-RES-")
        display_id = uid.replace("SB-MAT-0013-", "SB-SRC-0013/")
        assert display_id in science, f"missing Science row: {uid}"
        match = re.fullmatch(r"L([1-9][0-9]*)(?:-L([1-9][0-9]*))?", row["source_span"])
        assert match is not None, f"invalid locator for {uid}"
        start = int(match.group(1))
        end = int(match.group(2) or start)
        assert 1 <= start <= end <= len(source_lines), f"invalid range for {uid}"
        assert any(source_lines[i-1].strip() for i in range(start, end+1)), f"empty span for {uid}"
        fragment = f"#L{start}" + (f"-L{end}" if end != start else "")
        assert fragment in science, f"line anchor not published for {uid}"
        exact_links += 1
    return {
        "verdict": "STRUCTURAL_TRANSFER_ONLY_NO_SEMANTIC_OR_INDEPENDENT_PASS",
        "source_sha1": SOURCE_BLOB,
        "source_lines": len(source_lines),
        "rows": len(rows),
        "science_anchors": exact_links,
        "independent_reviews": 0,
        "source_level_disposition": "unaccounted",
    }


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), ensure_ascii=False))
    except Exception as exc:
        print(f"UX_0013_ROUTE_FAILURE: {exc!r}", file=sys.stderr)
        raise
