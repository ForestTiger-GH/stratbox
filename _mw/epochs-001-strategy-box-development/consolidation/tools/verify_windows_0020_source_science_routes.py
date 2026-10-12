#!/usr/bin/env python3
"""Frozen Windows Research original source-to-Science text routing, not independent semantics."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ORIGINAL = ROOT / "_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md"
LEDGERS = (
    ("WINDOWS-STUDY-0020-DIRECT-RECONCILIATION-09.jsonl", 9),
    ("WINDOWS-STUDY-0020-RUNTIME-WORKROOM-18.jsonl", 18),
    ("WINDOWS-STUDY-0020-FUTURE-AND-PORTABILITY-15.jsonl", 15),
)
UNITS_ROOT = ROOT / "_mw/epochs-001-strategy-box-development/consolidation/units"
SOURCE_SHA = "225128f2599f0792422c0b31cb3cbe1437991ced"
SOURCE_COMMIT = "8459dc58922b7e8df853cf1d9e8131fa9e132580"
SCOPED = {
    "docs/science/capabilities/definitions-plans-and-execution-truth.md",
    "docs/science/work/admission-planning-resource-scheduling-and-recovery.md",
    "docs/science/automation/trigger-occurrence-identity-and-governed-execution.md",
    "docs/science/deployment/headless-host-web-security-and-persistence-tradeoffs.md",
    "docs/science/automation/bounded-agent-routing-and-evidence-safe-automation.md",
    "docs/science/artifacts/output-identity-publication-and-availability.md",
    "docs/science/surfaces/semantic-portability-and-client-authority.md",
    "docs/science/engineering/proportional-assurance-and-knowledge-admission.md",
    "docs/science/surfaces/explorer-workroom-and-operational-desktop-interaction.md",
    "docs/science/collaboration/shared-conditions-and-log-access.md",
}


def verify() -> dict:
    raw = ORIGINAL.read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    assert actual == SOURCE_SHA, f"Original blob identity mismatch: {actual}"
    source_lines = raw.decode("utf-8").splitlines()
    rows = []
    for filename, expected in LEDGERS:
        entry_rows = [json.loads(line) for line in (UNITS_ROOT / filename).read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(entry_rows) == expected, filename
        rows.extend(entry_rows)
    assert len(rows) == 42
    seen = set()
    for row in rows:
        identity = row["unit_id"]
        assert identity not in seen, identity
        seen.add(identity)
        assert row["source_id"] == "SB-SRC-0020"
        assert row["source_blob_sha"] == SOURCE_SHA
        assert row["source_commit"] == SOURCE_COMMIT
        assert row["science_destination"] in SCOPED
        assert row["source_material_state"] == "unaccounted"
        assert row["independent_review"] == "OPEN"
        assert row["defeater_or_limit"].strip()
        m = re.fullmatch(r"L(\d+)-L(\d+)", row["source_span"])
        assert m
        a, b = map(int, m.groups())
        assert 1 <= a <= b <= len(source_lines)
        assert any(source_lines[i - 1].strip() for i in range(a, b + 1))
        text = (ROOT / row["science_destination"]).read_text(encoding="utf-8")
        assert identity.replace("SB-MAT-0020-", "SB-SRC-0020/") in text
        assert row["english_research_meaning"] in text
        assert row["defeater_or_limit"] in text
        assert f"#L{a}-L{b}" in text
    return {
        "status": "STRUCTURAL_SOURCE_TO_SCIENCE_ONLY",
        "source_id": "SB-SRC-0020",
        "source_blob_sha": SOURCE_SHA,
        "physical_source_lines": len(source_lines),
        "addresses_checked": len(seen),
        "material_state": "unaccounted",
        "independent_review": "OPEN",
    }


if __name__ == "__main__":
    print(json.dumps(verify()))
