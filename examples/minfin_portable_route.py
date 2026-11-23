"""Run the Minfin data route offline on a clearly synthetic budget fixture.

Requires the excel extra. No network, file mutation or storage provider is used.
The same generated snapshots can be passed to dataset.write_snapshot.
"""
from datetime import date
from io import BytesIO

from openpyxl import Workbook
from stratbox.domains import minfin
from stratbox.shared.evidence import SourcePayload


def admitted(result):
    if result.outcome != "succeeded":
        raise RuntimeError(tuple(item.code for item in result.diagnostics))
    return result.value


def main():
    source_id = "minfin.fedbud.annex3.monthly"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Synthetic budget"
    for row in (
        ("Code", "Indicator", "2025-10", "2026-10"),
        (1, "Доходы, всего", "100", "110"),
        (2, "Расходы, всего", "120", "135"),
        (3, "Дефицит (-)/Профицит (+)", "-20", "-25"),
    ):
        sheet.append(row)
    stream = BytesIO()
    workbook.save(stream)
    publication = minfin.PublicationContext(source_id, "synthetic-2026-10", "annex3_monthly", date(2026, 11, 1))
    physical = admitted(minfin.extract(minfin.ExtractRequest("minfin.fedbud",
        SourcePayload(stream.getvalue(), source_id=source_id), "xlsx", publication=publication)))
    flake = admitted(minfin.build_source_flake(minfin.BuildFlakeRequest(physical, source_id)))
    retained = admitted(minfin.build_flake_snapshot(minfin.FlakeSnapshotRequest(flake, source_id, "synthetic-edition")))
    restored = admitted(minfin.read_flake_snapshot(minfin.ReadFlakeSnapshotRequest(retained)))
    observations = admitted(minfin.integrate(minfin.IntegrateRequest(restored, "minfin.synthetic.observations", "synthetic-edition")))
    summary = admitted(minfin.calculate_headlines(minfin.SummaryRequest(restored)))
    calculation = admitted(minfin.build_summary_snapshot(minfin.SummarySnapshotRequest(summary, "minfin.synthetic.headlines", "synthetic-edition")))
    replayed = admitted(minfin.read_summary(minfin.ReadSummaryRequest(calculation)))
    view = admitted(minfin.prepare_view(minfin.PrepareHeadlineViewRequest(replayed, "synthetic-headlines")))
    view_snapshot = admitted(minfin.build_view_snapshot(minfin.ViewSnapshotRequest(view)))
    cold_view = admitted(minfin.read_view(minfin.ReadViewRequest(view_snapshot)))
    rendered = admitted(minfin.render_view(minfin.RenderViewRequest(cold_view, "json")))
    print(f"Synthetic route: {len(observations.observations)} observations; {len(summary.metrics)} headlines; {len(rendered.data)} rendered bytes.")
    print(f"Independent snapshot identities: {retained.identity.sha256}, {calculation.identity.sha256}, {view_snapshot.identity.sha256}")


if __name__ == "__main__":
    main()
