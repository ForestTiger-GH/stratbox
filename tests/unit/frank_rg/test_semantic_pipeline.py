"""Synthetic layouts exercise supplied-profile boundaries, never supplier layout claims."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import Workbook

from stratbox.domains import frank_rg as frg
from stratbox.shared.data.observations import MetricRef, PeriodRef, SubjectRef
from stratbox.shared.evidence import SourcePayload


def ok(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def workbook(value="123.456789012345678901234567890"):
    book = Workbook()
    sheet = book.active
    sheet.title = "Supplied layout"
    sheet.append(("Subject", "Reported amount"))
    sheet.append(("Fixture bank", value))
    sheet.append(("Other bank", "-"))
    sheet.merge_cells("D1:E1")
    stream = BytesIO()
    book.save(stream)
    return stream.getvalue()


def report(source_id, value="123.456789012345678901234567890"):
    period = frg.ReportPeriod(date(2026, 5, 1), 1 if frg.source(source_id).periodicity == "month_week" else None)
    return ok(frg.capture(frg.CaptureRequest(source_id, period, SourcePayload(workbook(value)), "xlsx")))


def profile(extract):
    return frg.SemanticProfile(extract.series_id, "fixture.explicit.v1", 1, extract.source_identity, (
        frg.CellBinding("Supplied layout", 2, 2, SubjectRef("bank", "fixture"),
            MetricRef("fixture.amount", "RUB", "stock", "fixture.v1", Decimal(1)),
            PeriodRef("as_of", as_of=date(2026, 4, 30)), "fixture_bank_population"),
        frg.CellBinding("Supplied layout", 3, 2, SubjectRef("bank", "other"),
            MetricRef("fixture.amount", "RUB", "stock", "fixture.v1", Decimal(1)),
            PeriodRef("as_of", as_of=date(2026, 4, 30)), "fixture_bank_population"),
    ))


@pytest.mark.parametrize("source_id", frg.all_sources())
def test_every_series_has_physical_route_and_byte_bound_semantic_replay(source_id):
    captured = report(source_id)
    extracted = ok(frg.extract(frg.ExtractRequest(captured)))
    assert extracted.series_id == source_id
    assert extracted.issue_id == captured.period.issue_id
    assert extracted.sheets[0].merged_ranges == ("D1:E1",)
    assert ok(frg.validate(frg.ValidateExtractRequest(extracted))).cells >= 6
    assert b'"kind":"cell"' in ok(frg.readable(frg.ReadableRequest(extracted))).data
    extract_snapshot = ok(frg.build_extract_snapshot(frg.ExtractSnapshotRequest(extracted)))
    assert ok(frg.read_extract(frg.ReadExtractRequest(extract_snapshot))) == extracted
    flake = ok(frg.build_flake(frg.BuildFlakeRequest(extracted, profile(extracted))))
    assert flake.batch.observations[0].value == Decimal("123.456789012345678901234567890")
    assert flake.batch.observations[1].value is None
    assert flake.batch.observations[1].value_status == "dash"
    assert flake.batch.observations[0].period.as_of == date(2026, 4, 30)
    saved = ok(frg.build_flake_snapshot(frg.FlakeSnapshotRequest(flake)))
    assert ok(frg.read_flake(frg.ReadFlakeRequest(saved))) == flake
    batch = ok(frg.integrate(frg.IntegrateRequest(flake, source_id + ".analysis", "edition-1")))
    snapshot = ok(frg.build_observation_snapshot(frg.ObservationSnapshotRequest(batch)))
    assert ok(frg.read_observations(frg.ReadObservationsRequest(snapshot))) == batch
    view = ok(frg.prepare_view(frg.PrepareViewRequest(batch, "fixture-view")))
    retained = ok(frg.build_view_snapshot(frg.ViewSnapshotRequest(view)))
    replayed = ok(frg.read_view(frg.ReadViewRequest(retained)))
    assert replayed == view
    assert b"123.456789012345678901234567890" in ok(frg.render_view(frg.RenderViewRequest(replayed))).data
    availability = frg.profile_availability(source_id)
    assert availability.semantic_state == "supplied_profile_required"
    assert availability.reviewed_profile_ids == ()


def test_profile_cannot_be_reused_for_different_bytes_or_incomplete_semantics():
    original = ok(frg.extract(frg.ExtractRequest(report("frg.express.issuance"))))
    changed = ok(frg.extract(frg.ExtractRequest(report("frg.express.issuance", "10"))))
    denied = frg.build_flake(frg.BuildFlakeRequest(changed, profile(original)))
    assert denied.outcome == "failed"
    supplied = profile(original)
    binding = replace(supplied.bindings[0], metric=replace(supplied.bindings[0].metric, scale=None))
    denied = frg.build_flake(frg.BuildFlakeRequest(original, replace(supplied, bindings=(binding,))))
    assert denied.outcome == "failed"
    assert denied.diagnostics[0].code == "frg.profile.semantics_required"


def test_align_history_revision_calculation_and_missing_status_are_independent():
    batches = []
    extracts = []
    for index, value in enumerate(("1.000000000000000000000000000001", "2.000000000000000000000000000002")):
        extracted = ok(frg.extract(frg.ExtractRequest(report("frg.express.issuance", value))))
        extracts.append(extracted)
        flake = ok(frg.build_flake(frg.BuildFlakeRequest(extracted, profile(extracted))))
        batches.append(ok(frg.integrate(frg.IntegrateRequest(flake, "frg.fixture", f"edition-{index}"))))
    physical = ok(frg.compare(frg.CompareExtractRequest(*extracts)))
    assert len(physical.cells) == 1
    history = ok(frg.build_history(frg.HistoryRequest(tuple(batches), "frg.fixture.history", "all")))
    assert len(history.observations) == 4
    assert {dict(x.dimensions)["publication_release"] for x in history.observations} == {"edition-0", "edition-1"}
    collision = frg.align(frg.AlignRequest(tuple(batches), "frg.fixture", "ambiguous"))
    assert collision.outcome == "failed"
    assert collision.diagnostics[0].code == "frg.integration.duplicate_semantic_key"
    result = ok(frg.calculate(frg.CalculateRequest(*batches, "frg.fixture.revisions", "r1")))
    assert result.observations[0].value == Decimal("1.000000000000000000000000000001")
    assert result.observations[1].value is None
    assert result.observations[1].value_status == "not_applicable"
    saved = ok(frg.build_observation_snapshot(frg.ObservationSnapshotRequest(result)))
    assert ok(frg.read_observations(frg.ReadObservationsRequest(saved))) == result


def test_domain_admission_requires_real_byte_bound_profile_and_preserves_coordinates():
    from stratbox.domains.frank_rg.profiles import admit
    from stratbox.shared.data.sources import SourceInstance
    from stratbox.shared.data.processing import DataContract
    extracted = ok(frg.extract(frg.ExtractRequest(report("frg.express.issuance"))))
    instance = SourceInstance(extracted.series_id, DataContract("frg.semantic_flake"),
        group_id="reported_metrics", issue_id=extracted.issue_id, material_identity=extracted.source_identity)
    assert admit(None, instance, extracted).state == "conditional"
    flake = ok(frg.build_flake(frg.BuildFlakeRequest(extracted, profile(extracted))))
    assert admit(None, instance, flake).state == "admitted"
    assert admit(None, replace(instance, material_identity=SourcePayload(b"other").identity), flake).state == "rejected"
    batch = ok(frg.integrate(frg.IntegrateRequest(flake, "caller.dataset", "caller.version")))
    coordinate = batch.source_uses[0].coordinate
    assert (coordinate.source_id, coordinate.issue_id, coordinate.source_group_id) == (
        extracted.series_id, extracted.issue_id, "reported_metrics")
    restored = ok(frg.read_observations(frg.ReadObservationsRequest(
        ok(frg.build_observation_snapshot(frg.ObservationSnapshotRequest(batch))))))
    assert restored.source_uses == batch.source_uses
