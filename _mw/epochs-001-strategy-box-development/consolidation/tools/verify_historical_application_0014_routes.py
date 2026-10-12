#!/usr/bin/env python3
"""Validate frozen original 0014 source identities and qualified Science transfers.

This is author-side structural provenance checking, not independent semantic
conservation, a verified current UI or an acceptance of the dated launcher.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "_mw/epochs-001-strategy-box-development/research/01-old-notes/О приложении Strategy Box.md"
LEDGER = ROOT / "_mw/epochs-001-strategy-box-development/consolidation/units/HISTORICAL-APPLICATION-0014-LAUNCHER-16.jsonl"
BLOB = "c10ee7d96f24996f6480d95adf2b005c0651122e"
SOURCE_REV = "8459dc58922b7e8df853cf1d9e8131fa9e132580"
PERMITTED = {
    "docs/science/deployment/headless-host-web-security-and-persistence-tradeoffs.md",
    "docs/science/surfaces/semantic-portability-and-client-authority.md",
    "docs/science/architecture/semantic-ownership-and-contract-boundaries.md",
    "docs/science/automation/trigger-occurrence-identity-and-governed-execution.md",
}


def verify() -> dict[str, object]:
    raw = SOURCE.read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    assert actual == BLOB, actual
    lines = raw.decode("utf-8").splitlines()
    rows = [json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 16
    seen = set()
    docs = {}
    for row in rows:
        uid = row["unit_id"]
        assert uid not in seen
        seen.add(uid)
        assert row["source_id"] == "SB-SRC-0014"
        assert row["source_commit"] == SOURCE_REV and row["source_blob_sha"] == BLOB
        assert row["source_material_state"] == "unaccounted"
        assert row["independent_review"] == "OPEN"
        assert row["epistemic_status"].strip()
        path = row["science_destination"]
        assert path in PERMITTED
        m = re.fullmatch(r"L(\d+)-L(\d+)", row["source_span"])
        assert m
        a, b = map(int, m.groups())
        assert 1 <= a <= b <= len(lines)
        assert any(lines[n - 1].strip() for n in range(a, b + 1))
        if path not in docs:
            docs[path] = (ROOT / path).read_text(encoding="utf-8")
        text = docs[path]
        for candidate in (
            uid.replace("SB-MAT-0014-", "SB-SRC-0014/"),
            row["english_research_meaning"],
            row["defeater_or_limit"],
            f"#L{a}-L{b}",
        ):
            assert candidate in text, f"Missing source meaning: {uid}"
    return {
        "status": "STRUCTURAL_HISTORICAL_SOURCE_TRANSFER_NOT_SEMANTIC_PASS",
        "original": "SB-SRC-0014",
        "source_lines": len(lines),
        "rows_checked": len(rows),
        "material_disposition": "unaccounted",
        "independent_assurance": "OPEN",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
