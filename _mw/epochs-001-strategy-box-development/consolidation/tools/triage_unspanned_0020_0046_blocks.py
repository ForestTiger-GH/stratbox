#!/usr/bin/env python3
"""Bounded reviewer triage of geometry-only original Research source gaps.

This tool does NOT decide whether any line has preserved semantic meaning.
Missing a structural ledger span is not identical to knowledge loss; having a
span is not a proof of semantic conservation. Reads exact frozen Git blobs.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from audit_research_span_routes import audit
from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "dist/research-original-0020-0046-unspanned-triage.json"
SOURCE_IDS = ("SB-SRC-0020", "SB-SRC-0046")
CENSUS = ROOT / "_mw/epochs-001-strategy-box-development/consolidation/sources/CENSUS.csv"


def classify_shape(lines: list[str]) -> str:
    # Shapes support prioritization only. Even a table/tree can encode
    # consequential business or release semantics.
    nonblank = [s.strip() for s in lines if s.strip()]
    if not nonblank:
        return "EMPTY"
    if all(s in ("---", "***") or s.startswith(("# ", "## ", "### "))
           for s in nonblank):
        return "SECTION_OR_DIVIDER_REVIEW"
    if any(s.startswith(("## ", "# ", "### ")) for s in nonblank):
        return "MIXED_HEADING_REVIEW"
    if any(s.startswith(("|", "```")) or "│" in s or "├" in s or "└" in s
           for s in nonblank):
        return "TABLE_CODE_TREE_REVIEW"
    return "PROSE_OR_LIST_REVIEW"


def main() -> dict:
    import csv
    with CENSUS.open(newline="", encoding="utf-8") as f:
        items = {r["source_id"]: r for r in csv.DictReader(f)}
    details = {r["source_id"]: r for r in audit()["source_detail"]}
    result = {"grade": "STRUCTURAL_GAP_REVIEW_PACKET_NOT_SEMANTIC_DISPOSITION",
              "originals": []}
    for sid in SOURCE_IDS:
        row, detail = items[sid], details[sid]
        raw = read_pinned_blob(ROOT, row["commit"], row["path"],
                               row["blob_sha"]).decode("utf-8")
        all_lines = raw.split("\n")
        blocks = []
        for entry in detail["completely_unspanned_blocks"]:
            m = re.fullmatch(r"L(\d+)-L(\d+)", entry["span"])
            assert m, entry
            first, last = map(int, m.groups())
            assert 1 <= first <= last <= len(all_lines)
            content = all_lines[first-1:last]
            blocks.append({
                "span": entry["span"],
                "envelope_length": len(content),
                "untraced_nonblank_in_envelope": entry["untraced_nonblank_lines"],
                "shape_hint_not_materiality": classify_shape(content),
                "source_lines_in_envelope": [
                    {"line": first+i, "text": line}
                    for i, line in enumerate(content)
                ],
                "reviewer_semantic_verdict": "NOT_REVIEWED",
            })
        summary = dict(Counter(b["shape_hint_not_materiality"] for b in blocks))
        result["originals"].append({
            "source_id": sid, "original_blob": row["blob_sha"],
            "original_ref": row["commit"], "original_source_path": row["path"],
            "nonblank_without_any_ledger_span": detail["nonblank_lines_without_any_ledger_span"],
            "envelope_block_count": len(blocks),
            "shape_only_counts": summary, "blocks": blocks,
            "source_independent_semantic_proof": "UNEXECUTED",
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(json.dumps({
        "grade": result["grade"],
        "sources": [
            {k: v for k, v in item.items() if k not in ("blocks", "original_source_path", "original_ref", "original_blob")}
            for item in result["originals"]
        ],
        "sample_unspanned_envelopes": [
            {"source": item["source_id"], "samples": [
                {"span": b["span"], "shape": b["shape_hint_not_materiality"],
                 "excerpt": " ".join(x["text"] for x in b["source_lines_in_envelope"])[:145]}
                for b in item["blocks"][:22]
            ]}
            for item in result["originals"]
        ],
        "artifact": str(OUT.relative_to(ROOT)),
    }, ensure_ascii=False))
    return result


if __name__ == "__main__":
    main()
