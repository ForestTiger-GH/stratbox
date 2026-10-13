#!/usr/bin/env python3
"""Fail-closed producer checks for the blank 53-source independent review packet.

No assessment, reviewer identity validation, protected-source text processing,
Science preservation verdict, census mutation or production application call.
Optional external response validation emits only metadata and NEVER PASS.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DIST = ROOT / "dist"
KIT = DIST / "strategy-box-source-first-reviewer-roster.zip"
KNOWLEDGE = DIST / "strategy-box-knowledge-standalone.zip"
EXPECTED_FILES = {
    "SOURCE-FIRST-INSTRUCTIONS.md",
    "SUBSTANTIVE-ORIGINAL-ROSTER.json",
    "SOURCE-FIRST-RESPONSE-TEMPLATE.json",
    "SOURCE-FIRST-PACKET-MANIFEST.json",
}


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def require(condition: bool, explanation: str) -> None:
    if not condition:
        raise ValueError(explanation)


def packet() -> tuple[dict, dict, dict]:
    with zipfile.ZipFile(KIT) as archive:
        names = set(archive.namelist())
        require(names == EXPECTED_FILES, "review-kit-entry-set-drift")
        manifest = json.loads(archive.read("SOURCE-FIRST-PACKET-MANIFEST.json"))
        for name in EXPECTED_FILES - {"SOURCE-FIRST-PACKET-MANIFEST.json"}:
            require(manifest["included_sha256"][name] == sha256(archive.read(name)),
                    "review-kit-entry-digest-mismatch")
        roster = json.loads(archive.read("SUBSTANTIVE-ORIGINAL-ROSTER.json"))
        template = json.loads(archive.read("SOURCE-FIRST-RESPONSE-TEMPLATE.json"))
    require(manifest["knowledge_sha256"] == sha256(KNOWLEDGE.read_bytes()),
            "review-source-publication-version-mismatch")
    require(manifest["source_review_result_included"] is False,
            "source-review-must-not-be-preapproved")
    require(manifest["independent_signoff_included"] is False,
            "source-review-must-not-be-signed-by-producer")
    require(roster["status"] == "UNEXECUTED_PRODUCER_PREPARATION",
            "roster-not-unexecuted")
    sources = roster["sources"]
    require(len(sources) == 53 and roster["full_census_total"] == 566,
            "frozen-research-denominator-drift")
    ids = [item["source_id"] for item in sources]
    require(len(set(ids)) == 53 and ids == sorted(ids),
            "roster-ids-not-unique-and-sorted")
    for item in sources:
        require(re.fullmatch(r"SB-SRC-[0-9]{4}", item["source_id"]) is not None,
                "source-identifier-invalid")
        require(re.fullmatch(r"[0-9a-f]{40}", item["frozen_git_commit"]) is not None,
                "original-commit-invalid")
        require(re.fullmatch(r"[0-9a-f]{40}", item["frozen_git_blob_sha"]) is not None,
                "original-git-blob-invalid")
        require(item["original_material_disposition"] == "unaccounted"
                and item["independent_material_verdict"] == "UNEXECUTED",
                "producer-must-not-preset-independent-source-disposition")
    require(template["status"] == "UNEXECUTED_TEMPLATE", "response-form-pre-signed")
    require(template["reviewer_identity"] is None
            and template["reviewer_signoff_external_to_this_packet"] is None,
            "response-form-pre-populated-reviewer")
    require(template["global_losslessness"] == "NOT_CERTIFIED",
            "response-form-fabricated-global-certification")
    return roster, template, manifest


def validate_response(response: dict, roster: dict) -> dict:
    require(response["packet_kind"] == "SOURCE_FIRST_ORIGINAL_MATERIAL_REVIEW_RESPONSE",
            "unexpected-response-kind")
    require(response["publication_commit"] == roster["publication_commit"]
            and response["knowledge_sha256"] == roster["knowledge_sha256"],
            "publication-identity-mismatch")
    require(response.get("global_losslessness") == "NOT_CERTIFIED"
            and response.get("review_of_513_other_census_identities")
            == "SEPARATE_REVIEW_REQUIRED",
            "research-slice-cannot-certify-global-566-corpus")
    records = response["source_assessment"]
    require(isinstance(records, list) and len(records) == 53,
            "must-include-exact-53-records")
    roster_by_id = {x["source_id"]: x for x in roster["sources"]}
    response_ids = [x["source_id"] for x in records]
    require(set(response_ids) == set(roster_by_id)
            and len(set(response_ids)) == len(response_ids),
            "missing-extra-or-duplicate-source-identifier")
    completed = 0
    for item in records:
        if item["individual_verdict"] is None:
            require(item["full_original_meaning_review_completed"] is False,
                    "incomplete-review-claims-full-read")
            continue
        require(item["full_original_meaning_review_completed"] is True,
                "verdict-without-whole-original-review")
        require(item["verified_frozen_blob_at_independent_read"]
                == roster_by_id[item["source_id"]]["frozen_git_blob_sha"],
                "unverified-or-wrong-original-blob")
        require(item["conflicts_supersession_and_evidence_limits_checked"] is True,
                "verdict-without-conflict-and-defeater-review")
        require(isinstance(item["source_to_science_claims_and_exact_destinations"], list)
                and bool(item["source_to_science_claims_and_exact_destinations"]),
                "verdict-without-source-to-science-evidence")
        require(isinstance(item["reasoned_materiality_scope_and_limitations"], str)
                and len(item["reasoned_materiality_scope_and_limitations"].strip()) >= 25,
                "verdict-without-reasoned-boundaries")
        completed += 1
    if completed:
        for key in ("reviewer_identity", "reviewer_affiliation_or_role",
                    "reviewed_at_utc",
                    "independence_justification_and_prior_involvement",
                    "authorized_original_access_attestation"):
            require(isinstance(response.get(key), str) and bool(response[key].strip()),
                    "claimed-review-missing-assessor-attribution:" + key)
        require(response["status"] in ("EXTERNAL_REVIEW_CANDIDATE",
                                        "PARTIAL_EXTERNAL_REVIEW_CANDIDATE"),
                "review-response-status-invalid")
    else:
        require(response["status"] == "UNEXECUTED_TEMPLATE",
                "blank-review-cannot-claim-completion")
    return {
        "classification": ("BLANK_UNEXECUTED_TEMPLATE" if completed == 0
                           else "STRUCTURALLY_PRESENTED_REVIEW_REQUIRES_EXTERNAL_AUTHENTICATION"),
        "source_records": len(records),
        "claims_of_reviewed_sources": completed,
        "remaining_source_records": 53 - completed,
        "independent_assessor_identity_verified_by_tool": False,
        "individual_semantic_verdicts_verified_by_tool": False,
        "global_losslessness": "NOT_CERTIFIED",
        "census_dispositions_changed": 0,
    }


def self_test() -> dict:
    roster, blank, manifest = packet()
    result = validate_response(blank, roster)
    require(result["classification"] == "BLANK_UNEXECUTED_TEMPLATE"
            and result["claims_of_reviewed_sources"] == 0,
            "blank-form-misclassified")
    negatives = 0

    def must_reject(mutator) -> None:
        nonlocal negatives
        document = copy.deepcopy(blank)
        mutator(document)
        try:
            validate_response(document, roster)
        except (ValueError, KeyError, TypeError):
            negatives += 1
            return
        raise AssertionError("false-positive-review-acceptance")

    must_reject(lambda q: q.update(global_losslessness="LOSSLESS_PASS"))
    must_reject(lambda q: q.update(publication_commit="0" * 40))
    must_reject(lambda q: q["source_assessment"].pop())
    must_reject(lambda q: q["source_assessment"][0].update(source_id="SB-SRC-9999"))
    must_reject(lambda q: q["source_assessment"][0].update(individual_verdict="PRESERVED"))
    must_reject(lambda q: q["source_assessment"][0].update(full_original_meaning_review_completed=True))
    must_reject(lambda q: q.update(status="LOSSLESS_PASS"))
    return {
        "status": "SOURCE_FIRST_BLANK_PACKET_AND_NEGATIVE_GATES_PASS",
        "source_count": 53,
        "negative_forgery_and_incompleteness_checks": negatives,
        "packet_publication_sha256": manifest["knowledge_sha256"],
        "review_receipts_received": 0,
        "independent_verifier": "ABSENT",
        "global_losslessness": "NOT_CERTIFIED",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--response", type=Path, default=None,
                        help="Optional locally held assessor response JSON; never uploaded or echoed")
    args = parser.parse_args()
    if args.response is None:
        result = self_test()
    else:
        roster, _, _ = packet()
        result = validate_response(json.loads(args.response.read_text(encoding="utf-8")),
                                   roster)
    print(json.dumps(result, sort_keys=True))
