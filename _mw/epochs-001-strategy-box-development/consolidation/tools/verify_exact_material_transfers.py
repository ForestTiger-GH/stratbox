#!/usr/bin/env python3
"""Producer-only exact source→destination preservation check, not semantic assurance.

Run from an ordinary checkout:
  python _mw/epochs-001-strategy-box-development/consolidation/tools/verify_exact_material_transfers.py

Checks 5 bounded original-source ledgers (currently 435 exact items),
their original Git blob identities, text transfer and Science relative links.
Does not test correctness of original research, cover all 566 sources,
execute product code, certify privacy or substitute independent review.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[4]
BASE = Path("_mw/epochs-001-strategy-box-development/consolidation")
CENSUS = BASE / "sources/CENSUS.csv"
EXPECTED_ITEMS = {"0025": 98, "0032": 70, "0029": 60, "0031": 37, "0019": 77, "0033": 30, "0034": 63}

LEDGERS = (
    "PROVIDER-EXACT-VECTORS-0025.jsonl",
    "MACHINE-READINESS-EXACT-ITEMS-0032.jsonl",
    "SEMANTIC-INVARIANTS-EXACT-ITEMS-0029.jsonl",
    "COGNITIVE-BOUNDARY-EXACT-ITEMS-0031.jsonl",
    "EPISTEMIC-TESTS-AND-FIREWALLS-EXACT-0019.jsonl",
    "THREAD-WORK-UX-CHOICES-EXACT-0033.jsonl",
    "COGNITION-FOUNDATION-EXACT-ITEMS-0034.jsonl",
    "BANK-MACRO-COMPARABILITY-EXACT-0019.jsonl",
)


def read_text(path: Path) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def original_sha(path: Path) -> str:
    proc = subprocess.run(
        ["git", "hash-object", "--", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def source_lines(source: Path) -> list[str]:
    return read_text(source).splitlines()


def normalized_for_markdown(text: str) -> str:
    return text.replace("|", r"\|").replace("<", "&lt;")


def verify() -> dict:
    with (ROOT / CENSUS).open(encoding="utf-8", newline="") as stream:
        catalog = {row["source_id"]: row for row in csv.DictReader(stream)}

    issues: list[str] = []
    source_cache: dict[str, list[str]] = {}
    target_cache: dict[str, str] = {}
    by_source: dict[str, int] = {}
    verified = 0
    seen_units: set[str] = set()

    for ledger in LEDGERS:
        ledger_path = BASE / "units" / ledger
        for index, raw in enumerate(read_text(ledger_path).splitlines(), start=1):
            if not raw.strip():
                continue
            item = json.loads(raw)
            label = item["unit_id"]
            if label in seen_units:
                issues.append(f"{label}: duplicate material unit ID")
            seen_units.add(label)
            source_id = item["source_id"]
            census = catalog.get(source_id)
            if census is None:
                issues.append(f"{label}: absent census source")
                continue

            path = Path(census["path"])
            if source_id not in source_cache:
                try:
                    sha = original_sha(path)
                    if sha != census["blob_sha"]:
                        issues.append(f"{source_id}: current source Git blob differs from frozen census")
                    source_cache[source_id] = source_lines(path)
                except (OSError, subprocess.CalledProcessError) as exc:
                    issues.append(f"{source_id}: unable to open/hash source: {exc}")
                    continue
            recorded_sha = item.get("source_sha") or item.get("source_blob_sha")
            if recorded_sha != census["blob_sha"]:
                issues.append(f"{label}: recorded source SHA mismatch")

            span = item.get("source_span") or f"L{item['source_line']}"
            match = re.fullmatch(r"L(\d+)(?:-L(\d+))?", span)
            if match is None:
                issues.append(f"{label}: invalid source span")
                continue
            first = int(match.group(1))
            last = int(match.group(2) or first)
            lines = source_cache[source_id]
            if not 1 <= first <= last <= len(lines):
                issues.append(f"{label}: source span out of bounds")
                continue

            target = item.get("science_destination") or item.get("preserved_exact_test_row")
            if not target:
                issues.append(f"{label}: no destination")
                continue
            if target not in target_cache:
                try:
                    target_cache[target] = read_text(Path(target))
                except OSError:
                    issues.append(f"{label}: destination missing: {target}")
                    continue
            rendered = target_cache[target]

            # Every bounded row must contain its durable original item handle.
            destination_id = item.get("science_id") or item.get("test_id")
            if destination_id is None:
                destination_id = item["unit_id"].replace("SB-MAT-", "SB-SRC-", 1)
                # Keep exact source groups as semantic handles, not arbitrary slugs.
                destination_id = destination_id.replace(f"{source_id}-", f"{source_id}/", 1)
            if source_id == "SB-SRC-0025":
                # For original Markdown tables, preserving the entire raw row
                # is stronger and less ambiguous than string matching one cell.
                if lines[first - 1] not in rendered:
                    issues.append(f"{label}: exact original table row missing")
            elif source_id == "SB-SRC-0019":
                if destination_id not in rendered:
                    issues.append(f"{label}: original item ID missing in Science")
                expected = item.get("full_source_test_body") or item.get("original_exact_meaning")
                if expected and expected not in rendered:
                    issues.append(f"{label}: original test body/firewall missing")
                if item.get("full_source_test_body") and chr(10).join(lines[first:last]).strip() != expected:
                    issues.append(f"{label}: stored test body differs from frozen original")
                if item.get("original_exact_meaning"):
                    observed = lines[first - 1].strip()
                    if item.get("material_kind") == "macro_series_qualifier":
                        observed = observed.removeprefix("- ").strip()
                    if observed != expected:
                        issues.append(f"{label}: original source phrase changed")
            elif source_id == "SB-SRC-0033":
                if destination_id not in rendered:
                    issues.append(f"{label}: original chat/Work item ID missing")
                if item.get("original_heading"):
                    heading = item["original_heading"]
                    reason = item["original_explanation"]
                    if heading not in lines[first - 1] or reason not in lines[first + 1]:
                        issues.append(f"{label}: original source anti-pattern changed")
                    if heading not in rendered or reason not in rendered:
                        issues.append(f"{label}: chat/Work anti-pattern text missing")
                else:
                    question = item["original_question"]
                    recommendation = item["original_recommendation"]
                    if question not in lines[first - 1] or recommendation not in lines[first - 1]:
                        issues.append(f"{label}: original source UX recommendation changed")
                    if normalized_for_markdown(question) not in rendered or normalized_for_markdown(recommendation) not in rendered:
                        issues.append(f"{label}: original UX recommendation missing")
            else:
                if destination_id not in rendered:
                    issues.append(f"{label}: source-addressable item ID missing")
                meaning = (
                    item.get("material_meaning")
                    or item.get("source_exact_meaning")
                    or item.get("meaning")
                    or item.get("original_exact_meaning")
                )
                if not meaning or normalized_for_markdown(meaning) not in rendered:
                    issues.append(f"{label}: original exact wording missing")
                if source_id in ("SB-SRC-0032", "SB-SRC-0029", "SB-SRC-0034") and meaning not in lines[first - 1]:
                    issues.append(f"{label}: stored wording differs from source line")
                if source_id == "SB-SRC-0031":
                    group = item.get("source_group")
                    source_here = lines[first - 1].strip()
                    if group == "BOUNDARY_CHECK":
                        # Numbered original Research question (e.g. "1. ...").
                        if meaning not in source_here:
                            issues.append(f"{label}: readiness check differs from original")
                    elif group == "BOUNDARY_ALARM":
                        # Bullet original Research alarm (e.g. "- ...").
                        if meaning not in source_here:
                            issues.append(f"{label}: warning indicator differs from original")
                    elif group == "HOST_INVARIANT":
                        # Heading + following explanation are two distinct lines.
                        name, sep, statement = meaning.partition(" — ")
                        original_window = chr(10).join(lines[first - 1:first + 3])
                        if not sep or name not in original_window or statement not in original_window:
                            issues.append(f"{label}: host-boundary invariant differs from original")
                    else:
                        issues.append(f"{label}: unknown source group {group!r}")
            verified += 1
            by_source[source_id] = by_source.get(source_id, 0) + 1

    for sid, expected in EXPECTED_ITEMS.items():
        actual = by_source.get(f"SB-SRC-{sid}", 0)
        if actual != expected:
            issues.append(f"SB-SRC-{sid}: expected {expected} exact units, found {actual}")

    file_count = 0
    links = 0
    for doc in sorted((ROOT / "docs/science").rglob("*.md")):
        file_count += 1
        doc_rel = doc.relative_to(ROOT)
        for candidate in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
            if candidate.startswith(("#", "https:", "http:", "mailto:", "data:")):
                continue
            route = unquote(candidate.split("#", 1)[0])
            if not route:
                continue
            links += 1
            target = (doc.parent / route).resolve()
            try:
                target.relative_to(ROOT.resolve())
            except ValueError:
                issues.append(f"{doc_rel}: link escapes repository: {candidate}")
                continue
            if not target.is_file():
                issues.append(f"{doc_rel}: broken relative link: {candidate}")

    return {
        "status": "PRODUCER_EXACT_CHECK_PASS" if not issues else "PRODUCER_EXACT_CHECK_FAIL",
        "scope": "fixed five source ledgers only; independent semantic audit not performed",
        "item_count_checked": verified,
        "by_source": dict(sorted(by_source.items())),
        "science_markdown_files": file_count,
        "science_local_links_checked": links,
        "issues": issues,
    }


if __name__ == "__main__":
    try:
        result = verify()
    except Exception as exc:
        result = {"status": "CHECKER_ERROR", "message": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == "PRODUCER_EXACT_CHECK_PASS" else 1)
