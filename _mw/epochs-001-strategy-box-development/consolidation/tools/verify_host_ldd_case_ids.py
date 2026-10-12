#!/usr/bin/env python3
"""Guard unique HC host LDD test-definition IDs; mentions and ranges are not definitions."""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OWNER = ROOT / "docs/ldd/hosting/host-client-attachment-boundary.md"


def verify() -> dict[str, object]:
    text = OWNER.read_text(encoding="utf-8")
    definitions = [int(x) for x in re.findall(r"^\|\s*HC-(\d+)\s*\|", text, flags=re.M)]
    assert definitions, "No HC vector definitions found"
    collisions = sorted({x for x in definitions if definitions.count(x) > 1})
    assert not collisions, f"Duplicate HC definition numbers: {collisions}"
    for idx in range(34, 52):
        assert idx in definitions, f"Expected HC-{idx} missing"
    for x in range(40, 46):
        assert f"| HC-{x} |" in text
    return {
        "status": "HOST_LDD_VECTOR_IDENTITY_ONLY",
        "unique_definitions": len(definitions),
        "collisions": 0,
        "source_code_execution": "not tested by this script",
    }


if __name__ == "__main__":
    print(verify())
