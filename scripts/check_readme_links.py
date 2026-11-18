"""Check local links in maintained Stratbox package README files.

Checks paths only; external URLs and fragment-only links are intentionally
out of scope. Markdown under archives and research workspaces is not scanned.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
README_ROOT = ROOT / "src" / "stratbox"
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^\n]+?)\)")


def local_link_paths(markdown: str) -> tuple[str, ...]:
    """Extract inline Markdown destinations outside fenced code samples."""
    active = True
    result: list[str] = []
    for line in markdown.splitlines():
        if line.lstrip().startswith(("'''", "```")):
            active = not active
            continue
        if not active:
            continue
        for match in MARKDOWN_LINK.finditer(line):
            raw = match.group(1).strip()
            if raw.startswith("<"):
                raw = raw[1:].split(">", 1)[0]
            else:
                raw = raw.split(' "', 1)[0].split(" '", 1)[0]
            uri = urlsplit(raw)
            if uri.scheme or uri.netloc or raw.startswith(("#", "//")):
                continue
            if uri.path:
                result.append(unquote(uri.path))
    return tuple(result)


def check_links(root: Path = README_ROOT, *, repository: Path = ROOT) -> list[str]:
    """Return diagnostics for escaped or missing local destinations."""
    failures = []
    repo_root = repository.resolve()
    for readme in sorted(root.rglob("README.md")):
        for href in local_link_paths(readme.read_text(encoding="utf-8")):
            # Repository-relative links are expressed via normal relative paths.
            resolved = (readme.parent / href).resolve()
            if not resolved.is_relative_to(repo_root):
                failures.append(f"{readme.relative_to(repo_root)}: link escapes repository: {href}")
            elif not resolved.exists():
                failures.append(f"{readme.relative_to(repo_root)}: missing link: {href}")
    return failures


def main() -> int:
    failures = check_links()
    for problem in failures:
        print("FAIL", problem)
    if failures:
        return 1
    print("OK maintained Stratbox README links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
