"""Offline workbook -> retained flake -> observations -> calculation -> view.

Run with PYTHONPATH=src and the excel extra installed. All values are synthetic;
independent temporary file providers demonstrate caller-selected destinations.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from openpyxl import Workbook

from stratbox.core.operations.materials.definitions import ArtifactDestination, SaveArtifactRequest
from stratbox.core.operations.materials.operations import artifact_from_output, save_artifact
from stratbox.core.storage.datasets import FileDatasetStore
from stratbox.core.storage.datasets.definitions import ReadSnapshotRequest, WriteSnapshotRequest
from stratbox.core.storage.datasets.operations import read_snapshot, write_snapshot
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains.cbr.operations.publications import IdentifyRequest, identify
from stratbox.domains.cbr.operations.statistics import contracts as C, handlers as statistics
from stratbox.domains.cbr.integration.statistics.contracts import RowBinding
from stratbox.shared.data.observations import MetricRef, PeriodRef, SubjectRef
from stratbox.shared.evidence import SourcePayload

SERIES = "cbr.monetary_statistics.monetary_agg"


def accepted(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def synthetic_workbook():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Денежные агрегаты"
    sheet.append(["Monetary levels, млрд руб.", date(2026, 1, 1), date(2026, 2, 1)])
    sheet.append(["M2", 100, 120])
    sheet.append(["Cash", 30, 36])
    out = BytesIO()
    workbook.save(out)
    return out.getvalue()


def main():
    with TemporaryDirectory() as directory:
        retained_root = str(Path(directory) / "retained")
        retained = LocalFileStore(retained_root)
        datasets = FileDatasetStore(retained, "datasets", provider_id="files", scope_id="demo")

        def retain_and_reopen(snapshot):
            reference = accepted(write_snapshot(WriteSnapshotRequest(snapshot), store=datasets)).reference
            # This adapter can equally be constructed in another process.
            fresh = FileDatasetStore(LocalFileStore(retained_root), "datasets", provider_id="files", scope_id="demo")
            return accepted(read_snapshot(ReadSnapshotRequest(reference), store=fresh))

        original = accepted(identify(IdentifyRequest(SERIES, "2026-11-23",
            SourcePayload(synthetic_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), "xlsx")))
        saved_original = accepted(save_artifact(SaveArtifactRequest(original.artifact,
            ArtifactDestination("originals/monetary.xlsx")), store=retained))
        assert saved_original.artifact.material.identity == original.payload.identity

        flake = accepted(statistics.extract(C.ExtractWorkbookRequest(original)))
        source_snapshot = accepted(statistics.build_flake_snapshot(C.FlakeRequest(flake)))
        reopened_flake = accepted(statistics.read_flake_snapshot(C.ReadSnapshotRequest(retain_and_reopen(source_snapshot))))
        assert reopened_flake == flake

        subject = SubjectRef("demo.geography", "russia")
        bindings = tuple(RowBinding(SERIES, "Денежные агрегаты", row,
            MetricRef(metric, "RUB", "stock", "demo.monetary.v1", Decimal(1_000_000_000)),
            subject, perimeter="demo.synthetic.monetary")
            for row, metric in ((2, "demo.m2"), (3, "demo.cash")))
        integrated = accepted(statistics.align(C.AlignStatisticsRequest((reopened_flake,),
            row_bindings=bindings, mapping_version="demo.mapping.v1", strict=True)))
        snapshot = accepted(statistics.build_dataset_snapshot(C.DatasetRequest(integrated)))
        reopened = accepted(statistics.read_dataset_snapshot(C.ReadSnapshotRequest(retain_and_reopen(snapshot))))
        assert reopened == integrated

        change = accepted(statistics.calculate_change(C.CalculateChangeRequest(reopened,
            PeriodRef("as_of", as_of=date(2026, 1, 1)), PeriodRef("as_of", as_of=date(2026, 2, 1)),
            method="growth_percent")))
        assert {item.value for item in change.batches[0].observations} == {Decimal(20)}
        share = accepted(statistics.calculate_share(C.CalculateShareRequest(reopened, "demo.cash", "demo.m2")))
        assert {item.value for item in share.batches[0].observations} == {Decimal(30)}

        view = accepted(statistics.build_view(C.BuildViewRequest(change, title="Synthetic monetary changes")))
        snapshot = accepted(statistics.build_view_snapshot(C.ViewRequest(view)))
        restored_view = accepted(statistics.read_view_snapshot(C.ReadSnapshotRequest(retain_and_reopen(snapshot))))
        rendered = statistics.render_view(C.RenderViewRequest(restored_view))
        accepted(rendered)
        artifact = artifact_from_output(rendered, "representation", series_id="demo.statistics")
        for name in ("output-a", "output-b"):
            output = LocalFileStore(str(Path(directory) / name))
            saved = accepted(save_artifact(SaveArtifactRequest(artifact,
                ArtifactDestination("products/changes.xlsx")), store=output))
            assert saved.artifact.material.identity == rendered.value.identity
            assert output.read_bytes("products/changes.xlsx") == rendered.value.data
        print("Verified original retention, independent flake/dataset/view replay, explicit calculations and two output stores.")


if __name__ == "__main__":
    main()
