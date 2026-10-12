#!/usr/bin/env python3
"""Exercise Markdown navigation with *only* copied docs/ available.

This reproduces the user-controlled scenario in which every historical
Research/Work/legacy source tree is deleted. It cannot certify that the original
Research was completely conserved, which remains a different assurance gate.
"""
from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "docs"
LINK = re.compile(r"\[([^\]\n]+)\]\(([^)\n]+)\)")


def prove() -> dict[str, object]:
    problems: list[str] = []
    navigated = 0
    with tempfile.TemporaryDirectory(prefix="stratbox-science-no-research-") as temp:
        # The temp directory has ONLY the published Knowledge. No _mw,
        # historical research, legacy docs or repo source code exists there.
        target_root = Path(temp) / "docs"
        shutil.copytree(SOURCE, target_root)
        files = sorted(target_root.rglob("*.md"))
        for file in files:
            body = file.read_text(encoding="utf-8")
            for match in LINK.finditer(body):
                destination = match.group(2).strip()
                parsed = urlsplit(unquote(destination))
                if parsed.scheme or parsed.netloc or destination.startswith("#"):
                    # External public direct-code or standards citations are
                    # optional evidence references, not local archive links.
                    continue
                pure = parsed.path
                if not pure:
                    continue
                resolved = (file.parent / pure).resolve()
                navigated += 1
                if not resolved.is_relative_to(target_root.resolve()):
                    problems.append(
                        f"{file.relative_to(target_root)}: outside docs-only archive: {destination}"
                    )
                elif not resolved.exists():
                    problems.append(
                        f"{file.relative_to(target_root)}: missing docs-only target: {destination}"
                    )
    result = {
        "verdict": "STANDALONE_DOCS_MARKDOWN_NAVIGATION_ONLY",
        "knowledge_md_files": len(files),
        "relative_links_checked": navigated,
        "forbidden_or_missing_links": len(problems),
        "research_work_archive_present": False,
        "semantic_research_amputation": "UNEXECUTED",
        "independent_content_review": "OPEN",
    }
    print(json.dumps(result, ensure_ascii=False))
    for issue in problems[:30]:
        print("FAIL", issue)
    if problems:
        raise SystemExit(1)
    return result


if __name__ == "__main__":
    prove()
