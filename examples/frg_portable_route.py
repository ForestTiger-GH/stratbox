"""Run a byte-bound Frank RG route on an explicitly synthetic workbook.

This fixture is not evidence of any supplier layout. Actual workbooks require
caller-reviewed cell bindings. Requires the excel extra; performs no effects.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from stratbox.domains import frank_rg as frg
from stratbox.shared.data.observations import MetricRef, PeriodRef, SubjectRef
from stratbox.shared.evidence import SourcePayload


def admitted(result):
    if result.outcome != "succeeded":
        raise RuntimeError(tuple(item.code for item in result.diagnostics))
    return result.value


def main():
    source_id = "frg.express.portfolios"
    book = Workbook()
    sheet = book.active
    sheet.title = "Synthetic layout"
    sheet.append(("Subject", "Amount"))
    sheet.append(("Synthetic bank", "100.1234567890123456789012345"))
    stream = BytesIO()
    book.save(stream)
    original = admitted(frg.capture(frg.CaptureRequest(source_id, frg.ReportPeriod(date(2026, 5, 1)),
        SourcePayload(stream.getvalue()), "xlsx")))
    physical = admitted(frg.extract(frg.ExtractRequest(original)))
    retained = admitted(frg.build_extract_snapshot(frg.ExtractSnapshotRequest(physical)))
    physical = admitted(frg.read_extract(frg.ReadExtractRequest(retained)))
    profile = frg.SemanticProfile(source_id, "synthetic.supplied_profile.v1", 1, original.payload.identity, (
        frg.CellBinding("Synthetic layout", 2, 2, SubjectRef("bank", "synthetic-bank"),
            MetricRef("synthetic.stock", "RUB", "stock", "synthetic.v1", Decimal(1)),
            PeriodRef("as_of", as_of=date(2026, 4, 30)), "synthetic_reporting_population"),
    ))
    flake = admitted(frg.build_flake(frg.BuildFlakeRequest(physical, profile)))
    flake_snapshot = admitted(frg.build_flake_snapshot(frg.FlakeSnapshotRequest(flake)))
    restored = admitted(frg.read_flake(frg.ReadFlakeRequest(flake_snapshot)))
    integrated = admitted(frg.integrate(frg.IntegrateRequest(restored, "frg.synthetic.observations", "synthetic-edition")))
    snapshot = admitted(frg.build_observation_snapshot(frg.ObservationSnapshotRequest(integrated)))
    integrated = admitted(frg.read_observations(frg.ReadObservationsRequest(snapshot)))
    view = admitted(frg.prepare_view(frg.PrepareViewRequest(integrated, "synthetic-view")))
    view_snapshot = admitted(frg.build_view_snapshot(frg.ViewSnapshotRequest(view)))
    view = admitted(frg.read_view(frg.ReadViewRequest(view_snapshot)))
    rendered = admitted(frg.render_view(frg.RenderViewRequest(view, "json")))
    print(f"Synthetic supplied-profile route: {len(integrated.observations)} observations; {len(rendered.data)} rendered bytes.")
    print(f"Independent snapshot identities: {retained.identity.sha256}, {flake_snapshot.identity.sha256}, {view_snapshot.identity.sha256}")


if __name__ == "__main__":
    main()
