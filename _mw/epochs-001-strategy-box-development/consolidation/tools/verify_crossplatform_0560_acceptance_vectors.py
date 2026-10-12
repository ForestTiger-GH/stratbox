#!/usr/bin/env python3
"""Exact Topic-07 cross-platform acceptance proposal routing, STRUCTURAL ONLY.

Checks frozen primary rows and the 5+12 source-labelled destination cases.
No installed Web/Android/AppDock host, a11y, perf or independent semantic
certification is inferred from this check.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pinned_source import read_pinned_blob

ROOT = Path(__file__).resolve().parents[4]
REV = "388e3d61ec01350d3b7d35ea4a97a21db0b36f97"
BLOB = "9613663bb0b546c404a6937193e05ec499eec656"
SOURCE = (
    "_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/"
    "07_mezhplatformennaya_arkhitektura_prilozheniy_strategy_box_2026-10-10.md"
)
SCIENCE = ROOT / "docs/science/surfaces/semantic-portability-and-client-authority.md"
EXPECTED_C = [f"C07-C{i:02d}" for i in range(1, 6)]
EXPECTED_M = [f"C07-M{i:02d}" for i in range(1, 13)]
EXPECTED_ORIGINAL = (
    "Два клиента запускают разные jobs",
    "Два клиента повторяют запрос с одинаковым idempotency key",
    "Web закрыт при `running`",
    "Android offline при job success",
    "Смена роли участника в другом клиенте",
    "Обновление source/action descriptors",
    "Перенос/удаление файла на host",
    "Artifact не полностью опубликован",
    "Ошибка AppDock remote capability",
    "Android перезапускается / экран вращается",
    "Browser user вводит путь `../`",
    "Ошибка логина / brute-force",
)
CHECK = re.compile(r"^\|\s*`(C07-[CM]\d{2})`\s*\|([^\n]*)$", re.MULTILINE)


def check() -> dict:
    original = read_pinned_blob(ROOT, REV, SOURCE, BLOB).decode("utf-8")
    assert len(original.splitlines()) == 704
    intro = original.split("### 15.1. Контрактный gate без GUI", 1)[1].split(
        "### 15.2. Multi-client behavioural tests", 1)[0]
    items = re.findall(r"(?m)^([1-5])\.\s+(.+)$", intro)
    assert [n for n, _ in items] == list("12345"), items
    assert all(len(x) > 45 for _, x in items), items
    original_table = original.split(
        "### 15.2. Multi-client behavioural tests", 1)[1].split(
        "### 15.3. UX/performance/a11y spike", 1)[0]
    raw_rows = re.findall(r"(?m)^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$", original_table)
    rows = [(q.strip(), a.strip()) for q, a in raw_rows
            if q.strip() not in ("Кейс", "---")]
    assert [row[0] for row in rows] == list(EXPECTED_ORIGINAL), rows
    assert all(len(answer) >= 32 for _, answer in rows)
    assert "1000+" in original and "20/200 МБ" in original
    assert "### 15.4. AppDock integration gate" in original

    published = SCIENCE.read_text(encoding="utf-8")
    section = published.split(
        "### Original Topic 07 — exact contract, multi-client, performance and external-platform acceptance intentions",
        1)[1].split("**Competing perspectives:**", 1)[0]
    cases = CHECK.findall(section)
    ids = [key for key, _ in cases]
    assert ids == EXPECTED_C + EXPECTED_M, (ids, EXPECTED_C + EXPECTED_M)
    assert len(set(ids)) == 17
    assert all(len(row.split("|")) >= 2 and
               all(len(cell.strip()) >= 30 for cell in row.split("|")[:2])
               for _, row in cases)
    assert all(published.count(f"`{key}`") == 1
               for key in (*EXPECTED_C, *EXPECTED_M, "C07-P01", "C07-A01"))
    assert "UNEXECUTED" in section
    assert "performance/accessibility" in section and "external-platform integration" in section
    assert "1000" in section.replace(",", "") and "20/200 MB" in section
    return {
        "status": "PASS_SOURCE_VECTOR_IDENTITY_AND_DESTINATION_STRUCTURE_ONLY",
        "source_id": "SB-SRC-0560",
        "original_blob": BLOB,
        "original_contract_test_intentions": 5,
        "original_multi_client_cases": len(rows),
        "published_case_rows": len(ids),
        "other_original_performance_and_platform_gates": 2,
        "original_executable_target_web_android_tests": "UNEXECUTED",
        "independent_whole_original_material_pass": "UNEXECUTED",
        "material_state": "unaccounted",
    }


if __name__ == "__main__":
    print(json.dumps(check(), ensure_ascii=False))
