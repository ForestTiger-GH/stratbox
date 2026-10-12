#!/usr/bin/env python3
"""Check frozen original 0018 numbered default rows and staged alternatives.

This checks historical source and public Science structural identity ONLY.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
SOURCE = (
    "_mw/epochs-001-strategy-box-development/research/02-base-study/"
    "Strategy_Box_background_jobs_processes_architecture_research_2026-10-08.md"
)
REV = "8459dc58922b7e8df853cf1d9e8131fa9e132580"
BLOB = "5ed80eeb3065b60f89d0706bfa49bbfd272fc066"
SCIENCE = ROOT / "docs/science/work/admission-planning-resource-scheduling-and-recovery.md"

def verify() -> dict:
    original = read_pinned_blob(ROOT, REV, SOURCE, BLOB).decode("utf-8")
    defaults = original.split("## 55. Рекомендуемые defaults", 1)[1].split(
        "## 56. Архитектурные вопросы с последствиями", 1)[0]
    choices = [
        s for s in defaults.splitlines()
        if s.startswith("|") and not s.startswith("|---") and not s.startswith("| Решение")
    ]
    assert len(choices) == 13, len(choices)
    original_questions = original.split(
        "## 56. Архитектурные вопросы с последствиями", 1)[1].split(
        "# XVII. Консолидированный вывод", 1)[0]
    assert len(re.findall(r"^\d\. \*\*", original_questions, re.M)) == 7
    original_stages = original.split("## 52. Основной принцип",1)[1].split(
        "## 53. Что переработать",1)[0]
    assert re.findall(r"^### Шаг (\d)\.", original_stages, re.M) == list("0123456")
    science = SCIENCE.read_text(encoding="utf-8")
    segment = science.split("### Historical defaults, open profile choices and vertical rollout",1)[1].split(
        "## 15. Source topic 02:",1)[0]
    for prefix, count in (("BG-DEF", 13), ("BG-OPEN", 7), ("BG-STAGE", 7)):
        digits = 1 if prefix == "BG-STAGE" else 2
        ids = re.findall(r"^\| (" + prefix + r"-\d{" + str(digits) + r"})", segment, re.M)
        expected = [f"{prefix}-{i:0{digits}d}" for i in range(1, count + 1)] if digits == 2 else [
            f"{prefix}-{i}" for i in range(count)
        ]
        assert ids == expected, (prefix, ids, expected)
    for marker in ("not a binding implementation plan", "not a present user setting",
                   "no-legacy-backward-compatibility", "logical", "physical",
                   "UN", "permission", "Run"):
        assert marker.lower() in segment.lower(), marker
    return {
        "verdict": "0018_HISTORICAL_DEFAULTS_AND_STAGES_STRUCTURAL_ONLY",
        "source_id": "SB-SRC-0018", "blob": BLOB,
        "source_default_rows": 13, "source_open_questions": 7,
        "source_stages": 7, "real_acceptance": "UNEXECUTED",
        "independent_source_semantic_review": "UNEXECUTED",
        "source_material_state": "unaccounted",
    }

if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
