"""Check that maintained historical source links point to real Git objects.

Git revision and path are a single evidence locator. A modern path must never
be silently substituted into a pinned historical revision. Run with a
non-shallow repository when validating older revisions.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(
    r"https://github[.]com/ForestTiger-GH/stratbox/blob/"
    r"([0-9a-fA-F]{40})/([^\\s)<>\\]\"']+)"
)


def pinned_links(text: str):
    """Yield revision, decoded file path, and source line for each pinned link."""
    for match in LINK.finditer(text):
        revision = match.group(1).lower()
        raw = match.group(2).split("#", 1)[0].split("?", 1)[0]
        relative = unquote(raw)
        line = text.count("\n", 0, match.start()) + 1
        yield revision, relative, line


def validate_pinned_links(documents: list[Path], *, repository: Path = ROOT) -> list[str]:
    """Validate exact Git blob objects, deduplicating lookups across documents."""
    issues = []
    cache: dict[tuple[str, str], bool] = {}
    for document in documents:
        content = document.read_text(encoding="utf-8")
        for revision, path, line in pinned_links(content):
            parts = path.split("/")
            if not parts or any(part in {"", ".", ".."} for part in parts) or "\\" in path:
                issues.append(f"{document}:{line}: invalid source path {path!r}")
                continue
            key = (revision, path)
            if key not in cache:
                checked = subprocess.run(
                    ["git", "cat-file", "-t", f"{revision}:{path}"],
                    cwd=repository,
                    capture_output=True, text=True, check=False,
                )
                cache[key] = checked.returncode == 0 and checked.stdout.strip() == "blob"
            if not cache[key]:
                issues.append(f"{document}:{line}: pinned source absent at {revision}:{path}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "docs/current-how")
    args = parser.parse_args()
    if not (ROOT / ".git").exists():
        parser.error("full Git history is required for revision-pinned verification")
    documents = sorted(args.directory.rglob("*.md"))
    if not documents:
        parser.error("no maintained documents found")
    issues = validate_pinned_links(documents)
    for issue in issues:
        print(issue)
    print(f"Checked {len(documents)} maintained documents; invalid revision-pinned paths: {len(issues)}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
