#!/usr/bin/env python3
"""Inventory Research coverage by unit kind; never certify semantic losslessness.

Read-only, stdlib-only. Execute from any working-directory within a Git
checkout. Prints factual coverage categories, unresolved gaps and source
identity errors. Heading/section locators, producer interpretations and exact
text-transferred source items are three DIFFERENT evidence classes.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "_mw/epochs-001-strategy-box-development/consolidation"
ROLES = {"historical_research", "base_research", "consolidation_research", "ai_raised_research"}
ORIENTATIONS = {"SB-SRC-0012", "SB-SRC-0017", "SB-SRC-0045"}
SPAN = re.compile(r"^L(\d+)(?:-L?(\d+))?$")


def sha_of(path: Path) -> str:
    return subprocess.run(
        ["git", "hash-object", "--", str(path)],
        cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> dict:
    with (BASE / "sources/CENSUS.csv").open(newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))
    registered = {r["source_id"]: r for r in all_rows}
    originals = {
        r["source_id"]: r
        for r in all_rows
        if r["role"] in ROLES and r["source_id"] not in ORIENTATIONS
    }
    issues = []
    by_source = defaultdict(lambda: Counter())
    by_role = Counter()
    unit_ids = set()
    ledger_rows = Counter()
    kinds = Counter()
    destinations = defaultdict(set)
    candidate_routes = defaultdict(set)

    for path in sorted((BASE / "units").glob("*.jsonl")):
        text = path.read_text(encoding="utf-8")
        for n, raw in enumerate(text.splitlines(), 1):
            if not raw.strip():
                continue
            try:
                v = json.loads(raw)
            except json.JSONDecodeError as e:
                issues.append(f"{path.name}:{n} malformed JSONL: {e}")
                continue
            ledger_rows[path.name] += 1
            sid = v.get("source_id")
            if sid not in registered:
                issues.append(f"{path.name}:{n} unknown census source {sid}")
                continue
            sha = v.get("source_blob_sha") or v.get("source_sha")
            if sha and sha != registered[sid]["blob_sha"]:
                issues.append(f"{path.name}:{n} original frozen blob SHA mismatch")
            locator_only = v.get("status") == "section_locator_only_semantic_equivalence_unverified"
            # Source-exact quotation and English translation are distinct
            # evidence classes. Both are line-addressed producer mappings,
            # neither is independent proof of semantic equivalence.
            routing_only = path.name.startswith("RESEARCH-ORIGINAL-CANDIDATE-ROUTING-")
            english_row = path.name.startswith((
                "WHOLE-SYSTEM-INV-TQ-ENGLISH-",
                "QUALITY-08-NEGATIVE-",
                "BACKGROUND-WORK-0018-ENGLISH-",
                "SCENARIO-CASCADE-0024-ENGLISH-",
                "OBSERVABILITY-0030-ENGLISH-",
                "REGISTRY-SOURCE-0035-ENGLISH-",
                "ARTIFACT-0027-ENGLISH-",
                "FORMAT-0028-ENGLISH-",
                "SHARED-NODE-0036-ENGLISH-",
                "CORE-DESIGN-0037-ENGLISH-",
                "WEB-HOST-0038-ENGLISH-",
                "AUTOMATION-0041-ENGLISH-",
                "WINDOWS-UX-0039-ENGLISH-",
                "EXECUTION-CONTROL-0026-ENGLISH-",
                "HISTORICAL-01-DETAIL-ENGLISH-",
                "HISTORICAL-UX-0013-ENGLISH-",
                "WINDOWS-STATE-0020-ENGLISH-",
                "CORE-SURVEY-0021-ENGLISH-",
                "HISTORICAL-REFACTOR-0016-ENGLISH-",
                "MACHINE-SCHEME-0022-ENGLISH-",
                "PORTABILITY-0023-ENGLISH-",
                "LATE-ONTOLOGY-0554-ENGLISH-",
                "LATE-LIFECYCLE-0555-ENGLISH-",
                "LATE-STATE-0556-ENGLISH-",
                "LATE-ARTIFACT-0557-ENGLISH-",
                "LATE-SOURCE-0562-ENGLISH-",
                "LATE-OWNERSHIP-0563-ENGLISH-",
                "LATE-OWNERSHIP-0563-TESTS-ENGLISH-",
                "LATE-ENDTOEND-0564-ENGLISH-",
                "LATE-ENDTOEND-0564-TESTS-ENGLISH-",
                "LATE-METHOD-0565-ENGLISH-",
                "LATE-METHOD-0565-TESTS-ENGLISH-",
            ))
            exact_text = path.name.startswith((
                "BANK-MACRO-COMPARABILITY-EXACT-",
                "COGNITION-FOUNDATION-EXACT-",
                "COGNITIVE-BOUNDARY-EXACT-",
                "EPISTEMIC-TESTS-AND-FIREWALLS-EXACT-",
                "MACHINE-READINESS-EXACT-",
                "PROVIDER-EXACT-",
                "SEMANTIC-INVARIANTS-EXACT-",
                "THREAD-WORK-UX-CHOICES-EXACT-",
                "TOPIC08-EXACT-",
            ))
            direct_code = "read_status" in v
            kind = ("section_locator_only" if locator_only else
                    "source_routing_only" if routing_only else
                    "source_row_traced_english" if english_row else
                    "exact_text_transcription" if exact_text else
                    "code_test_direct_read" if direct_code else
                    "producer_provisional_semantic")
            kinds[kind] += 1
            by_source[sid][kind] += 1
            if sid not in originals:
                continue
            if kind == "source_routing_only":
                route = v.get("route_candidate") or ""
                if route:
                    candidate_routes[sid].add(route)
                for alt in v.get("related_destination_candidates") or ():
                    candidate_routes[sid].add(alt)
                dest = ""
            elif kind == "producer_provisional_semantic":
                dest = (v.get("science_destination") or "").split(" §")[0]
            elif kind in ("exact_text_transcription", "source_row_traced_english"):
                dest = v.get("science_destination") or v.get("preserved_exact_test_row") or ""
            else:
                dest = v.get("route_candidate") or ""
            if dest:
                destinations[sid].add(dest)
            span = v.get("source_span", "")
            if span and not SPAN.fullmatch(span):
                issues.append(f"{path.name}:{n} unsupported locator {span!r}")
            unique = v.get("unit_id") or v.get("locator_id")
            if unique:
                if unique in unit_ids:
                    issues.append(f"duplicate unit or section locator ID {unique}")
                unit_ids.add(unique)

    no_semantic = []
    no_exact = []
    no_source_row_trace = []
    no_destination = []
    no_route = []
    pinned_bad = []
    read_by_role = Counter()
    for sid, row in originals.items():
        by_role[row["role"]] += 1
        read_by_role[row["read_state"]] += 1
        src = ROOT / row["path"]
        if not src.is_file():
            pinned_bad.append([sid, "SOURCE_NOT_IN_CHECKOUT", row["path"]])
        else:
            blob = sha_of(src)
            if blob != row["blob_sha"]:
                pinned_bad.append([sid, "SOURCE_CHANGED_FROM_FROZEN_CENSUS", row["path"]])
        values = by_source[sid]
        if (values["producer_provisional_semantic"] == 0 and
                values["exact_text_transcription"] == 0 and
                values["source_row_traced_english"] == 0):
            no_semantic.append(sid)
        if values["exact_text_transcription"] == 0:
            no_exact.append(sid)
        if values["exact_text_transcription"] == 0 and values["source_row_traced_english"] == 0:
            no_source_row_trace.append(sid)
        if not destinations[sid]:
            no_destination.append(sid)
        if not destinations[sid] and not candidate_routes[sid]:
            no_route.append(sid)
    return {
        "status": "INVENTORY_INTEGRITY_PASS_NOT_SEMANTIC_ASSURANCE"
                  if not issues and not pinned_bad else "INVENTORY_NEEDS_REVIEW",
        "purpose": "provenance and coverage gaps, not full lossless certification",
        "total_git_census": len(all_rows),
        "substantive_research_originals": len(originals),
        "originals_by_role": dict(sorted(by_role.items())),
        "originals_read_state": dict(sorted(read_by_role.items())),
        "orientations_excluded_from_substantive_count": sorted(ORIENTATIONS),
        "all_units_by_evidence_class": dict(sorted(kinds.items())),
        "units_by_class_not_additive_to_source_coverage": True,
        "number_of_ledgers": len(ledger_rows),
        "research_originals_without_semantic_provisional_or_exact": sorted(no_semantic),
        "research_originals_without_exact_transcriptions": sorted(no_exact),
        "research_originals_without_either_exact_or_english_source_row_trace": sorted(no_source_row_trace),
        "research_originals_without_destination": sorted(no_destination),
        "research_originals_without_even_a_candidate_route": sorted(no_route),
        "candidate_routes_are_not_material_destination_proofs": True,
        "unaccounted_git_source_records": sum(
            r["material_unit_state"] == "unaccounted" for r in all_rows
        ),
        "originals_without_independent_material_certification": len(originals),
        "source_byte_identity_issues": pinned_bad[:30],
        "inventory_issues_count": len(issues),
        "inventory_issues_sample": issues[:50],
        "source_detail": [
            {
                "source_id": sid,
                "role": original["role"],
                "read_state": original["read_state"],
                "provisional_semantic": by_source[sid]["producer_provisional_semantic"],
                "exact_text": by_source[sid]["exact_text_transcription"],
                "english_source_row": by_source[sid]["source_row_traced_english"],
                "section_only": by_source[sid]["section_locator_only"],
                "destination_count": len(destinations[sid]),
                "candidate_route_count": len(candidate_routes[sid]),
            }
            for sid, original in sorted(originals.items())
        ],
    }


if __name__ == "__main__":
    try:
        report = main()
    except Exception as exc:
        report = {"status": "AUDIT_TOOL_ERROR", "error": str(exc)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report["status"] == "INVENTORY_INTEGRITY_PASS_NOT_SEMANTIC_ASSURANCE" else 1)
