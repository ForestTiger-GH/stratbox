#!/usr/bin/env python3
"""Pinned FRG/SORS legacy full-read source guards; producer routes only."""
from __future__ import annotations
import csv,json,re
from pathlib import Path
from pinned_source import read_pinned_blob
ROOT=Path(__file__).resolve().parents[4]
REV="8459dc58922b7e8df853cf1d9e8131fa9e132580"
CENSUS=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/sources/CENSUS.csv"
LEDGER=ROOT/"_mw/epochs-001-strategy-box-development/consolidation/units/FRG-SORS-LEGACY-ORIGINALS-09.jsonl"
SCIENCE_FRG=ROOT/"docs/science/data-and-knowledge/frg-file-selection-cleanup-and-effects.md"
SCIENCE_SORS=ROOT/"docs/science/data-and-knowledge/sors-evidence-surfaces-crosswalk-and-audit.md"
def verify():
    with CENSUS.open(newline="",encoding="utf-8") as f:
        refs={x["source_id"]:x for x in csv.DictReader(f)}
    rows=[json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows)==9 and {x["source_id"] for x in rows}=={"SB-SRC-0064","SB-SRC-0074","SB-SRC-0081"}
    for sid in ("SB-SRC-0064","SB-SRC-0074","SB-SRC-0081"):
        assert refs[sid]["read_state"]=="full_read" and refs[sid]["material_unit_state"]=="unaccounted"
    for i,item in enumerate(rows,1):
        assert item["unit_id"]==f"SB-MAT-LEGACY-FRG-SORS-{i:02d}"
        assert item["source_commit"]==REV and item["source_path"]==refs[item["source_id"]]["path"]
        assert item["source_blob_sha"]==refs[item["source_id"]]["blob_sha"]
        lines=read_pinned_blob(ROOT,REV,item["source_path"],item["source_blob_sha"]).decode("utf-8").splitlines()
        mat=re.fullmatch(r"L(\d+)(?:-L(\d+))?",item["source_span"]);assert mat
        lo=int(mat.group(1)); hi=int(mat.group(2) or lo)
        assert 1<=lo<=hi<=len(lines) and any(t.strip() for t in lines[lo-1:hi])
        assert item["source_material_state"]=="unaccounted" and item["independent_review"]=="OPEN"
    frg=SCIENCE_FRG.read_text(encoding="utf-8")
    sors=SCIENCE_SORS.read_text(encoding="utf-8")
    for phrase in ("April 1, 2026","plan identity","ZIP","superseded_by_newer_week_in_same_month"):
        assert phrase in frg,phrase
    for phrase in ("four evidence tiers","five tiers","3 million rubles","1%"):
        assert phrase in sors,phrase
    print(json.dumps({"verdict":"THREE_FULL_HISTORIC_READS_AND_PUBLICATION_ONLY_MEANING","historical_sources":3,"units":9,"independent_assurance":"OPEN"}))
if __name__=="__main__":verify()
