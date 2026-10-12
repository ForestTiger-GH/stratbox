#!/usr/bin/env python3
"""Check documentation-only LCD Python blocks for parseability and explicit status.

This checks syntax and basic source-document invariants, NOT executability,
implementation readiness, domain correctness, or independent review.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LCD = ROOT / "docs/lcd"
START = re.compile(r"^([~`]{3,})python\s*$", re.IGNORECASE)
CLOSE = re.compile(r"^[~`]{3,}\s*$")
GRADE = re.compile(r"\bLCD_(?:CANDIDATE|BLOCKED|READY_FOR_IMPLEMENTATION)\b")


def extract_python_blocks(text: str, filename: str) -> tuple[list[tuple[int, str]], list[str]]:
    blocks: list[tuple[int, str]] = []
    errors: list[str] = []
    inside = False
    start_line = 0
    fence = ""
    chunk: list[str] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not inside:
            found = START.fullmatch(stripped)
            if found:
                inside = True
                fence = found.group(1)
                start_line = line_number
                chunk = []
            continue
        if CLOSE.fullmatch(stripped) and stripped[0] == fence[0] and len(stripped) >= len(fence):
            blocks.append((start_line, "\n".join(chunk) + "\n"))
            inside = False
            fence = ""
            chunk = []
        else:
            chunk.append(line)
    if inside:
        errors.append(f"{filename}:{start_line}: unclosed Python fence")
    return blocks, errors


def audit() -> dict[str, object]:
    problems: list[str] = []
    documents = 0
    blocks_count = 0
    node_count = 0
    per_doc: list[dict[str, object]] = []
    paths = sorted(p for p in LCD.rglob("*.md") if p.name != "README.md")
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        if not GRADE.search(text):
            problems.append(f"{rel}: missing explicit LCD grade")
        if "CANDIDATE_DESIGN" not in text and "NOT_APPLICABLE" not in text:
            problems.append(f"{rel}: candidate code has no documentation-only label")
        blocks, issues = extract_python_blocks(text, rel)
        problems.extend(issues)
        parsed_here = 0
        classes = 0
        defs = 0
        for start, source in blocks:
            try:
                module = ast.parse(source, filename=f"{rel}:{start}")
            except SyntaxError as exc:
                problems.append(f"{rel}:{start}: invalid Python skeleton: {exc.msg} at fragment line {exc.lineno}")
                continue
            parsed_here += 1
            classes += sum(isinstance(n, ast.ClassDef) for n in ast.walk(module))
            defs += sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(module))
            node_count += len(list(ast.walk(module)))
        documents += 1
        blocks_count += len(blocks)
        per_doc.append({
            "path": rel, "python_blocks": len(blocks),
            "parsed_blocks": parsed_here, "classes": classes, "functions": defs,
        })
    if not paths:
        problems.append("No concrete LCD documentation found")
    return {
        "verdict": "SYNTAX_AND_STATUS_STRUCTURE_PASS" if not problems else "SYNTAX_OR_STATUS_STRUCTURE_FAIL",
        "scope": "Python fenced blocks only; parseable fragments are NOT runnable production code",
        "documents": documents, "python_blocks": blocks_count,
        "ast_nodes": node_count,
        "documents_detail": per_doc, "errors": problems,
        "independent_semantic_review": "NOT_PERFORMED",
        "implementation_readiness": "NOT_ESTABLISHED",
    }


if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, indent=2))
    sys.exit(0 if not result["errors"] else 1)
