#!/usr/bin/env python3
"""Frozen Topic-04 A01..A20 and five storage profiles, structural only.

Conserves exact source-case identities, not production/natively tested effects.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
REV = "388e3d61ec01350d3b7d35ea4a97a21db0b36f97"
BLOB = "57ae0d79c91b8a5839668f73abfd7af4284f1142"
SOURCE = (
    "_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/"
    "04_Артефакты_и_управление_результатами_Strategy_Box_2026-10-10.md"
)
SCIENCE = ROOT / "docs/science/artifacts/output-identity-publication-and-availability.md"
EXPECTED = [f"A{i:02d}" for i in range(1, 21)]
ORIGINAL = re.compile(r"^\|\s*(A\d{2})\s*\|\s*([^|]+)\|\s*([^|]+)\|$", re.MULTILINE)
PUBLISHED = re.compile(r"^\|\s*\`(A\d{2})\`\s*\|\s*([^|]+)\|\s*([^|]+)\|$", re.MULTILINE)
PROFILES = ("NTFS/Windows", "Linux/POSIX", "SMB/NAS", "Object storage",
            "Remote host/client")


def verify() -> dict:
    frozen = read_pinned_blob(ROOT, REV, SOURCE, BLOB).decode("utf-8")
    selection = frozen.split("## 15.1. Обязательный тестовый набор для локального профиля", 1)[1].split(
        "## 15.2. Отдельные storage-conformance профили", 1)[0]
    source_cases = [(m.group(1), m.group(2).strip(), m.group(3).strip())
                    for m in ORIGINAL.finditer(selection)]
    assert [c[0] for c in source_cases] == EXPECTED, source_cases
    assert all(len(x) >= 10 and len(y) >= 10 for _, x, y in source_cases)
    profiles = frozen.split("## 15.2. Отдельные storage-conformance профили", 1)[1].split(
        "# 16. Архитектурные противоречия", 1)[0]
    for token in ("**Local NTFS/Windows:**", "**Linux/POSIX:**",
                  "**SMB/NAS:**", "**Object storage:**", "**Remote host/client:**"):
        assert token in profiles, token

    science = SCIENCE.read_text(encoding="utf-8")
    segment = science.split(
        "## Original Topic 04 — twenty exact output/publication failure cases and five storage conformance profiles",
        1)[1].split(
        "## Historical refactor 0016 — domain-by-domain candidate operation boundaries", 1)[0]
    science_cases = [(m.group(1), m.group(2).strip(), m.group(3).strip())
                     for m in PUBLISHED.finditer(segment)]
    assert [x[0] for x in science_cases] == EXPECTED, science_cases
    assert all(len(stimulus) > 20 and len(expected) > 55
               for _, stimulus, expected in science_cases)
    assert all(science.count(f"\`{case}\`") == 1 for case in EXPECTED)
    for name in PROFILES:
        assert f"| \`{name}\` |" in segment, name
    assert "UNEXECUTED" in segment and "five" in segment.lower()
    assert all(token in segment for token in (
        "ACCESS_DENIED", "OUTCOME", "MISSING", "UNAVAILABLE", "Run", "Step"))
    return {
        "verdict": "TOPIC_04_TWENTY_PRIMARY_CASE_IDENTITIES_STRUCTURALLY_PRESERVED",
        "source_id": "SB-SRC-0557",
        "source_blob": BLOB,
        "original_A_case_count": 20,
        "published_A_case_count": 20,
        "storage_conformance_profiles": 5,
        "real_native_target_execution": "UNEXECUTED",
        "independent_complete_original_semantic_assurance": "UNEXECUTED",
        "census_material_state": "unaccounted",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
