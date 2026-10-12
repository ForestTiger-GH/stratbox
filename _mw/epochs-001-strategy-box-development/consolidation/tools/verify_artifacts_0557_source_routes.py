#!/usr/bin/env python3
"""Check public-safe original Artifact Topic 04 source-to-Science transfers.

Frozen blob, anchors and exact English text only; source-independent semantic
completeness, installed Artifact contracts and actual authorization remain open.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
ORIGINAL = "_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md"
REVISION = "388e3d61ec01350d3b7d35ea4a97a21db0b36f97"
BLOB = "57ae0d79c91b8a5839668f73abfd7af4284f1142"
LEDGER = ROOT / "_mw/epochs-001-strategy-box-development/consolidation/units/ARTIFACTS-0557-ALTERNATIVES-12.jsonl"
PERMITTED = {
    "docs/science/artifacts/output-identity-publication-and-availability.md",
    "docs/science/state-and-recovery/shared-state-backup-generation-and-retention.md",
    "docs/science/collaboration/shared-conditions-and-log-access.md",
}


def verify() -> dict:
    lines = read_pinned_blob(ROOT, REVISION, ORIGINAL, BLOB).decode("utf-8").splitlines()
    assert len(lines) in (985, 986)
    rows = [json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 12
    seen = set()
    owners = {}
    for row in rows:
        uid = row["unit_id"]
        assert uid not in seen
        seen.add(uid)
        assert row["source_id"] == "SB-SRC-0557"
        assert row["source_commit"] == REVISION and row["source_blob_sha"] == BLOB
        assert row["source_material_state"] == "unaccounted"
        assert row["independent_review"] == "OPEN"
        assert row["epistemic_status"]
        m = re.fullmatch(r"L(\d+)-L(\d+)", row["source_span"])
        assert m
        a, b = map(int, m.groups())
        assert 1 <= a <= b <= len(lines)
        assert any(lines[i - 1].strip() for i in range(a, b + 1))
        path = row["science_destination"]
        assert path in PERMITTED
        if path not in owners:
            owners[path] = (ROOT / path).read_text(encoding="utf-8")
        for text in (
            uid.replace("SB-MAT-0557-", "SB-SRC-0557/"),
            row["english_research_meaning"],
            row["defeater_or_limit"],
            f"#L{a}-L{b}",
        ):
            assert text in owners[path], "Source route missing from maintained Science"
    return {
        "verdict": "FROZEN_ARTIFACT_ORIGINAL_TO_SCIENCE_TEXT_ONLY",
        "source_id": "SB-SRC-0557",
        "rows": len(rows),
        "whole_source_disposition": "unaccounted",
        "independent_review": "OPEN",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
