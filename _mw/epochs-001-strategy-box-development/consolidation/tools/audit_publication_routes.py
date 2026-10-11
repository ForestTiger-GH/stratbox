#!/usr/bin/env python3
"""Check publication routing only; no semantic or independent assurance verdict."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[4]
DOCS = ROOT / "docs"
PATTERN = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^)\n]+)\)")
HOST_OWNERS = (
    "docs/what/strategy-box/host-deployment-commitment.md",
    "docs/what/strategy-box/commitment-census.md",
    "docs/how/hosting/host-and-client-deployment.md",
    "docs/architecture/responsibility-allocation.md",
    "docs/ldd/hosting/host-client-attachment-boundary.md",
)
EXTERNAL = ("https:", "http:", "mailto:", "data:", "tel:", "//")

def visible_markdown(text: str) -> str:
    lines = []
    inside = False
    for line in text.splitlines():
        if line.lstrip().startswith(chr(96) * 3) or line.lstrip().startswith("~~~"):
            inside = not inside
            continue
        if not inside:
            lines.append(line)
    return "\n".join(lines)

def check_links() -> tuple[list[str], int, int]:
    errors = []
    paths = sorted(DOCS.rglob("*.md"))
    count = 0
    for p in paths:
        body = visible_markdown(p.read_text(encoding="utf-8"))
        for m in PATTERN.finditer(body):
            raw = m.group(1).strip().split(' "', 1)[0].strip("<>")
            href = unquote(raw.split("#", 1)[0].split("?", 1)[0])
            if not href or href.startswith(EXTERNAL):
                continue
            count += 1
            dest = (p.parent / href).resolve()
            if not dest.is_relative_to(ROOT.resolve()) or not dest.is_file():
                errors.append(f"{p.relative_to(ROOT)}: missing or escaping local link {raw!r}")
    return errors, len(paths), count

def check_host_route() -> list[str]:
    errors = []
    for path in HOST_OWNERS:
        f = ROOT / path
        if not f.is_file():
            errors.append(f"Missing canonical host owner: {path}")
            continue
        text = f.read_text(encoding="utf-8")
        if not any(s in text for s in ("PD-SB-HOST-2026-10-12-01", "HOST-O1", "PC-SB-003")):
            errors.append(f"Host commitment identity not routed: {path}")
    source = ROOT / HOST_OWNERS[0]
    if source.is_file():
        body = source.read_text(encoding="utf-8")
        for i in range(1, 8):
            if f"HOST-O{i}" not in body:
                errors.append(f"Admitted host invariant HOST-O{i} omitted")
    return errors

if __name__ == "__main__":
    try:
        errors, docs, links = check_links()
        errors += check_host_route()
    except Exception as exc:
        print(f"PUBLICATION_ROUTE_CHECKER_ERROR {exc!r}", file=sys.stderr)
        raise
    print({"verdict": "STRUCTURAL_NAVIGATION_ONLY_NOT_SEMANTIC_PASS", "docs": docs, "internal_file_links": links, "host_owner_routes": len(HOST_OWNERS), "issues": len(errors)})
    for e in errors[:100]:
        print(e, file=sys.stderr)
    sys.exit(1 if errors else 0)
