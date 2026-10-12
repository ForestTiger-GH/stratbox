#!/usr/bin/env python3
"""Frozen Topic 01 (20) source-to-Science probe routing; not independent PASS."""
from __future__ import annotations

import json
import re
from pathlib import Path
from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
REV = "388e3d61ec01350d3b7d35ea4a97a21db0b36f97"
SHA = "ffe6e24dfa3e542f278b7afa3dbeff09b637b935"
SRC = ("_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/"
       "01_Единая_онтология_операций_и_сценариев_Strategy_Box_2026-10-10.md")
SCIENCE = ROOT / "docs/science/capabilities/composition-identity-and-user-machine-projections.md"
EXPECTED = [f"T{i:02d}" for i in range(1, 21)]

def verify() -> dict:
    original = read_pinned_blob(ROOT, REV, SRC, SHA).decode("utf-8")
    span = original.split("### 20.1. Приёмочные проверки онтологии", 1)[1].split(
        "### 20.2. ", 1)[0]
    ids = [m.group(1) for m in re.finditer(r"^\|\s*(T\d{2})\s*\|", span, re.M)]
    assert ids == EXPECTED, ids
    assert "Эксперимент A" in original and "Эксперимент B" in original
    science = SCIENCE.read_text(encoding="utf-8")
    assert science.count("## Original Topic 01 — twenty") == 1
    portion = science.split("## Original Topic 01 — twenty", 1)[1]
    rows = [(m.group(1), m.group(2)) for m in
            re.finditer(r"^\| O01-(T\d{2}) \|([^\n]+)$", portion, re.M)]
    assert [x[0] for x in rows] == EXPECTED
    assert all(len(x[1].split("|")) >= 2 and all(len(y.strip()) >= 12
               for y in x[1].split("|")[:2]) for x in rows)
    assert all(science.count(f"| O01-{id} |") == 1 for id in EXPECTED)
    assert "Experiment A" in portion and "Experiment B" in portion
    assert "not automatically a separate Scheme" in portion
    return {
        "verdict": "20_ONTOLOGY_PROBES_AND_TWO_SCHEME_EXPERIMENTS_ROUTED",
        "source_id": "SB-SRC-0554",
        "source_blob": SHA,
        "source_probes": 20,
        "science_probes": 20,
        "experiment_forks": 2,
        "source_to_science_semantic_independent_assurance": "UNEXECUTED",
        "new_native_product_tests_executed": 0,
        "material_unit_state": "unaccounted",
    }

if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
