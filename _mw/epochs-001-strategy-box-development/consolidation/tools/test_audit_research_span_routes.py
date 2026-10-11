#!/usr/bin/env python3
"""Isolated stdlib regression checks for structural Research route accounting.

These are parser and line-accounting tests, not a semantic preservation test
or an independent scientific reviewer.
"""
from __future__ import annotations
import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("audit_research_span_routes.py")
spec = importlib.util.spec_from_file_location("structural_span_audit", MODULE_PATH)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


class StructuralAuditBoundaryTests(unittest.TestCase):
    def test_pinned_terminal_empty_line_can_be_addressed(self):
        original = "# Original\n"
        lines = original.split("\n")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[1], "")
        self.assertEqual(len(original.splitlines()), 1)
        self.assertIsNotNone(audit.SPAN.fullmatch("L2-L2"))
        # This is a valid locator in the frozen original offset convention;
        # a zero-content terminal line is not automatically substantive.
        self.assertEqual({i for i, x in enumerate(lines, 1) if x.strip()}, {1})

    def test_two_span_spellings_and_invalid_range(self):
        self.assertIsNotNone(audit.SPAN.fullmatch("L4-7"))
        self.assertIsNotNone(audit.SPAN.fullmatch("L4-L7"))
        self.assertIsNone(audit.SPAN.fullmatch("4-L7"))
        self.assertIsNone(audit.SPAN.fullmatch("L4-Lnot"))

    def test_science_topic_is_a_valid_candidate_destination(self):
        x = {
            "science_topic": "docs/science/extensions/example.md",
            "preserved_exact_test_row": "docs/ldd/extensions/example.md",
        }
        self.assertEqual(audit.destination(x), "docs/science/extensions/example.md")
        self.assertIsNone(audit.destination({"preserved_exact_test_row": "docs/ldd/other.md"}))
        self.assertEqual(audit.destination({"science_candidate_owner": "docs/science/automation/one.md"}), "docs/science/automation/one.md")
        self.assertIsNone(audit.destination({}))

    def test_frozen_line_and_explicit_span_take_distinct_routes(self):
        self.assertEqual(audit.source_locator({"source_line": 42}), "L42")
        self.assertEqual(audit.source_locator({"source_line": 42, "source_span": "L15-L27"}), "L15-L27")
        self.assertEqual(audit.source_locator({"span": "L9-L12"}), "L9-L12")
        self.assertIsNone(audit.source_locator({"source_line": 0}))

    def test_section_locator_does_not_count_as_preserved_material(self):
        self.assertEqual(audit.kind({"source_span": "L2-L6"}, "SECTION-INDEX-0025.jsonl"), "section_or_route")
        self.assertEqual(audit.kind({"source_line": 5}, "PROVIDER-EXACT-VECTORS-0025.jsonl"), "source_exact_transfer")
        self.assertEqual(audit.kind({"span": "L1-L20", "material_status": "producer_provisional_section_candidate"}, "BASE-STUDY-AUTOMATION-AI-0041.jsonl"), "section_or_route")

    def test_only_explicit_numeric_science_section_references_are_checked(self):
        self.assertEqual(
            audit.exact_science_section_locator({
                "science_destination": "docs/science/data-and-knowledge/example.md §12"
            }),
            ("docs/science/data-and-knowledge/example.md", 12),
        )
        self.assertIsNone(audit.exact_science_section_locator({
            "science_destination": "docs/science/example.md §§12-15"
        }))
        self.assertIsNone(audit.exact_science_section_locator({
            "science_topic": "docs/science/example.md"
        }))

    def test_holes_only_expose_candidates(self):
        lines = ["heading", "meaning", "", "counterexample", "alternative", "assumption", "unknown", "cost"]
        parts = audit.holes(lines, {1}, minimum=5)
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]["span"], "L2-L8")
        self.assertEqual(parts[0]["untraced_nonblank_lines"], 6)


if __name__ == "__main__":
    unittest.main()
