#!/usr/bin/env python3
"""Prepare a source-first independent *request* for 53 substantive originals.

This tool is a packet producer, NEVER a semantic assessor or independent witness.
Inputs: census identities and the separately built exact-SHA Knowledge ZIP only.
The packet contains no original content, source filename, private reference,
prepared answer, reviewer verdict, or auto-awarded material preservation.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "_mw/epochs-001-strategy-box-development/consolidation"
CENSUS = BASE / "sources/CENSUS.csv"
DIST = ROOT / "dist"
KNOWLEDGE = DIST / "strategy-box-knowledge-standalone.zip"
OUT = DIST / "strategy-box-source-first-reviewer-roster.zip"
SHA = DIST / "strategy-box-source-first-reviewer-roster.sha256"
RESEARCH_ROLES = frozenset({
    "historical_research", "base_research", "consolidation_research",
    "ai_raised_research"
})
NON_SUBSTANTIVE_ORIENTATIONS = frozenset({
    "SB-SRC-0012", "SB-SRC-0017", "SB-SRC-0045"
})
TIMESTAMP = (1980, 1, 1, 0, 0, 0)
PAYLOAD_NAMES = frozenset({
    "SOURCE-FIRST-INSTRUCTIONS.md",
    "SUBSTANTIVE-ORIGINAL-ROSTER.json",
    "SOURCE-FIRST-RESPONSE-TEMPLATE.json",
    "SOURCE-FIRST-PACKET-MANIFEST.json",
})


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def encode_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2)
            + "\n").encode("utf-8")


def build() -> dict:
    with CENSUS.open(encoding="utf-8", newline="") as stream:
        corpus = list(csv.DictReader(stream))
    assert len(corpus) == 566, len(corpus)
    assert len({r["source_id"] for r in corpus}) == 566
    assert all(r["material_unit_state"] == "unaccounted" for r in corpus)
    research = sorted(
        (r for r in corpus if r["role"] in RESEARCH_ROLES
         and r["source_id"] not in NON_SUBSTANTIVE_ORIENTATIONS),
        key=lambda item: item["source_id"]
    )
    assert len(research) == 53 and all(r["read_state"] == "full_read" for r in research)
    assert all(r["repository"] == "ForestTiger-GH/stratbox" for r in research)
    assert KNOWLEDGE.exists(), "Run deterministic Knowledge packaging first"
    knowledge_hash = digest(KNOWLEDGE.read_bytes())
    assert knowledge_hash == (DIST / "strategy-box-knowledge-standalone.sha256").read_text(
        encoding="utf-8").split()[0]
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    assert len(commit) == 40 and all(c in "0123456789abcdef" for c in commit)
    roster = {
        "packet_kind": "SOURCE_FIRST_ORIGINAL_MATERIAL_REVIEW_ROSTER",
        "status": "UNEXECUTED_PRODUCER_PREPARATION",
        "publication_commit": commit,
        "knowledge_sha256": knowledge_hash,
        "full_census_total": 566,
        "non_substantive_and_non_research_identities": 513,
        "original_research_substantive_count": 53,
        "reviewer_must_resolve_paths_from_authorized_source_census": True,
        "original_text_or_source_filenames_included": False,
        "sources": [{
            "source_id": r["source_id"],
            "source_role": r["role"],
            "frozen_git_commit": r["commit"],
            "frozen_git_blob_sha": r["blob_sha"],
            "original_material_disposition": "unaccounted",
            "producer_full_read_record": "full_read",
            "independent_material_verdict": "UNEXECUTED"
        } for r in research],
        "other_role_counts_not_original_first_reviewed": dict(
            sorted(Counter(r["role"] for r in corpus if r not in research).items())
        ),
    }
    ids = [r["source_id"] for r in research]
    template = {
        "packet_kind": "SOURCE_FIRST_ORIGINAL_MATERIAL_REVIEW_RESPONSE",
        "status": "UNEXECUTED_TEMPLATE",
        "publication_commit": commit,
        "knowledge_sha256": knowledge_hash,
        "reviewer_identity": None,
        "reviewer_affiliation_or_role": None,
        "reviewed_at_utc": None,
        "independence_justification_and_prior_involvement": None,
        "authorized_original_access_attestation": None,
        "source_assessment": [{
            "source_id": sid,
            "verified_frozen_blob_at_independent_read": None,
            "full_original_meaning_review_completed": False,
            "source_to_science_claims_and_exact_destinations": [],
            "science_to_source_counterexamples_or_unsupported_claims": [],
            "omitted_material_claims_and_candidate_repairs": [],
            "conflicts_supersession_and_evidence_limits_checked": False,
            "protected_original_content_handling": None,
            "individual_verdict": None,
            "reasoned_materiality_scope_and_limitations": None
        } for sid in ids],
        "review_of_513_other_census_identities": "SEPARATE_REVIEW_REQUIRED",
        "reviewer_signoff_external_to_this_packet": None,
        "global_losslessness": "NOT_CERTIFIED",
        "native_runtime_acceptance": "NOT_TESTED_BY_THIS_PACKET",
    }
    instructions = (
        "# Strategy Box — separate original-first scientific material reviewer\n\n"
        "**This kit is NOT the blind 22-case consumer questionnaire.** "
        "Do not give it to a blind Knowledge-only reviewer before that "
        "reviewer freezes responses; source IDs and Research access would "
        "invalidate the original source-hidden experiment.\n\n"
        "A *different qualified human or accountable independent reviewer* "
        "must read the 53 frozen substantive original Research files. "
        "Resolve each exact original Git path using the separately "
        "authorized same-version source census; the roster deliberately "
        "omits source filenames, document text, historical interpretations "
        "and private carrier references. Recompute each Git blob identity. "
        "Read the whole original: context, formulas, mechanisms, examples, "
        "negative cases, abandoned directions, assumptions and decisions.\n\n"
        "For every source record the original material questions and claims "
        "with exact line intervals; name the actual independently readable "
        "Science paragraph that preserves each distinct important meaning. "
        "Perform Science-to-original reverse checks for stronger-than-evidence "
        "claims, contradictions, adverse cases, scientific uncertainty and "
        "superseded positions. Mark a missing semantic passage or unsafe "
        "publication boundary as OPEN, with owner and repair. Duplicated "
        "material needs a concrete canonical destination and justification; "
        "layout separators require no scientific row but require justified "
        "non-material classification where in question.\n\n"
        "The supplied JSON is a **blank response form**, not a verdict or "
        "pre-filled proposed meaning. Reviewer identity, independence, "
        "source integrity, full original read and evidence locators must "
        "be established externally. Neither GitHub Actions nor this "
        "assistant can certify a different person's independence. "
        "Even a complete 53-original review would not certify the other "
        "513 frozen census identities, actual native releases, physical "
        "Product Decisions, or a full Research Amputation.\n\n"
        "**Safety:** keep restricted/private material and internal details "
        "out of public Research, Work and Knowledge derivatives. Record a "
        "protected content omission as a separately controlled limitation; "
        "do not paste source body, filenames of restricted carriers, "
        "credentials, user data or full source excerpts into response files.\n\n"
        f"**Pinned publication:** `stratbox@{commit}`; "
        f"Knowledge ZIP SHA-256 `{knowledge_hash}`. "
        "This packet must be kept separate from the initial blind "
        "22-case questionnaire.\n"
    ).encode("utf-8")
    payloads = {
        "SOURCE-FIRST-INSTRUCTIONS.md": instructions,
        "SUBSTANTIVE-ORIGINAL-ROSTER.json": encode_json(roster),
        "SOURCE-FIRST-RESPONSE-TEMPLATE.json": encode_json(template),
    }
    manifest = {
        "packet": "SOURCE_FIRST_REVIEWER_REQUEST_ONLY",
        "git_commit": commit,
        "knowledge_sha256": knowledge_hash,
        "original_ids": len(ids),
        "all_census_identities": len(corpus),
        "separate_from_blind_consumer_packet": True,
        "source_text_included": False,
        "source_filenames_included": False,
        "source_review_result_included": False,
        "independent_signoff_included": False,
        "material_disposition": "unaccounted",
        "included_sha256": {name: digest(value) for name, value in sorted(payloads.items())},
    }
    payloads["SOURCE-FIRST-PACKET-MANIFEST.json"] = encode_json(manifest)
    assert set(payloads) == PAYLOAD_NAMES
    for label, body in payloads.items():
        assert b"research/02-" not in body and b"research/03-" not in body, label
        assert b'"source_filename":' not in body, label
        assert b'"original_source_path":' not in body, label
        assert b"source_lines_in_envelope" not in body, label
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w") as archive:
        for name, body in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, TIMESTAMP)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, body, compresslevel=9)
    with zipfile.ZipFile(OUT) as archive:
        assert set(archive.namelist()) == PAYLOAD_NAMES
        for name, body in payloads.items():
            assert archive.read(name) == body
    out_hash = digest(OUT.read_bytes())
    SHA.write_text(out_hash + "  " + OUT.name + "\n", encoding="utf-8")
    return {
        "status": "53_ORIGINAL_FIRST_REVIEWER_REQUEST_PREPARED_ONLY",
        "publication_commit": commit,
        "originals": len(ids),
        "full_census": len(corpus),
        "archive_sha256": out_hash,
        "independent_reviews_received": 0,
        "global_material_state": "unaccounted"
    }


if __name__ == "__main__":
    print(json.dumps(build(), sort_keys=True))
