#!/usr/bin/env python3
"""Bounded frozen Topic 03 source→Science textual route integrity, not independent review."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/03_state_persistence_recovery_strategy_box_2026-10-10.md"
LEDGERS = (
    ("STATE-0556-RECOVERY-FAULT-12.jsonl", 12),
    ("STATE-0556-ORIGINAL-OPEN-QUESTIONS-16.jsonl", 16),
)
LEDGER_ROOT = ROOT / "_mw/epochs-001-strategy-box-development/consolidation/units"
SOURCE_BLOB = "f919df034a2e15ae8947d51aaec9cd564fe462ad"
SOURCE_COMMIT = "388e3d61ec01350d3b7d35ea4a97a21db0b36f97"
PERMITTED = {
    "docs/science/state-and-recovery/authority-durability-and-recovery.md",
    "docs/science/state-and-recovery/shared-state-backup-generation-and-retention.md",
}


def verify() -> dict[str, object]:
    raw = SOURCE.read_bytes()
    actual_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    assert actual_blob == SOURCE_BLOB, actual_blob
    lines = raw.decode("utf-8").splitlines()
    rows = []
    for filename, count in LEDGERS:
        found = [json.loads(x) for x in (LEDGER_ROOT / filename).read_text(encoding="utf-8").splitlines() if x.strip()]
        assert len(found) == count, filename
        rows.extend(found)
    assert len(rows) == 28, len(rows)
    seen = set()
    cache = {}
    for row in rows:
        uid = row["unit_id"]
        assert uid not in seen
        seen.add(uid)
        assert row["source_id"] == "SB-SRC-0556"
        assert row["source_blob_sha"] == SOURCE_BLOB
        assert row["source_commit"] == SOURCE_COMMIT
        assert row["source_material_state"] == "unaccounted"
        assert row["independent_review"] == "OPEN"
        assert row["epistemic_status"]
        dest = row["science_destination"]
        assert dest in PERMITTED
        m = re.fullmatch(r"L(\d+)-L(\d+)", row["source_span"])
        assert m is not None
        a, b = map(int, m.groups())
        assert 1 <= a <= b <= len(lines)
        assert any(lines[i - 1].strip() for i in range(a, b + 1))
        if dest not in cache:
            cache[dest] = (ROOT / dest).read_text(encoding="utf-8")
        sci = cache[dest]
        for excerpt in (
            uid.replace("SB-MAT-0556-", "SB-SRC-0556/"),
            row["english_research_meaning"],
            row["defeater_or_limit"],
            (f"#L{a}" if a == b else f"#L{a}-L{b}"),
        ):
            assert excerpt in sci, f"{uid} missing: {excerpt[:80]}"
    return {
        "verdict": "STRUCTURAL_ORIGINAL_TO_SCIENCE_ONLY_NOT_SEMANTIC_PASS",
        "original": "SB-SRC-0556",
        "rows": len(rows),
        "source_blob": SOURCE_BLOB,
        "full_source_material_state": "unaccounted",
        "independent_review": "OPEN",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
