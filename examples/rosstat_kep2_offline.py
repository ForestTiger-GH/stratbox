"""Offline KEP2 route with separate original, physical, flake, dataset and view storage.

Run:
    python examples/rosstat_kep2_offline.py --source /path/2026-08.xlsx \
        --issue 2026-08 --output-root /path/rosstat-output

The explicit issue is publication identity. Observation periods are read from
reviewed worksheet headers and source year rows. No HTTP or Git operation runs.
"""
from argparse import ArgumentParser
from pathlib import Path

from stratbox.core.operations.source.originals import save_original
from stratbox.core.operations.source.original_definitions import SaveOriginalRequest,OriginalDestination
from stratbox.core.operations.materials.operations import save_artifact
from stratbox.core.operations.materials.definitions import SaveArtifactRequest,ArtifactDestination
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.storage.datasets.files import FileDatasetStore
from stratbox.core.storage.datasets.operations import write_snapshot,read_snapshot
from stratbox.core.storage.datasets.definitions import WriteSnapshotRequest,ReadSnapshotRequest
from stratbox.shared.evidence import SourcePayload,UsedInputReceipt
from stratbox.shared.materials import MaterialArtifact
from stratbox.shared.data.processing import DataContract,DataRole
from stratbox.shared.source_publications import SourceAssetIdentity
from stratbox.domains.rosstat.operations import handlers as rosstat
from stratbox.domains.rosstat.operations.contracts import (
    PhysicalRequest,WorkbookRequest,SnapshotRequest,FlakeRequest,IntegrateRequest,DatasetRequest,ViewRequest,
)
from stratbox.domains.rosstat.tables.contracts import Kep2Request


def required(result):
    if result.outcome!="succeeded":
        raise RuntimeError((result.outcome,tuple(item.code for item in result.diagnostics)))
    return result.value


def build(source: Path,issue: str,output_root: Path):
    output_root.mkdir(parents=True,exist_ok=True)
    files=LocalFileStore(str(output_root))
    datasets=FileDatasetStore(files,"datasets",provider_id="rosstat.example",scope_id="local")
    identity=SourceAssetIdentity("rosstat.short_term_indicators",issue,"main_workbook")
    payload=SourcePayload(source.read_bytes(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",identity.source_id)
    required(save_original(SaveOriginalRequest(payload,OriginalDestination("originals/"+issue+".xlsx")),store=files))

    def retained(snapshot):
        receipt=required(write_snapshot(WriteSnapshotRequest(snapshot),store=datasets))
        if receipt.reference is None:
            raise RuntimeError("dataset.confirmed_reference_required")
        restored=required(read_snapshot(ReadSnapshotRequest(receipt.reference),store=datasets))
        if restored.identity!=snapshot.identity:
            raise RuntimeError("dataset.replay_identity_mismatch")
        return restored

    workbook=required(rosstat.extract_workbook(PhysicalRequest(payload,identity.series_id,identity.issue_id,identity.asset_id)))
    workbook=required(rosstat.read_workbook(SnapshotRequest(retained(required(rosstat.workbook_snapshot(WorkbookRequest(workbook)))))))
    flake=required(rosstat.extract_kep2(Kep2Request(workbook)))
    required(rosstat.validate_flake(FlakeRequest(flake)))
    flake=required(rosstat.read_flake(SnapshotRequest(retained(required(rosstat.flake_snapshot(FlakeRequest(flake)))))))
    dataset=required(rosstat.integrate(IntegrateRequest((flake,),"rosstat.kep2.integrated",issue)))
    dataset=required(rosstat.read_dataset(SnapshotRequest(retained(required(rosstat.dataset_snapshot(DatasetRequest(dataset)))))))
    view=required(rosstat.prepare_kep2_monthly(DatasetRequest(dataset)))
    view=required(rosstat.read_view(SnapshotRequest(retained(required(rosstat.view_snapshot(ViewRequest(view)))))))
    rendered=rosstat.render_kep2_xlsx(ViewRequest(view))
    representation=required(rendered)
    artifact=MaterialArtifact(DataContract("rosstat.kep2.monthly.xlsx",1,DataRole.PRODUCTS),representation,
        (*view.batch.lineage,UsedInputReceipt("prepared_view",view.identity,"application/vnd.stratbox.dataset","inline")),
        identity.series_id,identity,rendered.computation)
    published=required(save_artifact(SaveArtifactRequest(artifact,ArtifactDestination("products/"+issue+"-monthly.xlsx")),store=files))
    return {"source_sha256":payload.identity.sha256,"physical_sheets":len(workbook.sheets),
        "selected_source_values":len(flake.values),"monthly_values":len(view.batch.observations),
        "artifact":published.artifact}


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--issue",required=True)
    parser.add_argument("--output-root",type=Path,required=True)
    args=parser.parse_args()
    print(build(args.source,args.issue,args.output_root))


if __name__=="__main__":
    main()
