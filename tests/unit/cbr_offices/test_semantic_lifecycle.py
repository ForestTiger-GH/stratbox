"""Capture dates, source identities and calculations keep their distinct meaning."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
import re

import pytest

from stratbox.core.commands.products import product_render, view_prepare
from stratbox.domains.cbr.domain import DOMAIN
from stratbox.shared.data.values import Material

from .helpers import BANK, CAPTURED, HTML, OFFICIAL, bank_evidence, call, compare, context, roundtrip


def test_later_capture_keeps_the_same_official_state():
    before = bank_evidence()[2]
    after = bank_evidence(date(2026, 11, 23))[2]
    assert compare(before, after)["changes"] == ()
    assert before.semantics["captured_on"] != after.semantics["captured_on"]
    assert before.semantics["official_as_of"] == after.semantics["official_as_of"] == OFFICIAL.isoformat()
    assert {row["period"] for row in after.rows} == {OFFICIAL.isoformat()}


def test_two_official_states_captured_on_one_day_keep_distinct_periods():
    before = bank_evidence()[2]
    after = bank_evidence(CAPTURED, date(2026, 12, 1))[2]
    changes = compare(before, after)["changes"]
    assert {row["period"] for row in before.rows} == {"2026-11-01"}
    assert {row["period"] for row in after.rows} == {"2026-12-01"}
    assert {item["kind"] for item in changes} == {"added", "removed"}
    assert not any(item["delta"] is not None for item in changes)


def test_dropped_coverage_remains_explicit_in_the_comparison():
    before = bank_evidence()[2]
    shortened = re.sub(r"<tr><td>Новый регион.*?</tr>", "", HTML.read_text()).encode()
    after = bank_evidence(date(2026, 11, 23), data=shortened)[2]
    changes = compare(before, after)["changes"]
    assert changes and all(item["kind"] == "removed" and item["after"] is None for item in changes)
    assert len(after.rows) < len(before.rows)


def test_capture_period_is_qualified_when_the_official_date_is_unknown():
    dataset = bank_evidence(official=None)[2]
    assert dataset.semantics["official_as_of"] is None
    assert dataset.semantics["period_basis"] == "capture"
    assert "capture_date_is_not_official_as_of" in dataset.assessment.qualifications
    assert {row["period_kind"] for row in dataset.rows} == {"capture"}
    assert {row["period"] for row in dataset.rows} == {CAPTURED.isoformat()}


def test_retained_history_preserves_both_captures_without_new_source_parsing(tmp_path):
    before = bank_evidence()[2]
    after = bank_evidence(date(2026, 11, 23))[2]
    history = roundtrip(tmp_path / "capture_history.json", (before, after))
    assert history == (before, after)
    assert [item.semantics["captured_on"] for item in history] == ["2026-11-22", "2026-11-23"]
    assert all(item.semantics["official_as_of"] == "2026-11-01" for item in history)


def test_alignment_requires_explicit_bindings_and_retains_native_identity():
    source = bank_evidence()[2]
    declaration = DOMAIN.series[BANK].commands["command.observations.align"]
    with pytest.raises(ValueError, match="mapping_incomplete"):
        call(BANK, "command.observations.align", {"dataset": source},
            settings=replace(declaration.settings, require_all=True))
    subjects = sorted({(row["subject_namespace"], row["subject"]) for row in source.rows})
    bindings = tuple((*key, "bank." + str(index)) for index, key in enumerate(subjects))
    result = call(BANK, "command.observations.align", {"dataset": source},
        settings=replace(declaration.settings, subjects=bindings, require_all=True))["dataset"]
    assert result.assessment.complete
    for row, native in zip(result.rows, source.rows):
        assert row["source_subject"] == native["subject"]
        assert row["subject_namespace"] == "canonical"
        assert row["dimensions"] == native["dimensions"]
        assert row["measure_kind"] == "count" and row["evidence_ref"] == native["evidence_ref"]


def test_same_period_revision_reports_exact_deltas_and_unmatched_coverage(tmp_path):
    before = bank_evidence()[2]
    changed = next(index for index, row in enumerate(before.rows) if row["value_status"] == "reported")
    rows = list(before.rows)
    original = rows[changed]
    rows[changed] = {**original, "value": original["value"] + 2, "raw_token": str(original["value"] + 2)}
    after = replace(before, rows=tuple(rows))
    comparison = compare(before, after)
    assert len(comparison["changes"]) == 1
    assert comparison["changes"][0]["delta"] == Decimal(2)
    assert comparison["changes"][0]["before"] == original
    assert compare(before, replace(after, rows=after.rows[:-1]))["changes"][-1]["kind"] == "removed"
    retained = roundtrip(tmp_path / "revision_evidence.json", comparison)
    assert retained == comparison


def test_prepared_view_survives_independently_and_uses_standard_rendering(tmp_path):
    dataset = bank_evidence()[2]
    view = view_prepare({"dataset": dataset}, {"filters": {}}, context())["view"]
    retained = roundtrip(tmp_path / "office_view.json", view)
    assert retained == view and retained.lineage[-1] == dataset.identity
    csv = product_render({"view": retained}, {"format": "csv"}, context())["product"]
    assert csv.media_type == "text/csv" and b"evidence_ref" in csv.data and b"reported" in csv.data
    assert product_render({"view": retained}, {"format": "json"}, context())["product"].data


def test_original_native_html_bytes_remain_available_without_conversion():
    original, tables, dataset = bank_evidence()
    assert original.data == HTML.read_bytes() == tables.material.data
    assert tables.material.media_type == "text/html"
    assert original.identity in dataset.lineage
    assert all(original.identity.sha256 in row["evidence_ref"] for row in dataset.rows)


def test_invalid_html_cannot_be_promoted_to_office_observations():
    physical = call(BANK, "command.document.decode", {"material": Material(b"invalid", "text/html", BANK)})["physical"]
    with pytest.raises(Exception, match="SOURCE_"):
        call(BANK, "command.table.extract", {"physical": physical})
