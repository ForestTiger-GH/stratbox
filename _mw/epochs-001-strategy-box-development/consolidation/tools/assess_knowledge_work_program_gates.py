#!/usr/bin/env python3
"""Evidence-bounded Knowledge Work Program gate snapshot.

Machine-verifiable facts are checked. Human/independent/real-runtime gates
stay OPEN unless a separately admitted, verifiable receipt exists. This
script MUST NOT turn its own successful execution into LOSSLESS_PASS.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import zipfile
from collections import Counter
from pathlib import Path

from validate_source_first_assessor_handoff import packet as independent_packet, validate_response

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "_mw/epochs-001-strategy-box-development/consolidation"
DOCS = ROOT / "docs"
DIST = ROOT / "dist"
OUTPUT = DIST / "strategy-box-work-program-gates.json"
RESEARCH = {"historical_research", "base_research", "consolidation_research",
            "ai_raised_research"}
ORIENTATIONS = {"SB-SRC-0012", "SB-SRC-0017", "SB-SRC-0045"}


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, cwd=ROOT).strip()


def read_census() -> dict:
    with (BASE / "sources/CENSUS.csv").open(
            encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 566, "frozen source population changed"
    assert len(set(x["source_id"] for x in rows)) == 566
    substantial = [x for x in rows if x["role"] in RESEARCH
                   and x["source_id"] not in ORIENTATIONS]
    orientation = [x for x in rows if x["source_id"] in ORIENTATIONS]
    other = [x for x in rows if x["role"] not in RESEARCH]
    assert len(substantial) == 53 and len(orientation) == 3 and len(other) == 510
    read = Counter(x["read_state"] for x in rows)
    materials = Counter(x["material_unit_state"] for x in rows)
    assert sum(read.values()) == sum(materials.values()) == 566
    return {
        "frozen_git_source_identities": len(rows),
        "substantive_research_originals": len(substantial),
        "research_orientation_files": len(orientation),
        "nonresearch_role_scoped_sources": len(other),
        "read_states": dict(sorted(read.items())),
        "material_states": dict(sorted(materials.items())),
        "substantive_research_not_full_read": [
            x["source_id"] for x in substantial if x["read_state"] != "full_read"],
        "source_identities_with_unresolved_material": sum(
            n for state, n in materials.items() if state == "unaccounted"),
    }


def check_archives(expected_commit: str) -> dict:
    knowledge = DIST / "strategy-box-knowledge-standalone.zip"
    questionnaire = DIST / "strategy-box-independent-reader-questions.zip"
    assert knowledge.is_file() and questionnaire.is_file()
    digest = hash_bytes(knowledge.read_bytes())
    assert digest == (DIST / "strategy-box-knowledge-standalone.sha256").read_text(
        encoding="utf-8").split()[0]
    qdigest = hash_bytes(questionnaire.read_bytes())
    assert qdigest == (DIST / "strategy-box-independent-reader-questions.sha256").read_text(
        encoding="utf-8").split()[0]
    actual_docs = {
        "docs/" + p.relative_to(DOCS).as_posix(): hash_bytes(p.read_bytes())
        for p in DOCS.rglob("*") if p.is_file()
    }
    assert len([p for p in actual_docs if p.endswith(".md")]) == 114
    with zipfile.ZipFile(knowledge) as z:
        names = set(z.namelist())
        assert names == {"KNOWLEDGE-HASHES.json", *actual_docs}
        internal = json.loads(z.read("KNOWLEDGE-HASHES.json"))
        assert internal["git_commit"] == expected_commit
        assert internal["files_sha256"] == actual_docs
        assert internal["independent_research_semantic_assurance"] == "OPEN"
    with zipfile.ZipFile(questionnaire) as z:
        names = set(z.namelist())
        assert names == {
            "INSTRUCTIONS.md", "QUESTIONNAIRE.md",
            "RESPONSE-TEMPLATE.json", "REVIEWER-PACKET-MANIFEST.json"}
        manifest = json.loads(z.read("REVIEWER-PACKET-MANIFEST.json"))
        answers = json.loads(z.read("RESPONSE-TEMPLATE.json"))
        assert manifest["git_commit"] == expected_commit
        assert manifest["knowledge_zip_sha256"] == digest
        assert manifest["question_count"] == 22
        assert len(manifest["case_ids"]) == 22
        assert manifest["producer_answers_included"] is False
        assert manifest["status"] == "REVIEWER_UNEXECUTED"
        assert answers["status"] == "UNEXECUTED_TEMPLATE"
        assert answers["answers_frozen_before_research"] is False
        assert len(answers["cases"]) == 22
        assert all(x["answer"] is None and x["classification"] is None
                   for x in answers["cases"])
    return {
        "knowledge_docs_markdown": 114,
        "knowledge_inner_zip_sha256": digest,
        "questionnaire_zip_sha256": qdigest,
        "questionnaire_cases": 22,
        "questionnaire_answer_key_present": False,
        "independent_reviewer_answers_in_packet": 0,
        "packet_revision_bound": True,
        "scope": "byte_integrity_and_question_distribution_ONLY",
    }


def check_source_first_original_handoff(expected_commit: str, expected_knowledge_hash: str) -> dict:
    """Read exact 53-original review request without claiming a reviewer exists."""
    roster, template, manifest = independent_packet()
    assert roster["publication_commit"] == expected_commit
    assert manifest["git_commit"] == expected_commit
    assert roster["knowledge_sha256"] == expected_knowledge_hash
    outcome = validate_response(template, roster)
    assert outcome["classification"] == "BLANK_UNEXECUTED_TEMPLATE"
    assert outcome["claims_of_reviewed_sources"] == 0
    assert outcome["global_losslessness"] == "NOT_CERTIFIED"
    return {
        "source_first_original_ids": 53,
        "source_first_response_record_count": outcome["source_records"],
        "source_first_assessor_reviews_received": 0,
        "independent_reviewer_identity_authentication": "UNEXECUTED",
        "original_to_science_meaning_attestation": "UNEXECUTED",
        "source_first_handoff": "PREPARED_NOT_ADMINISTERED",
        "other_census_source_roles": "513_REMAIN_SEPARATE",
        "source_first_packet_exact_publication_binding": True,
        "whole_program_completion": "BLOCKED",
    }


def check_native_posix_evidence(expected_commit: str) -> dict:
    path = ROOT / "native_storage_fault_audit.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["git_commit"] == expected_commit
    assert data["status"] == "BOUND_TO_POSIX_NATIVE_LOCAL_TEMPORARY_FILES"
    expected = {
        "preopen_path_containment_can_be_invalidated",
        "single_final_component_nofollow_refusal",
        "open_fd_and_inode_do_not_ensure_immutable_bytes",
        "unfenced_repeated_staging_reads_disagree",
        "plain_replace_clobbers_a_changed_target",
        "posix_link_create_only_rejects_collision",
        "posix_link_create_only_adds_fresh_name",
        "same_bytes_different_observation_time_remain_equal",
    }
    assert data["passed"] == 8
    assert set(data["cases"]) == expected
    assert all(data["cases"].values())
    assert "not_proved" in data and any(
        "Windows" in term for term in data["not_proved"])
    return {
        "grade": "PRODUCER_LINUX_NATIVE_BOUNDED_EFFECT_EVIDENCE",
        "exact_commit": expected_commit,
        "passed": 8,
        "known_windows_smb_and_durable_storage": "NOT_ATTESTED",
        "profile_limit": data["scope"],
    }


def main() -> dict:
    head = commit()
    sources = read_census()
    bundles = check_archives(head)
    original_first = check_source_first_original_handoff(
        head, bundles["knowledge_inner_zip_sha256"])
    native_posix = check_native_posix_evidence(head)
    assert sources["substantive_research_not_full_read"] == []
    # This program can PROVE OPEN through explicit census evidence.
    # It has no authority to infer that an absent human review is completed.
    global_pass = sources["source_identities_with_unresolved_material"] == 0
    assert not global_pass, (
        "An input-integrity validator exists, but independently authenticated "
        "whole-corpus material-verification receipts have NOT been supplied")
    data = {
        "git_commit": head,
        "classification": "PRODUCER_MACHINE_CHECKED_GATE_SNAPSHOT",
        "status": "PARTIAL_WITH_EXTERNAL_INDEPENDENT_AND_IMPLEMENTATION_GATES",
        "frozen_source_population": sources,
        "reproducible_deliverables": bundles,
        "original_first_review_request": original_first,
        "bounded_native_posix_evidence": native_posix,
        "gates": {
            "source_identity_census": "PASS_EXACT_FROZEN_566",
            "all_53_substantive_research_read_producer": "PASS_PRODUCER_READ_STATE_ONLY",
            "all_material_meaning_independently_disposed": "BLOCKED_566_UNACCOUNTED",
            "source_reverse_semantic_certification": "NO_AUTHORIZED_INDEPENDENT_RECEIPT",
            "knowledge_archive_structural_navigation": "PASS_BOUNDED_CHECKS",
            "question_only_22_case_independent_handoff": "PREPARED_NOT_ADMINISTERED",
            "source_first_53_original_request": "PREPARED_NOT_ADMINISTERED",
            "source_first_53_original_response_input_checks": "PASS_STRUCTURAL_ONLY",
            "blind_independent_knowledge_consumer_review": "UNEXECUTED",
            "independent_original_first_reverse_check": "UNEXECUTED",
            "ten_lcd_candidate_fragment_probes": "CI_PRODUCER_FAKE_ONLY",
            "actual_linux_local_posix_race_characterization": "PASS_EIGHT_BOUNDED_REAL_FILESYSTEM_CASES",
            "actual_target_windows_smb_host_security_storage_domain_conformance": "UNEXECUTED",
            "product_platform_security_policy_decisions": "OPEN_WITH_OWNER",
            "lost_annotated_human_binary": "OWNER_DECLARED_LOST_EXCLUDED",
            "global_lossless_pass": "BLOCKED",
        },
        "publication_does_not_require_original_research_to_navigate": True,
        "irreducible_dependencies": [
            "qualified independent semantic source-to-Science and reverse evaluator",
            "different competent 22-case Knowledge-only reader with frozen responses",
            "actual authorized Product/Security/Platform/Operations decisions",
            "native and domain implementations plus real conformance where needed",
        ],
        "limits": (
            "A passing CI step proves only that this gate report truthfully "
            "declares unresolved evidence, not that independent review or "
            "a deployed host has occurred."),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                  indent=2) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    out = main()
    print(json.dumps({
        "git_commit": out["git_commit"],
        "status": out["status"],
        "gates": out["gates"],
        "question_count": out["reproducible_deliverables"]["questionnaire_cases"],
        "original_first_requests": out["original_first_review_request"]["source_first_original_ids"],
        "independent_original_reviews_received": out["original_first_review_request"]["source_first_assessor_reviews_received"],
        "unaccounted": out["frozen_source_population"]["source_identities_with_unresolved_material"],
    }, ensure_ascii=False))
