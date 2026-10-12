#!/usr/bin/env python3
"""Pinned 0020 date-qualified proposal source↔Science addresses.

Ensures exact source heading-span boundaries and published candidate English
countercases; no independent Research material judgment or Windows execution.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "_mw/epochs-001-strategy-box-development/consolidation"
LEDGER = BASE / "units/WINDOWS-STUDY-0020-DATED-PRIORITIES-AND-ROADMAP-17.jsonl"
SOURCE = ("_mw/epochs-001-strategy-box-development/research/02-base-study/"
          "stratbox-windows_current_state_full_research_2026-10-06.md")
REV = "8459dc58922b7e8df853cf1d9e8131fa9e132580"
BLOB = "225128f2599f0792422c0b31cb3cbe1437991ced"
P_SCI = "docs/science/architecture/product-system-model-actors-and-repository-boundaries.md"
RM_SCI = "docs/science/surfaces/semantic-portability-and-client-authority.md"

def science_rows(path: str, start: str, finish: str, prefix: str) -> list[list[str]]:
    content = (ROOT / path).read_text(encoding="utf-8")
    section = content.split(start, 1)[1].split(finish, 1)[0]
    return [list(map(str.strip, line[1:-1].split("|")))
            for line in section.splitlines() if line.startswith("| " + prefix)]

def verify() -> dict:
    original = read_pinned_blob(ROOT, REV, SOURCE, BLOB).decode("utf-8").splitlines()
    p = [(i+1, int(m.group(1)), m.group(2)) for i, line in enumerate(original)
         if (m := re.match(r"^## (7[1-9]|8[0-2])\\. (P[012]) ", line))]
    rm = [(i+1, int(m.group(1))) for i, line in enumerate(original)
          if (m := re.match(r"^## Этап ([1-5]) — ", line))]
    assert [n for _, n, _ in p] == list(range(71, 83))
    assert [n for _, n in rm] == [1, 2, 3, 4, 5]
    p_end = next(i for i, line in enumerate(original) if line.startswith("# XXI. Потенциал развития"))
    rm_end = next(i for i, line in enumerate(original) if line.startswith("# XXIV. Что сейчас уже является продуктом"))
    ledger = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line]
    assert len(ledger) == 17
    p_science = science_rows(P_SCI, "## Original Windows Research 0020: twelve dated P0–P2 modernization choices",
                             "## Original topic 10:", "W20-P")
    rm_science = science_rows(RM_SCI, "## Dated Windows study 0020: five proposed implementation stages",
                              "## Original application note 0014", "W20-RM")
    assert len(p_science) == 12 and len(rm_science) == 5
    expected = {}
    for index, (start, n, grade) in enumerate(p):
        end = (p[index+1][0] if index+1 < len(p) else p_end)-1
        cells = next(c for c in p_science if c[0] == f"W20-P{n}")
        assert cells[1] == grade and len(cells) == 4
        expected[f"SB-MAT-0020-P{n}"] = (f"L{start}-L{end}", P_SCI, cells[2], cells[3])
    for index, (start, n) in enumerate(rm):
        end = (rm[index+1][0] if index+1 < len(rm) else rm_end)-1
        cells = next(c for c in rm_science if c[0] == f"W20-RM{n}")
        assert len(cells) == 3
        expected[f"SB-MAT-0020-RM{n}"] = (f"L{start}-L{end}", RM_SCI, cells[1], cells[2])
    assert {x["unit_id"] for x in ledger} == set(expected)
    for row in ledger:
        assert (row["source_id"], row["source_blob_sha"], row["source_commit"]) == ("SB-SRC-0020", BLOB, REV)
        assert (row["source_span"], row["science_destination"], row["english_research_meaning"],
                row["defeater_or_limit"]) == expected[row["unit_id"]]
        assert row["source_material_state"] == "unaccounted" and row["independent_review"] == "OPEN"
    return {"status": "SOURCE_0020_17_PROPOSAL_SPANS_PRODUCER_ONLY",
            "p0_p2_source_sections": len(p), "dated_source_stages": len(rm),
            "exact_provisional_unit_routes": len(ledger),
            "whole_original_material_state": "unaccounted",
            "independent_review": "UNEXECUTED",
            "native_host_client_tests": "UNEXECUTED"}

if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
