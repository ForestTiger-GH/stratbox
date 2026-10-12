#!/usr/bin/env python3
"""Assign conservative evidence-owner routes to every non-substantive source role.

This is only source identity and evidential ROLE classification. It never
declares entire Python modules, tests, historical documents, or binaries
semantically preserved. Every registered source remains materially unaccounted.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CENSUS = ROOT / "_mw/epochs-001-strategy-box-development/consolidation/sources/CENSUS.csv"
RESEARCH = {"historical_research", "base_research", "consolidation_research", "ai_raised_research"}
ORIENTATION = {"SB-SRC-0012", "SB-SRC-0017", "SB-SRC-0045"}
OWNERS = {
    "core_auxiliary": ("core_repository", "auxiliary_source_scoped_read"),
    "work_governance": ("consolidation_process", "read_current_governing_owner"),
    "publication_bootstrap": ("published_knowledge", "publication_navigation_evidence"),
    "legacy_document": ("historical_provenance", "review_historical_claims_not_live_authority"),
    "engineering_check": ("core_repository_tests", "execute_relevant_engineering_check"),
    "core_implementation": ("core_implementation_owner", "source_direct_current_how_plus_behavior_test"),
    "core_test": ("core_test_owner", "execute_and_scope_test_evidence"),
    "surface_implementation": ("windows_implementation_owner", "source_direct_current_how_plus_behavior_test"),
    "generated_historical_artifact": ("windows_generated_artifact_history", "metadata_only_sensitive_quarantine"),
    "surface_integration_manifest": ("windows_activation_boundary", "check_exact_external_contract"),
    "surface_documentation": ("windows_surface_docs", "compare_against_pinned_windows_code"),
    "surface_test": ("windows_test_owner", "execute_and_scope_test_evidence"),
    "external_platform_contract": ("external_platform_public_contract", "external_source_contract_only"),
    "research_governance": ("historical_research_orientation", "routing_not_substantive_research"),
}


def verify() -> dict:
    with CENSUS.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 566, len(rows)
    ids = [r["source_id"] for r in rows]
    assert len(ids) == len(set(ids))
    assert all(r["material_unit_state"] == "unaccounted" for r in rows)
    substantive = [r for r in rows if r["role"] in RESEARCH and r["source_id"] not in ORIENTATION]
    orient = [r for r in rows if r["source_id"] in ORIENTATION]
    other = [r for r in rows if r["role"] not in RESEARCH]
    assert len(substantive) == 53
    assert len(orient) == 3
    assert len(other) == 510
    assert len(OWNERS) == len(set(r["role"] for r in other))
    assert {r["role"] for r in other} == set(OWNERS)
    role_counts = Counter(r["role"] for r in other)
    obligations = Counter(OWNERS[r["role"]][1] for r in other)
    assert sum(role_counts.values()) == 510
    assert sum(obligations.values()) == 510
    # No fabricated per-module verification, current implementation, semantic
    # understanding, binary content, or independent review.
    return {
        "verdict": "ALL_NONRESEARCH_IDENTITIES_ROUTED_BY_ROLE_ONLY_NOT_MATERIAL_DISPOSITION",
        "git_source_identities": len(rows),
        "substantive_research_originals_with_separate_science_accounting": len(substantive),
        "research_orientation_sources_not_substantive": len(orient),
        "nonresearch_or_other_source_roles_routed": len(other),
        "other_role_counts": dict(sorted(role_counts.items())),
        "candidate_evidence_obligations": dict(sorted(obligations.items())),
        "materially_unaccounted": len(rows),
        "direct_owner_review": "OPEN",
        "independent_assurance": "OPEN",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
