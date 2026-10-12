#!/usr/bin/env python3
"""Detach public Knowledge Markdown links from removable historical Work/Research.

This migration preserves each substantive statement, evidence limitation, historical
table row and source-position label. The source→claim identity ledger stays in
the private-to-public Work evidence area, not as a Knowledge navigation dependency.

Default mode is a read-only report. --apply changes docs/; --check fails if any
Markdown URL points into disposable source-history or Work paths.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[4]
DOCS = ROOT / "docs"
INLINE_LINK = re.compile(r"\[([^\]\n]+)\]\(([^)\n]+)\)")
REFERENCE_LINK = re.compile(r"(?m)^\s*\[[^\]\n]+\]:\s*(\S+)")
RAW_URL = re.compile(r"https?://[^\s)>\"']+")


def forbidden(target: str) -> bool:
    value = unquote(target.strip().strip("<>"))
    url = urlsplit(value)
    if url.scheme and url.scheme not in {"http", "https"}:
        return False
    path = url.path.replace("\\", "/")
    # The entire Work area is intentionally removable from the publication
    # view, not merely the original "research" child directory.
    segments = [part.lower() for part in path.split("/") if part and part != ".."]
    if "_mw" in segments or "docs_old" in segments:
        return True
    if url.scheme and "github.com" in url.netloc.lower():
        # Legacy Research paths (including a future moved corpus) are not a
        # stable external scientific dependency.
        if "research" in segments and (
            "stratbox" in segments or "stratbox-windows" in segments
        ):
            return True
    if not url.scheme and (
        path.lower().startswith("research/")
        or "/research/" in f"/{path.lower()}"
    ):
        return True
    return False


def replacement(match: re.Match[str]) -> str:
    label, target = match.group(1), match.group(2)
    if not forbidden(target):
        return match.group(0)
    # Historical source line geometry may still be asserted by producer
    # structural tests; retain it as plain informational text, never a link.
    fragment = unquote(urlsplit(target.strip()).fragment)
    span = re.search(r"L\d+(?:-L\d+)?", fragment)
    if span:
        token = f"#{span.group(0)}"
        if token not in label:
            return f"{label} (\`{token}\`)"
    return label


def errors_for(path: Path, content: str) -> list[str]:
    errors: list[str] = []
    for m in INLINE_LINK.finditer(content):
        if forbidden(m.group(2)):
            errors.append(f"{path.relative_to(ROOT)}: link target {m.group(2)[:120]}")
    for m in REFERENCE_LINK.finditer(content):
        if forbidden(m.group(1)):
            errors.append(f"{path.relative_to(ROOT)}: reference target {m.group(1)[:120]}")
    # Also catch raw or angle-bracketed links, which are not inline Markdown.
    for m in RAW_URL.finditer(content):
        if forbidden(m.group(0)):
            errors.append(f"{path.relative_to(ROOT)}: raw research URL at char {m.start()}")
    return errors


def run(apply: bool, check: bool) -> None:
    files = sorted(DOCS.rglob("*.md"))
    touched: list[str] = []
    removed = 0
    issues: list[str] = []
    for path in files:
        old = path.read_text(encoding="utf-8")
        matches = [m for m in INLINE_LINK.finditer(old) if forbidden(m.group(2))]
        removed += len(matches)
        new = INLINE_LINK.sub(replacement, old)
        if new != old:
            touched.append(str(path.relative_to(ROOT)))
            if apply:
                path.write_text(new, encoding="utf-8")
        if check:
            issues.extend(errors_for(path, new if apply else old))
    print(
        {
            "knowledge_docs": len(files),
            "detached_research_or_work_links": removed,
            "files_modified_or_needing_modification": len(touched),
            "applied": apply,
            "independence_issues": len(issues),
            "migration_type": "LINK_ONLY_PRESERVE_CLAIM_TEXT",
            "whole_source_semantic_assurance": "NOT_CERTIFIED",
        }
    )
    if issues:
        for issue in issues[:60]:
            print("FAIL", issue)
        raise SystemExit(1)
    if check and touched and not apply:
        print("INFO: remaining links must be migrated before the published docs become self-contained")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    opts = parser.parse_args()
    run(apply=opts.apply, check=opts.check)
