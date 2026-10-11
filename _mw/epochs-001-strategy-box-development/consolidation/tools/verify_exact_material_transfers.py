#!/usr/bin/env python3
"""Producer-only source identity, English destination presence and link check.

Run from an ordinary checkout:
  python _mw/epochs-001-strategy-box-development/consolidation/tools/verify_exact_material_transfers.py

Checks source-ledger entries (currently 1131 items): exact original SHA/line,
maintained English rendering or source-exact destination and relative links.
Does not test correctness of original research, cover all 566 sources,
execute product code, certify privacy or substitute independent review.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[4]
BASE = Path("_mw/epochs-001-strategy-box-development/consolidation")
CENSUS = BASE / "sources/CENSUS.csv"
EXPECTED_ITEMS = {"0018": 57, "0024": 36, "0027": 16, "0028": 20, "0036": 15, "0037": 10, "0038": 12, "0041": 15, "0039": 30, "0026": 15, "0030": 30, "0035": 24, "0025": 98, "0032": 70, "0029": 60, "0031": 37, "0019": 77, "0033": 30, "0034": 63, "0047": 86, "0055": 47, "0014": 10, "0015": 20, "0013": 22, "0020": 16, "0021": 10, "0016": 12, "0022": 16, "0023": 16, "0554": 16, "0555": 18, "0556": 15, "0557": 16, "0558": 20, "0559": 20, "0560": 18, "0561": 20, "0562": 18, "0563": 42, "0564": 50, "0565": 32, "0040": 24, "0044": 17, "0042": 22}

LEDGERS = (
    "PROVIDER-EXACT-VECTORS-0025.jsonl",
    "MACHINE-READINESS-EXACT-ITEMS-0032.jsonl",
    "SEMANTIC-INVARIANTS-EXACT-ITEMS-0029.jsonl",
    "COGNITIVE-BOUNDARY-EXACT-ITEMS-0031.jsonl",
    "EPISTEMIC-TESTS-AND-FIREWALLS-EXACT-0019.jsonl",
    "THREAD-WORK-UX-CHOICES-EXACT-0033.jsonl",
    "COGNITION-FOUNDATION-EXACT-ITEMS-0034.jsonl",
    "BANK-MACRO-COMPARABILITY-EXACT-0019.jsonl",
    "TOPIC08-EXACT-QUALITIES-50-0047.jsonl",
    "QUALITY-08-NEGATIVE-36-ENGLISH-LOCATORS.jsonl",
    "BACKGROUND-WORK-0018-ENGLISH-57.jsonl",
    "SCENARIO-CASCADE-0024-ENGLISH-36.jsonl",
    "OBSERVABILITY-0030-ENGLISH-30.jsonl",
    "REGISTRY-SOURCE-0035-ENGLISH-24.jsonl",
    "ARTIFACT-0027-ENGLISH-16.jsonl",
    "FORMAT-0028-ENGLISH-20.jsonl",
    "SHARED-NODE-0036-ENGLISH-15.jsonl",
    "CORE-DESIGN-0037-ENGLISH-10.jsonl",
    "WEB-HOST-0038-ENGLISH-12.jsonl",
    "AUTOMATION-0041-ENGLISH-15.jsonl",
    "WINDOWS-UX-0039-ENGLISH-30.jsonl",
    "EXECUTION-CONTROL-0026-ENGLISH-15.jsonl",
    "WHOLE-SYSTEM-INV-TQ-ENGLISH-47-0055.jsonl",
    "HISTORICAL-01-DETAIL-ENGLISH-30.jsonl",
    "HISTORICAL-UX-0013-ENGLISH-22.jsonl",
    "WINDOWS-STATE-0020-ENGLISH-16.jsonl",
    "CORE-SURVEY-0021-ENGLISH-10.jsonl",
    "HISTORICAL-REFACTOR-0016-ENGLISH-12.jsonl",
    "MACHINE-SCHEME-0022-ENGLISH-16.jsonl",
    "PORTABILITY-0023-ENGLISH-16.jsonl",
    "LATE-ONTOLOGY-0554-ENGLISH-16.jsonl",
    "LATE-LIFECYCLE-0555-ENGLISH-18.jsonl",
    "LATE-STATE-0556-ENGLISH-15.jsonl",
    "LATE-ARTIFACT-0557-ENGLISH-16.jsonl",
    "LATE-SECURITY-0558-ENGLISH-20.jsonl",
    "LATE-MACHINE-0559-ENGLISH-20.jsonl",
    "LATE-CLIENTS-0560-ENGLISH-18.jsonl",
    "LATE-OBSERVABILITY-0561-ENGLISH-20.jsonl",
    "LATE-SOURCE-0562-ENGLISH-18.jsonl",
    "LATE-OWNERSHIP-0563-ENGLISH-20.jsonl",
    "LATE-OWNERSHIP-0563-TESTS-ENGLISH-22.jsonl",
    "LATE-ENDTOEND-0564-ENGLISH-20.jsonl",
    "LATE-ENDTOEND-0564-TESTS-ENGLISH-30.jsonl",
    "LATE-METHOD-0565-ENGLISH-20.jsonl",
    "LATE-METHOD-0565-TESTS-ENGLISH-12.jsonl",
    "MOTION-0040-ENGLISH-24.jsonl",
    "SETTINGS-0044-ENGLISH-17.jsonl",
    "STYLESET-0042-ENGLISH-22.jsonl",
)


def read_text(path: Path) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def original_sha(path: Path) -> str:
    proc = subprocess.run(
        ["git", "hash-object", "--", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def source_lines(source: Path) -> list[str]:
    return read_text(source).splitlines()


def normalized_for_markdown(text: str) -> str:
    return text.replace("|", r"\|").replace("<", "&lt;")


def verify() -> dict:
    with (ROOT / CENSUS).open(encoding="utf-8", newline="") as stream:
        catalog = {row["source_id"]: row for row in csv.DictReader(stream)}

    issues: list[str] = []
    source_cache: dict[str, list[str]] = {}
    target_cache: dict[str, str] = {}
    by_source: dict[str, int] = {}
    verified = 0
    seen_units: set[str] = set()

    for ledger in LEDGERS:
        ledger_path = BASE / "units" / ledger
        for index, raw in enumerate(read_text(ledger_path).splitlines(), start=1):
            if not raw.strip():
                continue
            item = json.loads(raw)
            label = item["unit_id"]
            if label in seen_units:
                issues.append(f"{label}: duplicate material unit ID")
            seen_units.add(label)
            source_id = item["source_id"]
            census = catalog.get(source_id)
            if census is None:
                issues.append(f"{label}: absent census source")
                continue

            path = Path(census["path"])
            if source_id not in source_cache:
                try:
                    sha = original_sha(path)
                    if sha != census["blob_sha"]:
                        issues.append(f"{source_id}: current source Git blob differs from frozen census")
                    source_cache[source_id] = source_lines(path)
                except (OSError, subprocess.CalledProcessError) as exc:
                    issues.append(f"{source_id}: unable to open/hash source: {exc}")
                    continue
            recorded_sha = item.get("source_sha") or item.get("source_blob_sha")
            if recorded_sha != census["blob_sha"]:
                issues.append(f"{label}: recorded source SHA mismatch")

            span = item.get("source_span") or f"L{item['source_line']}"
            match = re.fullmatch(r"L(\d+)(?:-L(\d+))?", span)
            if match is None:
                issues.append(f"{label}: invalid source span")
                continue
            first = int(match.group(1))
            last = int(match.group(2) or first)
            lines = source_cache[source_id]
            if not 1 <= first <= last <= len(lines):
                issues.append(f"{label}: source span out of bounds")
                continue

            target = item.get("science_destination") or item.get("preserved_exact_test_row")
            if not target:
                issues.append(f"{label}: no destination")
                continue
            if target not in target_cache:
                try:
                    target_cache[target] = read_text(Path(target))
                except OSError:
                    issues.append(f"{label}: destination missing: {target}")
                    continue
            rendered = target_cache[target]

            # Every bounded row must contain its durable original item handle.
            destination_id = item.get("science_id") or item.get("test_id")
            if destination_id is None:
                destination_id = item["unit_id"].replace("SB-MAT-", "SB-SRC-", 1)
                # Keep exact source groups as semantic handles, not arbitrary slugs.
                destination_id = destination_id.replace(f"{source_id}-", f"{source_id}/", 1)
            # Two orthogonal producer checks:
            # (a) the ledger still describes the original frozen source;
            # (b) the English Science destination retains ID, visible meaning
            #     and a direct line link. This CANNOT certify translation meaning.
            def source_english_row(identifier: str) -> str:
                return next(
                    (line for line in rendered.splitlines()
                     if line.startswith("|") and f"`{identifier}`" in line),
                    "",
                )

            source_here = lines[first - 1]
            if source_id == "SB-SRC-0025":
                # Generic provider vectors use original markdown rows verbatim.
                if source_here not in rendered:
                    issues.append(f"{label}: exact original provider vector missing")
            elif source_id == "SB-SRC-0019":
                if destination_id not in rendered:
                    issues.append(f"{label}: source item identity missing")
                test_body = item.get("full_source_test_body")
                if test_body:
                    if chr(10).join(lines[first:last]).strip() != test_body:
                        issues.append(f"{label}: ledger test body differs from original")
                    if f"#L{first}" not in rendered:
                        issues.append(f"{label}: exact original test line link missing")
                    if f"`{destination_id}`" not in rendered:
                        issues.append(f"{label}: English test identity missing")
                else:
                    original = item.get("original_exact_meaning")
                    if original:
                        observed = source_here.strip()
                        if item.get("material_kind") == "macro_series_qualifier":
                            observed = observed.removeprefix("- ").strip()
                        if observed != original:
                            issues.append(f"{label}: original study wording changed")
                    row = source_english_row(destination_id)
                    if not row or f"#L{first}" not in row:
                        issues.append(f"{label}: evidence boundary/series rendering missing")
                    if row and item.get("material_kind") not in (
                        "banking_boundary",
                    ):
                        if original and normalized_for_markdown(original) not in row:
                            issues.append(f"{label}: unchanged exact original term missing")
            elif source_id == "SB-SRC-0026":
                original_id = item["unit_id"].replace("SB-MAT-0026-", "")
                handle = f"SB-SRC-0026/{original_id}"
                row = source_english_row(handle)
                number = item.get("original_number")
                if not isinstance(number, int) or not source_here.startswith(f"{number}. ") or source_here != item.get("original_source_line"):
                    issues.append(f"{label}: original execution research numbered item changed")
                meaning = item.get("english_research_meaning")
                if not row or f"#L{first}" not in row or not meaning or meaning not in row:
                    issues.append(f"{label}: original execution-control English destination missing")
            elif source_id == "SB-SRC-0039":
                original_id = item["unit_id"].replace("SB-MAT-0039-", "")
                handle = f"SB-SRC-0039/{original_id}"
                row = source_english_row(handle)
                if source_here != item.get("original_bullet") or not source_here.startswith("- "):
                    issues.append(f"{label}: original desktop acceptance bullet changed")
                meaning = item.get("english_research_expectation")
                if not row or f"#L{first}" not in row or not meaning or meaning not in row:
                    issues.append(f"{label}: English desktop UX item/source line missing")
            elif source_id == "SB-SRC-0041":
                original_id = item["unit_id"].replace("SB-MAT-0041-", "")
                handle = f"SB-SRC-0041/{original_id}"
                row = source_english_row(handle)
                ordinal = int(original_id.split("-")[-1])
                if source_here != item.get("original_heading") or not source_here.startswith(f"## {ordinal}. "):
                    issues.append(f"{label}: original AI automation section heading changed")
                meaning = item.get("english_research_meaning")
                if not row or f"#L{first}" not in row or not meaning or meaning not in row:
                    issues.append(f"{label}: English AI research boundary or source line missing")
            elif source_id == "SB-SRC-0038":
                original_id = item["unit_id"].replace("SB-MAT-0038-", "")
                handle = f"SB-SRC-0038/{original_id}"
                row = source_english_row(handle)
                ordinal = int(original_id.split("-")[-1])
                if source_here != item.get("original_heading") or not source_here.startswith(f"## {ordinal}. "):
                    issues.append(f"{label}: original Web anti-pattern heading changed")
                meaning = item.get("english_research_antipattern")
                scoped = item.get("english_scoped_reason")
                if (not row or f"#L{first}" not in row or not meaning or meaning not in row or
                        not scoped or scoped not in row):
                    issues.append(f"{label}: English Web caution or source line missing")
            elif source_id == "SB-SRC-0037":
                original_id = item["unit_id"].replace("SB-MAT-0037-", "")
                handle = f"SB-SRC-0037/{original_id}"
                row = source_english_row(handle)
                heading = item.get("original_heading")
                if source_here != heading or not source_here.startswith("# "):
                    issues.append(f"{label}: original architecture section heading changed")
                meaning = item.get("english_source_research_claim")
                if not row or f"#L{first}" not in row or not meaning or meaning not in row:
                    issues.append(f"{label}: English architecture source row missing")
            elif source_id == "SB-SRC-0036":
                original_id = item["unit_id"].replace("SB-MAT-0036-", "")
                handle = f"SB-SRC-0036/{original_id}"
                row = source_english_row(handle)
                number = int(original_id.split("-")[-1])
                if not source_here.startswith(f"## {number}. ") or item.get("original_heading") != source_here:
                    issues.append(f"{label}: original shared-node criterion heading changed")
                meaning = item.get("english_candidate_expectation")
                if not row or f"#L{first}" not in row or not meaning or meaning not in row:
                    issues.append(f"{label}: English shared-node criterion/source line missing")
            elif source_id == "SB-SRC-0028":
                original_id = item["unit_id"].replace("SB-MAT-0028-", "")
                handle = f"SB-SRC-0028/{original_id}"
                row = source_english_row(handle)
                number = int(original_id.split("-")[-1])
                if not source_here.startswith(f"{number}. **"):
                    issues.append(f"{label}: original numbered format candidate changed")
                meaning = item.get("english_research_meaning")
                if not row or f"#L{first}" not in row or not meaning or meaning not in row:
                    issues.append(f"{label}: English format candidate source mapping missing")
            elif source_id == "SB-SRC-0027":
                original_id = item["unit_id"].replace("SB-MAT-0027-", "")
                handle = f"SB-SRC-0027/{original_id}"
                row = source_english_row(handle)
                number = int(original_id[1:])
                if not source_here.startswith(f"### D{number}. "):
                    issues.append(f"{label}: original Artifact decision heading changed")
                proposal = item.get("english_research_proposal")
                limitation = item.get("english_limitation")
                if (not row or f"#L{first}" not in row or
                        not proposal or proposal not in row or
                        not limitation or limitation not in row):
                    issues.append(f"{label}: source-pinned English Artifact decision missing")
            elif source_id == "SB-SRC-0035":
                original_id = item["unit_id"].replace("SB-MAT-0035-", "")
                handle = f"SB-SRC-0035/{original_id}"
                row = source_english_row(handle)
                if item.get("source_row_type") == "headed_research_antipattern":
                    ordinal = int(original_id.split("-")[-1])
                    if not source_here.startswith(f"## 48.{ordinal}. "):
                        issues.append(f"{label}: original antipattem heading changed")
                elif item.get("source_row_type") == "enumerated_research_recommendation":
                    ordinal = int(original_id.split("-")[-1])
                    if not source_here.startswith(f"{ordinal}. **"):
                        issues.append(f"{label}: original registry recommendation changed")
                else:
                    issues.append(f"{label}: unsupported registry original row type")
                meaning = item.get("english_research_meaning")
                if not row or f"#L{first}" not in row or not meaning or meaning not in row:
                    issues.append(f"{label}: English registry row or original link missing")
            elif source_id == "SB-SRC-0030":
                research_id = item["unit_id"].replace("SB-MAT-0030-", "")
                handle = f"SB-SRC-0030/{research_id}"
                row = source_english_row(handle)
                kind = item.get("original_research_row_type")
                statement = item.get("english_research_meaning")
                if kind == "source_fault_scenario":
                    if source_here.strip() != statement:
                        issues.append(f"{label}: original source fault scenario changed")
                elif kind == "research_target_thesis":
                    if not source_here.startswith(f"{int(research_id.split(chr(45))[-1])}. **"):
                        issues.append(f"{label}: original enumerated observability thesis changed")
                else:
                    issues.append(f"{label}: unknown observability source row kind")
                if not row or f"#L{first}" not in row or not statement or statement not in row:
                    issues.append(f"{label}: English observability item or source link missing")
            elif source_id == "SB-SRC-0024":
                original_id = item["unit_id"].replace("SB-MAT-0024-", "")
                handle = f"SB-SRC-0024/{original_id}"
                row = source_english_row(handle)
                shape = item.get("source_row_kind")
                if shape == "original_enumerated_term":
                    if item.get("original_stable_key") != source_here.strip():
                        issues.append(f"{label}: source term has changed")
                elif shape == "original_bullet":
                    if not source_here.startswith("- "):
                        issues.append(f"{label}: original anti-pattern bullet changed")
                elif shape == "two_column_original_decision":
                    if not source_here.startswith("| ") or source_here.count("|") < 3:
                        issues.append(f"{label}: original decision row invalid")
                else:
                    issues.append(f"{label}: unknown original source-row kind")
                meaning = item.get("english_research_meaning")
                if not row or f"#L{first}" not in row or not meaning or meaning not in row:
                    issues.append(f"{label}: English Source 0024 item/line/meaning missing")
            elif source_id == "SB-SRC-0018":
                original_id = item["original_research_id"]
                source_handle = f"{source_id}/{original_id}"
                row = source_english_row(source_handle)
                if item.get("source_structure") == "markdown_two_column_research_case":
                    if not source_here.startswith("| ") or source_here.count("|") < 3:
                        issues.append(f"{label}: malformed original background scenario")
                else:
                    if f"**{original_id}.**" not in source_here:
                        issues.append(f"{label}: named source acceptance check changed")
                statement = item.get("english_interpretation")
                expectation = item.get("english_expected")
                if (not row or f"#L{first}" not in row or
                        not statement or statement not in row or
                        (expectation and expectation not in row)):
                    issues.append(f"{label}: English Work source interpretation missing")
            elif source_id == "SB-SRC-0047":
                original_id = item.get("research_id") or item.get("research_test_id")
                row = source_english_row(original_id)
                if item.get("research_test_id"):
                    if not source_here.startswith(f"| {original_id} |"):
                        issues.append(f"{label}: original source fixture ID/line changed")
                    scenario = item.get("english_scenario")
                    expected = item.get("english_expected_property")
                    if not row or not scenario or scenario not in row or not expected or expected not in row:
                        issues.append(f"{label}: negative fixture English rendering missing")
                else:
                    invariant = item["source_exact_invariant"]
                    falsifier = item["source_exact_falsifier"]
                    if source_here != f"| **{original_id}** | {invariant} | {falsifier} |":
                        issues.append(f"{label}: quality source row differs from frozen original")
                if not row or f"#L{first}" not in row:
                    issues.append(f"{label}: translated quality row or original line missing")
            elif source_id == "SB-SRC-0042":
                style_id = item.get("source_item_id")
                handle = f"SB-SRC-0042/{style_id}"
                row = source_english_row(handle)
                meaning = item.get("english_meaning")
                if (not row or f"#L{first}" not in row
                    or not meaning or meaning not in row):
                    issues.append(f"{label}: StyleSet English proposal/source row missing")
                expected_number = int(style_id.removeprefix("A")) if style_id else -1
                if not source_here.startswith(f"{expected_number}. "):
                    issues.append(f"{label}: original StyleSet numbered acceptance row changed")
            elif source_id == "SB-SRC-0044":
                item_id = item.get("source_item_id")
                handle = f"SB-SRC-0044/{item_id}"
                row = source_english_row(handle)
                meaning = item.get("english_meaning")
                if (not row or f"#L{first}" not in row
                    or not meaning or meaning not in row):
                    issues.append(f"{label}: English Settings classification/source line missing")
                if item_id and item_id.startswith("CRITERION-"):
                    if not re.match(r"\d+\. ", source_here):
                        issues.append(f"{label}: original Settings eligibility item changed")
                elif item_id and item_id.startswith("OWNER-"):
                    if not source_here.startswith("## 4."):
                        issues.append(f"{label}: original Settings owner heading changed")
                elif item_id and item_id.startswith("PAGE-"):
                    if not source_here.strip():
                        issues.append(f"{label}: original Settings page candidate missing")
                else:
                    issues.append(f"{label}: unknown Settings item family")
            elif source_id == "SB-SRC-0040":
                motion_id = item.get("source_item_id")
                handle = f"SB-SRC-0040/{motion_id}"
                row = source_english_row(handle)
                meaning = item.get("english_meaning")
                if not row or f"#L{first}" not in row or not meaning or meaning not in row:
                    issues.append(f"{label}: motion English item/source-line missing")
                if motion_id and motion_id.startswith("DURATION-"):
                    original_token = source_here.split("|")[1].strip()
                    if not original_token.startswith("`motion."):
                        issues.append(f"{label}: source duration token row changed")
                elif motion_id and motion_id.startswith("STATE-"):
                    if not source_here.startswith("| ") or not source_here.split("|")[1].strip():
                        issues.append(f"{label}: source motion-state row changed")
                else:
                    issues.append(f"{label}: unknown source motion item family")
            elif source_id == "SB-SRC-0565":
                test_id = item.get("research_test_id")
                if test_id:
                    handle = f"SB-SRC-0565/{test_id}"
                    row = source_english_row(handle)
                    if not source_here.startswith(f"| {test_id}. "):
                        issues.append(f"{label}: original method-alignment test row changed")
                    scenario = item.get("english_scenario")
                    expected = item.get("english_expected_property")
                    if (not row or f"#L{first}" not in row
                        or not scenario or scenario not in row
                        or not expected or expected not in row):
                        issues.append(f"{label}: method Topic 11 source/English test missing")
                else:
                    handle = item.get("science_id")
                    row = source_english_row(handle)
                    meaning = item.get("english_research_meaning")
                    if (not row or f"#L{first}" not in row or not meaning
                        or meaning not in row):
                        issues.append(f"{label}: method Topic 11 semantic item missing")
                    if not source_here.strip():
                        issues.append(f"{label}: empty original method research line")
            elif source_id == "SB-SRC-0564":
                test_id = item.get("research_test_id")
                if test_id:
                    handle = f"SB-SRC-0564/{test_id}"
                    row = source_english_row(handle)
                    if not source_here.startswith(f"| {test_id} |"):
                        issues.append(f"{label}: original end-to-end test row changed")
                    scenario = item.get("english_scenario")
                    expected = item.get("english_expected_property")
                    if (not row or f"#L{first}" not in row
                        or not scenario or scenario not in row
                        or not expected or expected not in row):
                        issues.append(f"{label}: Topic 12 English test row/destination missing")
                else:
                    handle = item.get("science_id")
                    row = source_english_row(handle)
                    meaning = item.get("english_research_meaning")
                    if (not row or f"#L{first}" not in row or not meaning
                        or meaning not in row):
                        issues.append(f"{label}: Topic 12 mapped meaning missing")
                    if not source_here.strip():
                        issues.append(f"{label}: empty original Topic 12 source span")
            elif source_id == "SB-SRC-0563":
                test_id = item.get("research_test_id")
                if test_id:
                    handle = f"SB-SRC-0563/{test_id}"
                    row = source_english_row(handle)
                    if not source_here.startswith(f"| {test_id} |"):
                        issues.append(f"{label}: original Topic 10 test row differs")
                    scenario = item.get("english_scenario")
                    outcome = item.get("english_expected_property")
                    if (not row or f"#L{first}" not in row
                        or not scenario or scenario not in row
                        or not outcome or outcome not in row):
                        issues.append(f"{label}: English Topic 10 integration test is missing")
                else:
                    handle = item.get("science_id")
                    row = source_english_row(handle)
                    meaning = item.get("english_research_meaning")
                    if (not row or f"#L{first}" not in row or not meaning
                        or meaning not in row):
                        issues.append(f"{label}: Topic 10 source-owner statement missing")
                    if not source_here.strip():
                        issues.append(f"{label}: empty original Topic 10 source line")
            elif source_id == "SB-SRC-0562":
                # The original Topic 09 source contains proposed T01..T18
                # fault fixtures as Russian three-column Markdown rows.
                test_id = item.get("research_test_id")
                expected_id = f"SB-SRC-0562/{test_id}"
                row = source_english_row(expected_id)
                if not test_id or not source_here.startswith(f"| {test_id}: "):
                    issues.append(f"{label}: original Topic 09 source fault row changed")
                scenario = item.get("english_scenario")
                expected_property = item.get("english_expected_property")
                if (not row or f"#L{first}" not in row
                    or not scenario or scenario not in row
                    or not expected_property or expected_property not in row):
                    issues.append(f"{label}: Topic 09 English provenance fault fixture missing")
            elif source_id == "SB-SRC-0055":
                original_id = item["original_test_id"]
                if not source_here.startswith(f"| {original_id} |"):
                    issues.append(f"{label}: original Topic-09 test/invariant row changed")
                row = source_english_row(original_id)
                if not row or f"#L{first}" not in row:
                    issues.append(f"{label}: Topic-09 English destination/line missing")
                meaning = item.get("english_research_meaning")
                fixture = item.get("english_negative_fixture")
                if row and (not meaning or meaning not in row or not fixture or fixture not in row):
                    issues.append(f"{label}: Topic-09 English text changed")
            elif (source_id in ("SB-SRC-0013", "SB-SRC-0014", "SB-SRC-0015", "SB-SRC-0016", "SB-SRC-0020", "SB-SRC-0021", "SB-SRC-0022", "SB-SRC-0023", "SB-SRC-0554", "SB-SRC-0555", "SB-SRC-0556", "SB-SRC-0557", "SB-SRC-0558", "SB-SRC-0559", "SB-SRC-0560", "SB-SRC-0561")
                  and item.get("epistemic_status") in (
                      "DATED_HISTORICAL_RESEARCH_OR_CHANGE_NOTE",
                      "HISTORICAL_UX_PROPOSAL_NOT_CURRENT_IMPLEMENTATION",
                      "PINNED_WINDOWS_SOURCE_SURVEY_NOT_INSTALLED_RUNTIME_CERTIFICATION",
                      "DATED_SECONDARY_CORE_IMPLEMENTATION_STUDY",
                      "DATED_ARCHITECTURE_REFRACTOR_PROPOSAL",
                      "RESEARCH_MACHINE_SCHEME_PROPOSAL_OWNER_OPEN",
                      "PUBLIC_GENERIC_PORTABILITY_RESEARCH_PROPOSAL",
                      "LATE_RESEARCH_ONTOLOGY_ALTERNATIVE_NOT_PRODUCT_APPROVED",
                      "LATE_RESEARCH_LIFECYCLE_PROPOSAL_NOT_PRODUCTION_ASSURANCE",
                      "LATE_RESEARCH_STATE_DURABILITY_PROPOSAL_NOT_ACCEPTED",
                      "LATE_RESEARCH_ARTIFACT_ASSURANCE_NOT_IMPLEMENTED",
                      "RESEARCH_THREAT_MODEL_CANDIDATE_NOT_SECURITY_CERTIFICATION",
                      "LATE_MACHINE_CAPABILITY_RESEARCH_NOT_IMPLEMENTED_PROTOCOL",
                      "LATE_CROSS_PLATFORM_RESEARCH_NOT_ACCEPTED_DELIVERY",
                      "LATE_OBSERVABILITY_RESEARCH_NOT_INSTALLED_DIAGNOSTICS",
                  )):
                row = source_english_row(destination_id)
                meaning = item.get("english_research_meaning")
                if not source_here.strip() or source_here.lstrip().startswith("<mark>"):
                    issues.append(f"{label}: invalid private/empty historical original line")
                if (not row or not meaning or meaning not in row or
                    f"#L{first}" not in row):
                    issues.append(f"{label}: historical English claim or original-line link missing")
                if not item.get("disposition"):
                    issues.append(f"{label}: missing historical/currentness disposition")
            elif source_id == "SB-SRC-0033":
                if f"`{destination_id}`" not in rendered:
                    issues.append(f"{label}: Chat/Work item identity missing")
                if item.get("original_heading"):
                    heading = item["original_heading"]
                    reason = item["original_explanation"]
                    if heading not in source_here or reason not in lines[first + 1]:
                        issues.append(f"{label}: original research anti-pattern changed")
                else:
                    question = item["original_question"]
                    recommendation = item["original_recommendation"]
                    if question not in source_here or recommendation not in source_here:
                        issues.append(f"{label}: original research UX choice changed")
                row = source_english_row(destination_id)
                if not row or f"#L{first}" not in row:
                    issues.append(f"{label}: English Chat/Work choice or source link missing")
            else:
                if f"`{destination_id}`" not in rendered:
                    issues.append(f"{label}: material source identity missing")
                original = (
                    item.get("material_meaning")
                    or item.get("source_exact_meaning")
                    or item.get("meaning")
                    or item.get("original_exact_meaning")
                )
                if not original:
                    issues.append(f"{label}: original wording absent from ledger")
                if source_id in ("SB-SRC-0032", "SB-SRC-0029", "SB-SRC-0034"):
                    if original and original not in source_here:
                        issues.append(f"{label}: material wording differs from original")
                if source_id == "SB-SRC-0031":
                    group = item.get("source_group")
                    if group in ("BOUNDARY_CHECK", "BOUNDARY_ALARM"):
                        if original not in source_here:
                            issues.append(f"{label}: source list item differs from original")
                    elif group == "HOST_INVARIANT":
                        title, delimiter, statement = original.partition(" — ")
                        neighborhood = chr(10).join(lines[first - 1:first + 3])
                        if not delimiter or title not in neighborhood or statement not in neighborhood:
                            issues.append(f"{label}: source heading/body differs from original")
                    else:
                        issues.append(f"{label}: unknown group {group!r}")
                row = source_english_row(destination_id)
                if not row or f"#L{first}" not in row:
                    issues.append(f"{label}: maintained source item/line missing")
                # Only the original English source rows of these groups remain
                # verbatim; original Russian research rows were translated.
                if (source_id == "SB-SRC-0029"
                    or source_id == "SB-SRC-0032"
                    and item.get("material_kind") != "research_acceptance_question"):
                    if original and row and normalized_for_markdown(original) not in row:
                        issues.append(f"{label}: original English source wording missing")

            # Every article row must be in English, except source content
            # which is retained verbatim only in the original frozen input.
            if source_id != "SB-SRC-0025":
                row_key = item.get("original_test_id") or item.get("research_id") or destination_id
                row = source_english_row(row_key)
                # Source links necessarily contain original Russian filenames
                # in their URL path. That is citation metadata, not visible
                # translated article text. Keep source original filenames
                # unchanged for faithful traceability, but inspect only the
                # reader-visible rendering of the English destination row.
                visible_row = re.sub(
                    r"\]\((?:https?|mailto):[^)]*\)",
                    "](SOURCE_LINK)",
                    row,
                )
                if visible_row and re.search(r"[А-Яа-яЁё]", visible_row):
                    issues.append(f"{label}: non-English visible maintained rendering")
            verified += 1
            by_source[source_id] = by_source.get(source_id, 0) + 1

    for sid, expected in EXPECTED_ITEMS.items():
        actual = by_source.get(f"SB-SRC-{sid}", 0)
        if actual != expected:
            issues.append(f"SB-SRC-{sid}: expected {expected} exact units, found {actual}")

    science_files = 0
    science_links = 0
    docs_files = 0
    docs_links = 0
    for doc in sorted((ROOT / "docs").rglob("*.md")):
        doc_rel = doc.relative_to(ROOT)
        is_science = doc_rel.parts[:2] == ("docs", "science")
        docs_files += 1
        if is_science:
            science_files += 1
        for candidate in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
            if candidate.startswith(("#", "https:", "http:", "mailto:", "data:")):
                continue
            route = unquote(candidate.split("#", 1)[0])
            if not route:
                continue
            docs_links += 1
            if is_science:
                science_links += 1
            target = (doc.parent / route).resolve()
            try:
                target.relative_to(ROOT.resolve())
            except ValueError:
                issues.append(f"{doc_rel}: link escapes repository: {candidate}")
                continue
            if not target.exists():
                issues.append(f"{doc_rel}: broken relative link: {candidate}")

    return {
        "status": "PRODUCER_TRACE_CHECK_PASS" if not issues else "PRODUCER_TRACE_CHECK_FAIL",
        "scope": "twenty-three mixed exact/English-translation ledgers, twenty-one original studies; original SHA/line and destination ID/link checks only, NOT semantic equivalence proof",
        "item_count_checked": verified,
        "by_source": dict(sorted(by_source.items())),
        "science_markdown_files": science_files,
        "science_local_links_checked": science_links,
        "maintained_docs_markdown_files": docs_files,
        "maintained_docs_local_links_checked": docs_links,
        "issues": issues,
    }

if __name__ == "__main__":
    try:
        result = verify()
    except Exception as exc:
        result = {"status": "CHECKER_ERROR", "message": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == "PRODUCER_TRACE_CHECK_PASS" else 1)
