"""Independent source semantics, explicit reference mapping and presentation choices."""
from dataclasses import replace
from datetime import date
from io import BytesIO

import pytest
from openpyxl import load_workbook

from stratbox.domains.cbr.common.contracts import MappingRules, SubjectBinding
from stratbox.domains.cbr.methods.actions import observations, publications
from stratbox.domains.cbr.products.specifications import ESCROW_CONTENT
from stratbox.shared.data.values import Assessment

from .test_replay import SERIES, context, decoded, encoded, history, prepared, publication, rendered, source


def test_product_style_changes_neither_extracted_nor_interpreted_identity():
    _, table, dataset = source(publication(extra=False))
    table_identity, dataset_identity = encoded(table).identity, dataset.identity
    before = prepared(dataset)
    customized = replace(ESCROW_CONTENT, sheets=tuple(replace(item, name=f"Table_{i}",
        title=f"Published metric {i}", number_format="0.0000") for i, item in enumerate(ESCROW_CONTENT.sheets, 1)))
    after = prepared(dataset, customized)
    assert encoded(before).identity != encoded(after).identity
    assert encoded(table).identity == table_identity and dataset.identity == dataset_identity
    book = load_workbook(BytesIO(rendered(after).data))
    assert book.sheetnames[0] == "Table_1"
    assert book["Table_1"]["B5"].number_format == "0.0000"
    book.close()


def test_history_uses_the_same_rows_as_independent_source_commands():
    requests = (publication(), publication(period="01072026", region="New region"))
    composed = history(*requests)
    independent = tuple(row for request in requests for row in source(request)[2].rows)
    assert composed.rows == independent
    assert len(composed.source_uses) == 2
    assert {row["period"] for row in composed.rows} == {"2026-06-01", "2026-07-01"}


def test_prepared_product_replays_custom_style_without_source_or_calculation(monkeypatch):
    dataset = history(publication(extra=False), publication(period="01072026", extra=False))
    settings = replace(ESCROW_CONTENT, sheets=tuple(replace(item, name=f"View_{i}")
        for i, item in enumerate(ESCROW_CONTENT.sheets, 1)))
    view = prepared(dataset, settings)
    restored = decoded(encoded(view))
    assert restored.lineage == view.lineage
    def unexpected(*args, **kwargs):
        raise AssertionError("A saved view must render independently")
    monkeypatch.setattr("stratbox.domains.cbr.methods.tables.project_finance.parser.parse_escrow_excel_bytes", unexpected)
    monkeypatch.setattr("stratbox.domains.cbr.methods.actions.escrow.interpret", unexpected)
    monkeypatch.setattr("stratbox.domains.cbr.products.actions.prepare", unexpected)
    assert rendered(restored) == rendered(view)


def test_revision_comparison_distinguishes_lexical_representation_and_facts():
    before = source(publication(amount="0012.2500"))[2]
    same = source(publication(amount="12.25"))[2]
    changed = source(publication(amount="13.25"))[2]
    settings = __import__("stratbox.domains.cbr.domain", fromlist=["DOMAIN"]).DOMAIN.series[SERIES].commands["command.source.assess"].settings
    assert publications.assess({"baseline": before, "evidence": same}, settings, context())["assessment"].status == "representation_changed"
    assert publications.assess({"baseline": before, "evidence": changed}, settings, context())["assessment"].status == "facts_changed"
    later = source(publication(period="01072026"))[2]
    assert {row["period"] for row in later.rows} != {row["period"] for row in before.rows}


def test_source_geography_remains_local_until_explicit_dated_reference_mapping():
    dataset = history(publication())
    settings = MappingRules(SERIES)
    original = observations.align({"dataset": dataset}, settings, context())["dataset"]
    assert any(row["subject_namespace"] == "cbr.published_territory" and row["subject"] == "Example region" for row in original.rows)
    money = next(row for row in original.rows if row["metric"] == "escrow_balance_mln_rub")
    assert money["unit"] == "RUB" and money["scale"] == 1_000_000
    assert {"blank", "dash"} <= {row["value_status"] for row in original.rows}
    cumulative = next(row for row in original.rows if row["metric"] == "revealed_escrow_amount_mln_rub")
    assert cumulative["measure_kind"] is None
    assert dict(cumulative["dimensions"])["source_period_basis"] == "cumulative_start_unspecified"
    binding = SubjectBinding("cbr.published_territory", "Example region", "reference.geography", "example",
        "sha256:reference-content", date(2026, 1, 1), date(2026, 12, 31))
    mapped = observations.align({"dataset": dataset}, replace(settings, bindings=(binding,)), context())["dataset"]
    row = next(row for row in mapped.rows if row["subject"] == "example")
    assert row["subject_namespace"] == "reference.geography"
    assert row["source_subject"] == "Example region"
    assert mapped.identity != original.identity and mapped.source_uses == original.source_uses
    with pytest.raises(ValueError, match="mapping_ambiguous"):
        observations.align({"dataset": dataset}, replace(settings, bindings=(binding, binding)), context())
    expired = replace(binding, valid_until=date(2025, 12, 31))
    unmatched = observations.align({"dataset": dataset}, replace(settings, bindings=(expired,)), context())["dataset"]
    assert not any(row["subject"] == "example" for row in unmatched.rows)


def test_incomplete_history_retains_evidence_and_requires_explicit_presentation_choice():
    dataset = history(publication())
    partial = replace(dataset, assessment=Assessment("partial", ("one_publication_failed",),
        qualifications=frozenset({"selection_incomplete"})))
    retained = decoded(encoded(partial))
    assert retained.assessment == partial.assessment
    with pytest.raises(ValueError, match="history_incomplete"):
        prepared(retained)
    assert prepared(retained, require_complete_history=False)
