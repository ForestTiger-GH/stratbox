#!/usr/bin/env python3
"""Read byte-precise frozen Git sources even after a public working-copy revision.

Frozen source rows have an original commit, path and Git blob SHA. Never replace
this identity with present checkout bytes or a redacted working-tree copy.
A missing original commit is an explicit error rather than a fallback.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path


def read_pinned_blob(root: Path, revision: str, path: str, expected_sha: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("A full frozen Git commit SHA is required")
    if not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
        raise ValueError("A full frozen Git blob SHA is required")
    relative = Path(path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Only repository-relative frozen source paths are valid")
    raw = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if actual != expected_sha:
        raise ValueError("Original Git source blob has a hash mismatch")
    return raw
