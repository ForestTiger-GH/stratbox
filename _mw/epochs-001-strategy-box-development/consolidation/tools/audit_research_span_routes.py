#!/usr/bin/env python3
"""Exhaustive STRUCTURAL Research-ledger span audit, never a semantic lossless verdict.

Reads already-maintained frozen census and existing JSONL ledgers in place;
does not issue new source identities or reinterpret Research as Product Decisions.
Run: python3 .../audit_research_span_routes.py [--top N]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import defaultdict, Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[4]
ROLES = {"historical_research", "base_research", "consolidation_research", "ai_raised_research"}
ORIENTATIONS = {"SB-SRC-0012", "SB-SRC-0017", "SB-SRC-0045"}
SPAN = re.compile(r"^L([0-9]+)(?:-L?([0-9]+))?$")

def git_blob(path: Path) -> str:
    return subprocess.run(
        ["git", "hash-object", "--", str(path)], cwd=ROOT, check=True,
        text=True, capture_output=True
    ).stdout.strip()

def source_locator(item: dict) -> str | None:
    raw = item.get("source_span")
    if raw:
        return str(raw)
    line = item.get("source_line")
    return f"L{line}" if isinstance(line, int) and line > 0 else None

def destination(item: dict) -> str | None:
    raw = item.get("science_destination") or item.get("preserved_exact_test_row")
    if not isinstance(raw, str):
        return None
    text = raw.split(" §", 1)[0].strip()
    return text if text.startswith("docs/science/") else None

def kind(item: dict, ledger: str) -> str:
    if (ledger.startswith(("SECTION-INDEX-", "RESEARCH-ORIGINAL-CANDIDATE-ROUTING-"))
            or item.get("status") == "section_locator_only_semantic_equivalence_unverified"):
        return "section_or_route"
    if ledger.startswith(("PROVIDER-EXACT-", "TOPIC08-EXACT-", "BANK-MACRO-COMPARABILITY-EXACT-",
                          "COGNITION-FOUNDATION-EXACT-", "COGNITIVE-BOUNDARY-EXACT-",
                          "EPISTEMIC-TESTS-AND-FIREWALLS-EXACT-", "MACHINE-READINESS-EXACT-",
                          "SEMANTIC-INVARIANTS-EXACT-", "THREAD-WORK-UX-CHOICES-EXACT-")):
        return "source_exact_transfer"
    if "ENGLISH" in ledger or "english_research_meaning" in item or "english_expected_property" in item:
        return "producer_english_interpretation"
    if item.get("read_status"):
        return "direct_source_read"
    return "provisional_semantic"

def holes(lines: list[str], seen: set[int], minimum: int = 6) -> list[dict]:
    # Physical line blocks are a triage hint only, not a judgment of materiality.
    misses = [i for i, text in enumerate(lines, 1) if text.strip() and i not in seen]
    blocks: list[list[int]] = []
    for i in misses:
        if not blocks or i - blocks[-1][-1] > 2:
            blocks.append([i])
        else:
            blocks[-1].append(i)
    return [
        {"span": f"L{b[0]}-L{b[-1]}", "untraced_nonblank_lines": len(b)}
        for b in blocks if len(b) >= minimum
    ]

def audit() -> dict:
    with (BASE / "sources/CENSUS.csv").open(newline="", encoding="utf-8") as f:
        census = list(csv.DictReader(f))
    study = {r["source_id"]: r for r in census
             if r["role"] in ROLES and r["source_id"] not in ORIENTATIONS}
    structural_issues: list[str] = []
    register: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for path in sorted((BASE / "units").glob("*.jsonl")):
        for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as e:
                structural_issues.append(f"{path.name}:{i}: JSONL decode: {e}")
                continue
            sid = row.get("source_id")
            if sid in study:
                register[sid].append((path.name, row))
    totals = Counter()
    detail = []
    for sid, r in sorted(study.items()):
        source = ROOT / r["path"]
        if not source.is_file():
            structural_issues.append(f"{sid}: source missing from checkout")
            continue
        current_sha = git_blob(source)
        if current_sha != r["blob_sha"]:
            structural_issues.append(f"{sid}: frozen source blob differs: {current_sha}")
        lines = source.read_text(encoding="utf-8").splitlines()
        nonblank = {i for i, line in enumerate(lines, 1) if line.strip()}
        observed: set[int] = set()
        candidate: set[int] = set()
        counts = Counter()
        unique_destinations = set()
        bad_destinations = set()
        for ledger, item in register[sid]:
            typ = kind(item, ledger)
            counts[typ] += 1
            recorded_sha = item.get("source_blob_sha") or item.get("source_sha")
            if recorded_sha and recorded_sha != r["blob_sha"]:
                structural_issues.append(f"{sid}/{ledger}: recorded blob mismatch")
            loc = source_locator(item)
            if not loc:
                continue
            m = SPAN.fullmatch(loc)
            if not m:
                structural_issues.append(f"{sid}/{ledger}: malformed span {loc!r}")
                continue
            start, finish = int(m.group(1)), int(m.group(2) or m.group(1))
            if start < 1 or finish > len(lines) or finish < start:
                structural_issues.append(f"{sid}/{ledger}: out-of-bound span {loc!r}")
                continue
            target_set = candidate if typ == "section_or_route" else observed
            target_set.update(range(start, finish + 1))
            dest = destination(item)
            if dest:
                unique_destinations.add(dest)
                if not (ROOT / dest).is_file():
                    bad_destinations.add(dest)
        for broken in sorted(bad_destinations):
            structural_issues.append(f"{sid}: Science destination missing: {broken}")
        traced_nonblank = len(nonblank & observed)
        total_nonblank = len(nonblank)
        totals["research_nonblank_source_lines"] += total_nonblank
        totals["nonblank_lines_with_some_nonrouting_ledger_span"] += traced_nonblank
        totals["research_sources_with_ledger_spans"] += bool(observed)
        totals["research_sources_with_science_destination"] += bool(unique_destinations)
        totals["research_originals"] += 1
        observed_holes = holes(lines, observed)
        detail.append({
            "source_id": sid, "source_path": r["path"],
            "source_blob_sha": r["blob_sha"], "source_lines": len(lines),
            "nonblank_lines": total_nonblank,
            "nonblank_lines_with_some_nonrouting_span": traced_nonblank,
            "coverage_ratio_not_semantic_preservation": (
                round(traced_nonblank / total_nonblank, 4) if total_nonblank else None),
            "ledger_classes": dict(sorted(counts.items())),
            "distinct_candidate_science_destinations": len(unique_destinations),
            "long_untraced_line_blocks": observed_holes[:12],
            "unreported_additional_blocks": max(0, len(observed_holes) - 12),
            "role": r["role"]
        })
    detail.sort(key=lambda x: (x["coverage_ratio_not_semantic_preservation"] or 0, x["source_id"]))
    return {
        "status": "STRUCTURAL_INTEGRITY_PASS_WITH_SEMANTIC_ASSURANCE_OPEN"
        if not structural_issues else "STRUCTURAL_INTEGRITY_FAIL",
        "verdict_boundary": "CANNOT_CERTIFY_LOSSLESS_OR_RESEARCH_AMPUTATION",
        "source_universe": "frozen original Research population only; all other source roles still require their own current evidence work",
        "source_rows_entire_census": len(census),
        "research_originals_expected": len(study),
        "counts": dict(sorted(totals.items())),
        "important_warning": (
            "A line covered by a provisional ledger is NOT preserved meaning. "
            "A line uncovered by ledger spans may be boilerplate, formatting or a real material omission. "
            "Repeated overlapping ledgers do not yield independent corroboration. "
            "Source and destination identity checks do not perform Science-to-ground semantic checking."
        ),
        "sources_lowest_structural_coverage": detail[:15],
        "source_detail": detail,
        "structural_issues_count": len(structural_issues),
        "structural_issues": structural_issues[:100]
    }

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()
    try:
        result = audit()
        # CI logs should give a compact, actionable head; full report is an
        # optional stdout redirect that can be retained as run evidence.
        result["sources_lowest_structural_coverage"] = result["source_detail"][:max(0, args.top)]
        result.pop("source_detail")
    except Exception as e:
        result = {"status": "STRUCTURAL_AUDIT_ERROR", "error": repr(e)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == "STRUCTURAL_INTEGRITY_PASS_WITH_SEMANTIC_ASSURANCE_OPEN" else 1)
