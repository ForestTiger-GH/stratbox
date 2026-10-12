#!/usr/bin/env python3
"""Metadata-only line-envelope triage for ALL frozen Research originals with gaps.

This is structural geometry, not a statement of missing meaning, safe content,
independent source materiality or complete Research conservation.
"""
from __future__ import annotations
from pathlib import Path
from audit_research_span_routes import audit
from triage_unspanned_0020_0046_blocks import ROOT, packet_for

OUT = ROOT / "dist/research-original-all-unspanned-metadata-triage.json"

def main() -> dict:
    details = audit()["source_detail"]
    active = tuple(sorted(x["source_id"] for x in details
                          if x["nonblank_lines_without_any_ledger_span"] > 0))
    assert len(active) == len(set(active))
    packet = packet_for(active, OUT)
    assert packet["redaction_profile"] == "METADATA_ONLY_NO_SOURCE_TEXT"
    assert [item["source_id"] for item in packet["originals"]] == list(active)
    allowed = {"span", "envelope_length", "untraced_nonblank_in_envelope",
               "shape_hint_not_materiality", "reviewer_semantic_verdict"}
    assert all(set(block) == allowed for item in packet["originals"]
               for block in item["blocks"])
    return packet

if __name__ == "__main__":
    main()
