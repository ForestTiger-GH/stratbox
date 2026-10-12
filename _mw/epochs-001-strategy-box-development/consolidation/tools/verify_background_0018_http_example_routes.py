#!/usr/bin/env python3
"""Structural original-0018 candidate HTTP surface preservation, not API testing.

This source-first check ensures all literal proposed routes have an explicit
historical qualified destination without establishing their semantic correctness.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
REV = "8459dc58922b7e8df853cf1d9e8131fa9e132580"
BLOB = "5ed80eeb3065b60f89d0706bfa49bbfd272fc066"
SOURCE = (
    "_mw/epochs-001-strategy-box-development/research/02-base-study/"
    "Strategy_Box_background_jobs_processes_architecture_research_2026-10-08.md"
)
SCIENCE = ROOT / "docs/science/work/admission-planning-resource-scheduling-and-recovery.md"
EXPECTED = [
    "POST /api/v1/scenarios/{scenario_id}/runs",
    "POST /api/v1/cascades/{cascade_id}/runs",
    "GET /api/v1/jobs?state=active",
    "GET /api/v1/jobs/{job_id}",
    "POST /api/v1/jobs/{job_id}/cancel",
    "POST /api/v1/jobs/{job_id}/retry",
    "GET /api/v1/cases/{case_id}",
    "GET /api/v1/cases/{case_id}/events",
    "GET /api/v1/chats",
    "GET /api/v1/chats/{chat_id}/entries",
    "GET /api/v1/task-center/summary",
    "GET /api/v1/automations",
    "POST /api/v1/automations",
    "PATCH /api/v1/automations/{automation_id}",
    "POST /api/v1/automations/{automation_id}/run-now",
    "POST /api/v1/automations/{automation_id}/pause",
    "POST /api/v1/automations/{automation_id}/resume",
    "GET /api/v1/events/stream?after_seq=12345"
]

def verify() -> dict:
    original = read_pinned_blob(ROOT, REV, SOURCE, BLOB).decode("utf-8")
    original_routes = original.split("## 43. API операций", 1)[1].split(
        "## 44. Транзакционное правило submit", 1)[0]
    original_lines = re.findall(
        r"^\s*(GET|POST|PATCH|PUT|DELETE)\s+(/api/v1/[^\s]+)\s*$",
        original_routes, flags=re.MULTILINE
    )
    actual = [method + " " + path for method, path in original_lines]
    assert actual == EXPECTED, ("frozen-original/API example changed", actual)
    science = SCIENCE.read_text(encoding="utf-8")
    candidate = science.split(
        "### Historical 0018 machine contract examples and transactional handoff:",
        1)[1].split("## 15. Source topic 02:", 1)[0]
    rows = re.findall(
        r"^\|\s*(BG-API-\d{2})\s*\|\s*`((?:GET|POST|PATCH|PUT|DELETE) /api/v1/[^`]+)`\s*\|([^|]+)\|([^|]+)\|$",
        candidate, flags=re.MULTILINE
    )
    assert len(rows) == len(EXPECTED) == 18, len(rows)
    for i, (ident, path, intended, negative) in enumerate(rows):
        assert ident == f"BG-API-{i+1:02d}", ident
        assert path == EXPECTED[i], (ident, path)
        assert len(intended.strip()) > 8 and len(negative.strip()) > 30, ident
    for marker in ("NOT", "candidate", "not an authorization",
                   "durable dispatch", "opaque", "Work/Run/Case",
                   "HTTP response", "external file"):
        assert marker.lower() in candidate.lower(), marker
    return {
        "verdict": "SOURCE_0018_EXAMPLE_ROUTES_STRUCTURAL_PRESERVATION_ONLY",
        "source_id": "SB-SRC-0018", "blob": BLOB,
        "original_examples": len(actual),
        "maintained_examples": len(rows),
        "verified_real_network_endpoints": 0,
        "independent_semantic_losslessness": "UNEXECUTED",
        "material_unit_state": "unaccounted",
    }

if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
