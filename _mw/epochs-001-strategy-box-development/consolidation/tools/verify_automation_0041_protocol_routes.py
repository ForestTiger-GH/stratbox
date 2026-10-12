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
    protocol_science = SCIENCE.read_text(encoding="utf-8")
    assert SCIENCE_HEADER in protocol_science
    assert all(url in protocol_science for url in PRIMARY_SPEC_URLS), "primary specification route missing"

    packet_specs = (
        (LEDGER, 7, {"docs/science/capabilities/machine-discovery-bindings-and-adapters.md"}),
        (
            ROOT / "_mw/epochs-001-strategy-box-development/consolidation/units/AUTOMATION-0041-TRIGGER-AUTONOMY-24.jsonl",
            24,
            {
                "docs/science/automation/trigger-occurrence-identity-and-governed-execution.md",
                "docs/science/automation/bounded-agent-routing-and-evidence-safe-automation.md",
            },
        ),
    )
    docs = {}
    seen = set()
    counts = []
    for packet_path, expected, permitted in packet_specs:
        rows = [json.loads(x) for x in packet_path.read_text(encoding="utf-8").splitlines() if x.strip()]
        assert len(rows) == expected, f"{packet_path}: expected {expected}, got {len(rows)}"
        for row in rows:
            uid = row["unit_id"]
            assert uid not in seen, f"duplicated material unit ID {uid}"
            seen.add(uid)
            assert row["source_id"] == "SB-SRC-0041"
            assert row["source_blob_sha"] == BLOB
            assert row["source_commit"] == "8459dc58922b7e8df853cf1d9e8131fa9e132580"
            assert row["independent_review"] == "OPEN"
            assert (row.get("material_state") or row.get("source_material_state")) == "unaccounted"
            assert row["epistemic_status"].strip()
            caveat = row.get("defeater_or_limit") or row.get("counterexample_or_limit")
            assert caveat and caveat.strip()
            dest = row["science_destination"]
            assert dest in permitted, f"{uid}: out-of-scope Science destination {dest}"
            if dest not in docs:
                docs[dest] = (ROOT / dest).read_text(encoding="utf-8")
            science = docs[dest]
            assert row["english_research_meaning"] in science, f"{uid}: missing English meaning"
            assert caveat in science, f"{uid}: missing counterexample or limit"
            assert uid.replace("SB-MAT-0041-", "SB-SRC-0041/") in science, f"{uid}: missing Science identity"
            span = re.fullmatch(r"L(\d+)-L(\d+)", row["source_span"])
            assert span, f"{uid}: invalid locator"
            a, b = map(int, span.groups())
            assert 1 <= a <= b <= len(lines), f"{uid}: out-of-range locator"
            assert any(lines[i - 1].strip() for i in range(a, b + 1)), f"{uid}: empty source passage"
            assert "#L" + str(a) + "-L" + str(b) in science, f"{uid}: missing source anchor"
        counts.append({"ledger":packet_path.name, "rows":len(rows), "structural_transfers":len(rows)})
    return {
        "verdict": "SOURCE_IDENTITY_AND_DESTINATION_TEXT_ONLY_NOT_INDEPENDENT_SEMANTIC_PASS",
        "source": "SB-SRC-0041",
        "packet_counts": counts,
        "total_rows": len(seen),
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
