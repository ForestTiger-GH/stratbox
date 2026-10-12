#!/usr/bin/env python3
"""Build a source-hidden, answer-free 22-case reviewer kit.

This is a *distribution* tool, not an examiner. It runs after the exact-commit
Knowledge ZIP, carries only the question columns, and never reads prepared
producer answers or protected/Work ledgers outside the two question sources.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "_mw/epochs-001-strategy-box-development/consolidation/coverage"
DIST = ROOT / "dist"
KNOWLEDGE = DIST / "strategy-box-knowledge-standalone.zip"
OUT = DIST / "strategy-box-independent-reader-questions.zip"
SHA = DIST / "strategy-box-independent-reader-questions.sha256"
FROZEN = (1980, 1, 1, 0, 0, 0)
ALLOWED_OUT = ("INSTRUCTIONS.md", "QUESTIONNAIRE.md", "RESPONSE-TEMPLATE.json",
               "REVIEWER-PACKET-MANIFEST.json")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rows_from_markdown(filename: str, prefix: str) -> list[tuple[str, str]]:
    text = (BASE / filename).read_text(encoding="utf-8")
    result: list[tuple[str, str]] = []
    for raw in text.splitlines():
        if not re.match(r"^\|\s*" + re.escape(prefix) + r"-\d{2}\b", raw):
            continue
        parts = [x.strip() for x in raw.strip().strip("|").split("|")]
        assert len(parts) >= 2, (filename, raw)
        match = re.match(r"^(" + re.escape(prefix) + r"-\d{2})(?:\s*/.*)?$", parts[0])
        assert match, (filename, parts[0])
        assert parts[1] and "\n" not in parts[1], (filename, match.group(1))
        result.append((match.group(1), parts[1]))
    return result


def entry(name: str, data: bytes) -> tuple[zipfile.ZipInfo, bytes]:
    info = zipfile.ZipInfo(name, FROZEN)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info, data


def main() -> dict:
    assert KNOWLEDGE.is_file(), "build the standalone Knowledge ZIP first"
    # These source Work documents are intentionally not copied into the kit.
    first = rows_from_markdown(
        "INDEPENDENT-PUBLICATION-ONLY-REVIEW-QUESTIONS-2026-10-12.md", "IR")
    second = rows_from_markdown(
        "SECOND-HOLDOUT-RESEARCH-AMPUTATION-CHALLENGE-2026-10-12.md", "H")
    assert [x[0] for x in first] == [f"IR-{i:02d}" for i in range(1, 15)]
    assert [x[0] for x in second] == [f"H-{i:02d}" for i in range(1, 9)]
    cases = first + second
    assert len(cases) == 22 and len(set(k for k, _ in cases)) == 22
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, cwd=ROOT).strip()
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    evidence_zip_hash = sha256(KNOWLEDGE.read_bytes())
    knowledge_hash_file = (DIST / "strategy-box-knowledge-standalone.sha256").read_text(
        encoding="utf-8").split()[0]
    assert evidence_zip_hash == knowledge_hash_file

    intro = (
        "# Strategy Box — 22 independent reader questions\n\n"
        f"**Knowledge baseline:** \`ForestTiger-GH/stratbox@{commit}\`. "
        f"**Knowledge-only ZIP SHA-256:** \`{evidence_zip_hash}\`.\n\n"
        "Read only the separately supplied, SHA-verified Knowledge ZIP. "
        "Do not inspect original Research, Work ledgers, previous producer answers, "
        "Git history or unpublished source code before freezing your responses. "
        "All questions concern bounded claims; a justified UNKNOWN can be correct.\n\n"
        "| ID | Question |\n| --- | --- |\n"
    )
    questions = intro + "".join(f"| {k} | {q} |\n" for k, q in cases)
    instructions = (
        "# Independent reviewer instructions — no source answers supplied\n\n"
        "1. Verify the exact Knowledge-only ZIP SHA-256 in QUESTIONNAIRE.md. "
        "It must contain only docs/ plus KNOWLEDGE-HASHES.json.\n"
        "2. Use only the published docs/ files in the first phase. For every case, "
        "record a bounded answer, exact docs/ file and section, current-vs-proposed "
        "scope, one counterexample, and all unproved/dependent decisions.\n"
        "3. Choose one of ANSWERABLE_FROM_KNOWLEDGE, PARTIAL_WITH_OWNED_UNKNOWN, "
        "RAW_RESEARCH_REQUIRED, CONTRADICTED, INAPPROPRIATE_CONSUMER. Do not "
        "conflate a plausible answer with a tested deployed host.\n"
        "4. Freeze and attribute the completed answers (reviewer ID, UTC time, "
        "the exact Knowledge ZIP hash, review environment and any independence "
        "limitations) **before** any original-Research access.\n"
        "5. A separate competent original-first assessor then compares admissible "
        "frozen source material to the published Science including discarded "
        "hypotheses, caveats, late contradictions and negative cases. Source-level "
        "material accounting is a separate exhaustive gate beyond these 22 samples.\n"
        "6. Mark missing source material, protected-data limits and pending Product "
        "Decisions as open; never self-award global LOSSLESS_PASS or LCD readiness.\n\n"
        "**Independence requirement:** the Knowledge producer cannot be the "
        "independent assessor merely by resetting its context or using this form. "
        "The reviewer kit has no answer key or hidden scoring column.\n"
    )
    template = {
        "packet_kind": "INDEPENDENT_READER_BLIND_QUESTIONNAIRE",
        "status": "UNEXECUTED_TEMPLATE",
        "git_commit": commit,
        "knowledge_zip_sha256": evidence_zip_hash,
        "reviewer_id": None,
        "reviewed_at_utc": None,
        "independence_declaration": None,
        "answers_frozen_before_research": False,
        "cases": [{
            "case_id": k,
            "classification": None,
            "answer": None,
            "docs_file_and_section": [],
            "current_vs_candidate_vs_owner_decision": None,
            "counterexample_or_falsifier": None,
            "unknowns_and_boundaries": None,
        } for k, _ in cases],
    }
    payloads = {
        "INSTRUCTIONS.md": instructions.encode("utf-8"),
        "QUESTIONNAIRE.md": questions.encode("utf-8"),
        "RESPONSE-TEMPLATE.json": (json.dumps(
            template, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"),
    }
    manifest = {
        "packet": "QUESTION_ONLY_INDEPENDENT_REVIEW_HANDOFF",
        "git_commit": commit,
        "knowledge_zip_sha256": evidence_zip_hash,
        "question_count": len(cases),
        "case_ids": [k for k, _ in cases],
        "included_sha256": {k: sha256(v) for k, v in sorted(payloads.items())},
        "status": "REVIEWER_UNEXECUTED",
        "producer_answers_included": False,
        "historical_research_work_source_included": False,
        "semantic_assurance": "NOT_ATTESTED",
    }
    payloads["REVIEWER-PACKET-MANIFEST.json"] = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    assert tuple(sorted(payloads)) == tuple(sorted(ALLOWED_OUT))
    assert all("coverage/" not in v.decode("utf-8")
               for v in payloads.values()), "raw Work path in reader kit"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w") as archive:
        for name, data in sorted(payloads.items()):
            info, body = entry(name, data)
            archive.writestr(info, body, compresslevel=9)
    with zipfile.ZipFile(OUT) as archive:
        assert set(archive.namelist()) == set(ALLOWED_OUT)
        for name, body in payloads.items():
            assert archive.read(name) == body
    digest = sha256(OUT.read_bytes())
    SHA.write_text(digest + "  " + OUT.name + "\n", encoding="utf-8")
    return {
        "status": "22_BLIND_QUESTIONS_PREPARED_NOT_REVIEWED",
        "packet_sha256": digest,
        "knowledge_sha256": evidence_zip_hash,
        "questions": len(cases),
        "target": commit,
        "independent_review": "NOT_EXECUTED",
    }


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False))
