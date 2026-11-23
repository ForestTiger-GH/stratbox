"""Economic admission, exact source context and independent calculation replay."""
from dataclasses import replace
from datetime import date
from decimal import Decimal

from stratbox.domains import minfin
from stratbox.domains.minfin.tables.contracts import FlakeColumn, FlakeRow
from stratbox.shared.data.observations import MetricRef, SubjectRef
from stratbox.shared.identity import ByteIdentity


def ok(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def flake():
    return minfin.FlakeTable("minfin.fedbud", "minfin.fedbud.annex3.monthly", ByteIdentity.of(b"exact original"),
        "Budget", "monthly", "ytd", (FlakeColumn(3, "Oct 2025", "2025-10"), FlakeColumn(4, "Oct 2026", "2026-10")),
        (FlakeRow(4, "1", "Доходы, всего", ("100", "110"), "RUB", "1000000000", "ytd"),
         FlakeRow(5, "2", "Расходы, всего", ("120", "135"), "RUB", "1000000000", "ytd"),
         FlakeRow(6, "3", "Дефицит (-)/Профицит (+)", ("-20", "-25"), "RUB", "1000000000", "ytd")),
        "minfin.flake.budget.v2", "billion_rub", minfin.PublicationContext(
            "minfin.fedbud.annex3.monthly", "issue-42", "annex-3", date(2026, 11, 12), date(2026, 11, 13),
            "42", "https://minfin.gov.ru/example"))


def test_context_and_per_row_units_survive_both_codecs_and_integrate_to_ytd_intervals():
    value = flake()
    serialized = ok(minfin.serialize_source_flake(minfin.SerializeFlakeRequest(value)))
    assert ok(minfin.read_source_flake(minfin.ReadFlakeRequest(serialized))) == value
    retained = ok(minfin.build_flake_snapshot(minfin.FlakeSnapshotRequest(value, "minfin.flakes", "edition-42")))
    restored = ok(minfin.read_flake_snapshot(minfin.ReadFlakeSnapshotRequest(retained)))
    assert restored == value
    batch = ok(minfin.integrate(minfin.IntegrateRequest(restored, "minfin.observations", "edition-42")))
    assert len(batch.observations) == 6
    first = batch.observations[0]
    assert first.period.start == date(2025, 1, 1)
    assert first.period.end == date(2025, 10, 31)
    assert first.metric.scale == Decimal("1e9")
    assert first.metric.unit == "RUB"
    assert "issue=issue-42&asset=annex-3" in first.evidence_ref
    saved = ok(minfin.build_observation_snapshot(minfin.ObservationSnapshotRequest(batch)))
    assert ok(minfin.read_observations(minfin.ReadObservationsRequest(saved))) == batch


def test_headline_unit_admission_and_durable_result_view_replay():
    value = flake()
    assert minfin.calculate_headlines(minfin.SummaryRequest(replace(value, unit_hint="percent"))).outcome == "failed"
    wrong = replace(value.rows[0], unit="USD")
    assert minfin.calculate_headlines(minfin.SummaryRequest(replace(value, rows=(wrong, *value.rows[1:])))).outcome == "failed"
    summary = ok(minfin.calculate_headlines(minfin.SummaryRequest(value)))
    retained = ok(minfin.build_summary_snapshot(minfin.SummarySnapshotRequest(summary, "minfin.results", "edition-42")))
    replay = ok(minfin.read_summary(minfin.ReadSummaryRequest(retained)))
    assert replay == summary
    assert replay.publication == value.publication
    assert replay.calculation_profile == "minfin.budget_headlines"
    assert replay.flake_identity is not None
    view = ok(minfin.prepare_view(minfin.PrepareHeadlineViewRequest(replay, "budget-headlines")))
    snapshot = ok(minfin.build_view_snapshot(minfin.ViewSnapshotRequest(view)))
    cold = ok(minfin.read_view(minfin.ReadViewRequest(snapshot)))
    assert cold == view
    assert b"budget.revenue" in ok(minfin.render_view(minfin.RenderViewRequest(cold, "json"))).data


def test_explicit_mixed_row_mapping_does_not_invent_stocks_or_zero_values():
    value = replace(flake(), family_id="minfin.nwf", source_id="minfin.nwf.flows", publication=None,
        value_basis="stock", unit_hint="mixed", method_version="minfin.flake.nwf.v2",
        rows=(FlakeRow(8, "9", "Caller identified flow", ("-", "0"), "USD", "1", "period_flow"),))
    bindings = (minfin.RowBinding("9", MetricRef("nwf.explicit_flow", "USD", "flow", "supplied.v1", Decimal(1)),
        SubjectRef("geography", "RU"), "explicit_fund_perimeter", "period_flow"),)
    batch = ok(minfin.integrate(minfin.IntegrateRequest(value, "minfin.explicit", "release", bindings)))
    assert batch.observations[0].value_status == "dash"
    assert batch.observations[0].value is None
    assert batch.observations[1].value == Decimal(0)
    assert batch.observations[1].period.start == date(2026, 10, 1)
    assert batch.observations[1].metric.quantity_kind == "flow"


def test_ordered_document_and_publisher_context_survive_cold_replay():
    from io import BytesIO
    from docx import Document
    from stratbox.shared.evidence import SourcePayload
    document = Document()
    document.add_paragraph("Before table")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Value"
    table.cell(0, 1).text = "10"
    document.add_paragraph("After table")
    stream = BytesIO()
    document.save(stream)
    publication = minfin.PublicationContext("minfin.nwf.volume", "issue-5", "main", date(2026, 5, 1),
        date(2026, 5, 2), "source-document-5", "https://minfin.gov.ru/example")
    payload = SourcePayload(stream.getvalue(), source_id=publication.series_id)
    value = ok(minfin.extract_document(minfin.ExtractDocumentRequest("minfin.nwf", payload, publication)))
    assert tuple(block.kind for block in value.document.blocks) == ("paragraph", "table", "paragraph")
    assert value.document.blocks[2].text == "After table"
    saved = ok(minfin.build_document_snapshot(minfin.DocumentSnapshotRequest(value)))
    restored = ok(minfin.read_document(minfin.ReadDocumentRequest(saved)))
    assert restored == value
    assert restored.publication.document_id == "source-document-5"
    assert b"After table" in ok(minfin.render_document(minfin.RenderDocumentRequest(restored))).data


def test_exact_numeric_lexeme_and_source_structure_survive_source_cell_codec():
    from io import BytesIO
    from zipfile import ZipFile, ZIP_DEFLATED
    from openpyxl import Workbook
    from stratbox.shared.evidence import SourcePayload
    book = Workbook()
    sheet = book.active
    sheet.title = "Cells"
    sheet["A1"] = 12345.5
    sheet["B1"] = "=A1*2"
    sheet.merge_cells("C2:D2")
    stream = BytesIO()
    book.save(stream)
    original = ZipFile(BytesIO(stream.getvalue()))
    changed = BytesIO()
    with ZipFile(changed, "w", ZIP_DEFLATED) as target:
        for entry in original.infolist():
            data = original.read(entry.filename)
            if entry.filename == "xl/worksheets/sheet1.xml":
                data = data.replace(b"12345.5", b"12345.50000000000000000000000001")
            target.writestr(entry, data)
    publication = flake().publication
    value = ok(minfin.extract(minfin.ExtractRequest("minfin.fedbud",
        SourcePayload(changed.getvalue(), source_id=publication.series_id), "xlsx", publication=publication)))
    numeric = value.sheets[0].cells[0]
    assert numeric.value == "12345.50000000000000000000000001"
    assert numeric.raw_token == numeric.value
    assert value.sheets[0].merged_ranges == ("C2:D2",)
    encoded = ok(minfin.serialize_extract(minfin.SerializeRequest(value)))
    assert ok(minfin.read_representation(minfin.ReadRepresentationRequest(encoded))) == value


def test_source_catalog_declares_table_and_document_applicability():
    from stratbox.domains.minfin.operations.source_catalog import source_cards
    cards = source_cards()
    assert len(cards) == 13
    assert len([card for card in cards if any(op.operation_id == "minfin.integrate" for op in card.operations)]) == 10
    document = next(card for card in cards if card.series_id == "minfin.nwf.veb_deposits")
    assert document.formats == ("doc",)
    assert all(op.operation_id != "minfin.extract_document" for op in document.operations)
    assert any(op.operation_id == "source.save_original" for op in document.operations)


def test_ratio_mapping_requires_explicit_point_or_interval_periods():
    from stratbox.shared.data.observations import PeriodRef
    value = replace(flake(), family_id="minfin.nwf", source_id="minfin.nwf.flows", publication=None,
        value_basis="stock", unit_hint="mixed", method_version="minfin.flake.nwf.v2",
        rows=(FlakeRow(8, "9", "Explicit ratio", ("10", "20"), "percent", "1", "ratio"),))
    binding = minfin.RowBinding("9", MetricRef("nwf.explicit_ratio", "percent", "ratio", "supplied.v1", Decimal(1)),
        SubjectRef("geography", "RU"), "explicit_population", "ratio")
    denied = minfin.integrate(minfin.IntegrateRequest(value, "minfin.explicit", "release", (binding,)))
    assert denied.outcome == "failed"
    assert denied.diagnostics[0].code == "minfin.integration.explicit_periods_required"
    binding = replace(binding, periods=(("2025-10", PeriodRef("as_of", as_of=date(2025, 10, 31))),
                                        ("2026-10", PeriodRef("as_of", as_of=date(2026, 10, 31)))))
    result = ok(minfin.integrate(minfin.IntegrateRequest(value, "minfin.explicit", "release", (binding,))))
    assert all(item.period.kind == "as_of" for item in result.observations)


def test_domain_profile_admission_keeps_period_basis_and_source_release_pairs():
    from stratbox.domains.minfin.profiles import admit
    from stratbox.shared.data.sources import SourceInstance
    from stratbox.shared.data.processing import DataContract
    value = flake()
    instance = SourceInstance(value.source_id, DataContract("minfin.flake", 2),
        group_id="fiscal_statistics", issue_id=value.publication.issue_id)
    assert admit(None, instance, value).state == "admitted"
    assert admit(None, instance, replace(value, frequency="annual")).state == "rejected"
    batch = ok(minfin.integrate(minfin.IntegrateRequest(value, "caller.dataset", "caller.version")))
    use, = batch.source_uses
    assert (use.coordinate.source_id, use.coordinate.issue_id, use.coordinate.asset_id) == (
        value.source_id, "issue-42", "annex-3")
    assert use.coordinate.source_group_id == "fiscal_statistics"
