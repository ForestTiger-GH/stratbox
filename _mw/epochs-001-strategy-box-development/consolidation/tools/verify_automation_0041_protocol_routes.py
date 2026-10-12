#!/usr/bin/env python3
"""Bounded source/Science transfer for historical automation research, not a semantic audit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md"
LEDGER = ROOT / "_mw/epochs-001-strategy-box-development/consolidation/units/AUTOMATION-0041-MCP-PROTOCOL-07.jsonl"
SCIENCE = ROOT / "docs/science/capabilities/machine-discovery-bindings-and-adapters.md"
BLOB = "dee8958b16b3fe08042b5212d35fcc8424db28e3"
SCIENCE_HEADER = "## Protocol-version boundary: task handles versus additional input are different contracts"
SOURCE_LOCATOR_PREFIX = "#L"
PRIMARY_SPEC_URLS = (
    "https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/changelog.mdx",
    "https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx",
    "https://github.com/modelcontextprotocol/ext-tasks/blob/main/specification/2026-07-28/tasks.md",
)


def verify() -> dict[str, object]:
    raw = SOURCE.read_bytes()
    git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    assert git_blob == BLOB, f"source byte identity changed: {git_blob}"
    lines = raw.decode("utf-8").splitlines()
    text = SCIENCE.read_text(encoding="utf-8")
    assert SCIENCE_HEADER in text
    assert all(url in text for url in PRIMARY_SPEC_URLS), "primary specification route missing"
    entries = [json.loads(row) for row in LEDGER.read_text(encoding="utf-8").splitlines() if row.strip()]
    assert len(entries) == 7
    ids = set()
    source_meaning_transfers = 0
    for item in entries:
        uid = item["unit_id"]
        assert uid not in ids, uid
        ids.add(uid)
        assert item["source_id"] == "SB-SRC-0041"
        assert item["source_blob_sha"] == BLOB
        assert item["science_destination"] == str(SCIENCE.relative_to(ROOT))
        assert item["source_material_state"] == "unaccounted"
        assert item["independent_review"] == "OPEN"
        assert item["defeater_or_limit"].strip()
        assert item["epistemic_status"].strip()
        span = re.fullmatch(r"L(\d+)-L(\d+)", item["source_span"])
        assert span, uid
        start, end = map(int, span.groups())
        assert 1 <= start <= end <= len(lines)
        assert any(lines[i - 1].strip() for i in range(start, end + 1)), uid
        assert item["english_research_meaning"] in text, "Science prose transfer missing: " + uid
        scientific_id = uid.replace("SB-MAT-0041-", "SB-SRC-0041/")
        assert scientific_id in text, "Science identifier missing: " + uid
        assert "#L" + str(start) + "-L" + str(end) in text, "source anchor missing: " + uid
        source_meaning_transfers += 1
    return {
        "verdict": "EXACT_SOURCE_ROW_TRANSFER_NOT_SEMANTIC_OR_INDEPENDENT_PASS",
        "source": "SB-SRC-0041",
        "rows": len(entries),
        "source_meaning_transfers": source_meaning_transfers,
        "source_git_blob": BLOB,
        "source_material_state": "unaccounted",
        "independent_reviews": 0,
        "source_lines": len(lines),
    }


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), ensure_ascii=False))
    except Exception as exc:
        print(f"AUTOMATION_0041_ROUTE_FAILURE: {exc!r}", file=sys.stderr)
        raise
