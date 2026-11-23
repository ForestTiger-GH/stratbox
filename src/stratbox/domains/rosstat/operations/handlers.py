"""Thin operation boundary; family semantics live in their functional packages."""
from __future__ import annotations
from dataclasses import replace
import re

from stratbox.core.execution import Completion,OperationFailure,run
from stratbox.shared.evidence import SourcePayload,UsedInputReceipt
from stratbox.shared.source_publications import SourceAssetIdentity
from stratbox.shared.data.snapshots import DatasetSnapshot
from . import definitions as D


from .evidence import use_value,record_value,snapshot_of


def _execute(definition,request,action,context=None):
    def work(req,invocation):
        for port in definition.processing.inputs:
            use_value(getattr(req,port.path),invocation,port.name)
        for name in definition.processing.parameters:
            parameter=getattr(req,name)
            if name in {"profile","layout","evidence"}:
                use_value(parameter,invocation,name)
                edition=getattr(parameter,"territory_edition",None)
                if edition is not None:
                    use_value(edition,invocation,"territory_edition")
        invocation.stage(definition.operation_id)
        try:
            value=action(req,invocation)
            record_value(value,req,definition,invocation)
        except ValueError as error:
            code=str(error)
            if not re.fullmatch(r"[a-z][a-z0-9_.]+",code):
                code="rosstat.input_invalid"
            raise OperationFailure(code) from None
        invocation.check_cancelled()
        coverage=getattr(value,"coverage",None)
        if definition.partial_allowed and coverage is not None and coverage.status!="complete":
            return Completion(value,"partial","rosstat.source_scope_qualified")
        return value
    return run(definition,request,work,context=context)


def select(request,*,context=None):
    from ..publications.discovery.selection import select_assets
    return _execute(D.SELECT,request,lambda r,i:select_assets(r.index,issue_ids=r.issue_ids,
        asset_roles=r.asset_roles,policy=r.policy,max_assets=r.max_assets),context)


def plan_updates(request,*,context=None):
    from ..publications.discovery.selection import compare_publication_indices
    return _execute(D.PLAN_UPDATES,request,lambda r,i:compare_publication_indices(r.before,r.after),context)


def review_index(request,*,context=None):
    from ..publications.discovery.approval import approve_index
    return _execute(D.APPROVE_INDEX,request,lambda r,i:approve_index(r.index,r.evidence),context)


def _physical(request,invocation,kind):
    from ..publications.catalog import get_rosstat_source
    get_rosstat_source(request.series_id)
    identity=SourceAssetIdentity(request.series_id,request.issue_id,request.asset_id)
    if request.payload.source_id is not None and request.payload.source_id!=identity.source_id:
        raise ValueError("rosstat.physical_source_identity_mismatch")
    if (request.container_identity is None)!=(request.member is None):
        raise ValueError("rosstat.physical_member_lineage_required")
    if request.series_id=="rosstat.socioeconomic_regions" and request.container_identity is None:
        raise ValueError("rosstat.regional_member_lineage_required")
    if kind=="workbook":
        if request.series_id=="rosstat.socioeconomic_russia":
            raise ValueError("rosstat.family_document_required")
        from stratbox.core.formats.spreadsheets.extracts import extract_workbook
        value=extract_workbook(request.payload,series_id=request.series_id,issue_id=request.issue_id,asset_id=request.asset_id,
            budget=invocation.budget,checkpoint=invocation.check_cancelled)
    else:
        if request.series_id not in {"rosstat.socioeconomic_russia","rosstat.socioeconomic_regions"}:
            raise ValueError("rosstat.family_workbook_required")
        from stratbox.core.formats.documents import extract_document
        value=extract_document(request.payload,series_id=request.series_id,issue_id=request.issue_id,asset_id=request.asset_id,
            budget=invocation.budget,checkpoint=invocation.check_cancelled)
    if request.member is not None:
        receipt=UsedInputReceipt.for_payload(request.payload,"archive_member",container=request.container_identity,member=request.member)
        container=UsedInputReceipt("regional_archive",request.container_identity,"application/octet-stream","reference_only",request.payload.source_id)
        value=replace(value,lineage=(container,receipt))
        invocation.use(receipt)
        invocation.use(container)
    return value


def extract_workbook(request,*,context=None):
    return _execute(D.EXTRACT_WORKBOOK,request,lambda r,i:_physical(r,i,"workbook"),context)


def extract_document(request,*,context=None):
    return _execute(D.EXTRACT_DOCUMENT,request,lambda r,i:_physical(r,i,"document"),context)


def inspect_archive(request,*,rar_reader=None,context=None):
    from ..publications.archives import inspect_archive as inspect
    return _execute(D.INSPECT_ARCHIVE,request,lambda r,i:inspect(r.payload,limits=r.limits,rar_reader=rar_reader,budget=i.budget),context)


def extract_members(request,*,rar_reader=None,context=None):
    from ..publications.archives import acquire_members
    return _execute(D.EXTRACT_MEMBERS,request,lambda r,i:acquire_members(r.payload,r.inventory,r.names,
        limits=r.limits,rar_reader=rar_reader,budget=i.budget,checkpoint=i.check_cancelled),context)


def workbook_snapshot(request,*,context=None):
    from stratbox.shared.data.workbooks import workbook_snapshot as encode
    return _execute(D.WORKBOOK_SNAPSHOT,request,lambda r,i:snapshot_of(r.workbook,i),context)


def read_workbook(request,*,context=None):
    from stratbox.shared.data.workbooks import workbook_from_snapshot
    return _execute(D.READ_WORKBOOK,request,lambda r,i:workbook_from_snapshot(r.snapshot),context)


def readable_workbook(request,*,context=None):
    from stratbox.shared.data.workbooks import readable_workbook as render
    return _execute(D.READABLE_WORKBOOK,request,lambda r,i:render(r.workbook),context)


def compare_workbooks(request,*,context=None):
    from stratbox.shared.data.workbooks import compare_workbooks as compare
    return _execute(D.COMPARE_WORKBOOKS,request,lambda r,i:compare(r.before,r.after),context)


def document_snapshot(request,*,context=None):
    from stratbox.shared.data.documents import document_snapshot as encode
    return _execute(D.DOCUMENT_SNAPSHOT,request,lambda r,i:snapshot_of(r.document,i),context)


def read_document(request,*,context=None):
    from stratbox.shared.data.documents import document_from_snapshot
    return _execute(D.READ_DOCUMENT,request,lambda r,i:document_from_snapshot(r.snapshot),context)


def readable_document(request,*,context=None):
    from stratbox.shared.data.documents import readable_document as render
    return _execute(D.READABLE_DOCUMENT,request,lambda r,i:render(r.document),context)


def structure_document(request,*,context=None):
    from ..tables.documents import structure_document as structure
    return _execute(D.STRUCTURE_DOCUMENT,request,lambda r,i:structure(r.document,r.layout),context)


def extract_kep2(request,*,context=None):
    from ..tables.kep2 import extract_kep2 as extract
    return _execute(D.KEP2,request,lambda r,i:extract(r,budget=i.budget,checkpoint=i.check_cancelled),context)


def map_reviewed_cells(request,*,context=None):
    from ..tables.mapping import map_reviewed_cells as map_cells
    return _execute(D.MAP_CELLS,request,lambda r,i:map_cells(r.physical,r.profile),context)


def flake_snapshot(request,*,context=None):
    from ..tables.snapshots import flake_snapshot as encode
    return _execute(D.FLAKE_SNAPSHOT,request,lambda r,i:snapshot_of(r.flake,i),context)


def read_flake(request,*,context=None):
    from ..tables.snapshots import flake_from_snapshot
    return _execute(D.READ_FLAKE,request,lambda r,i:flake_from_snapshot(r.snapshot),context)


def readable_flake(request,*,context=None):
    from ..tables.representation import readable_flake as render
    return _execute(D.READABLE_FLAKE,request,lambda r,i:render(r.flake),context)


def integrate(request,*,context=None):
    from ..integration.datasets import integrate_flakes
    return _execute(D.INTEGRATE,request,lambda r,i:integrate_flakes(r.flakes,dataset_id=r.dataset_id,release_id=r.release_id),context)


def dataset_snapshot(request,*,context=None):
    from ..integration.datasets import dataset_snapshot as encode
    return _execute(D.DATASET_SNAPSHOT,request,lambda r,i:snapshot_of(r.dataset,i),context)


def read_dataset(request,*,context=None):
    from ..integration.datasets import dataset_from_snapshot
    return _execute(D.READ_DATASET,request,lambda r,i:dataset_from_snapshot(r.snapshot),context)


def compare_datasets(request,*,context=None):
    from ..analytics.indicators import compare_datasets as compare
    return _execute(D.COMPARE_DATASETS,request,lambda r,i:compare(r.before,r.after),context)


def derive_index_growth(request,*,context=None):
    from ..analytics.indicators import derive_index_growth as derive
    return _execute(D.DERIVE_GROWTH,request,lambda r,i:derive(r.dataset,release_id=r.release_id),context)


def prepare_view(request,*,context=None):
    from ..products.views import prepare_view as prepare
    return _execute(D.PREPARE_VIEW,request,lambda r,i:prepare(r.dataset,view_id=r.view_id,metric_ids=r.metric_ids),context)


def prepare_kep2_monthly(request,*,context=None):
    from ..products.views import prepare_kep2_monthly as prepare
    return _execute(D.KEP2_MONTHLY_VIEW,request,lambda r,i:prepare(r.dataset),context)


def view_snapshot(request,*,context=None):
    from stratbox.shared.data.views import view_snapshot as encode
    return _execute(D.VIEW_SNAPSHOT,request,lambda r,i:snapshot_of(r.view,i),context)


def read_view(request,*,context=None):
    from stratbox.shared.data.views import view_from_snapshot
    return _execute(D.READ_VIEW,request,lambda r,i:view_from_snapshot(r.snapshot),context)


def render_view(request,*,context=None):
    from stratbox.shared.data.views import render_observation_view
    return _execute(D.RENDER_VIEW,request,lambda r,i:render_observation_view(r.view,format=r.format),context)


def render_kep2_xlsx(request,*,context=None):
    from ..products.xlsx import render_kep2_xlsx as render
    return _execute(D.RENDER_KEP2_XLSX,request,lambda r,i:render(r.view),context)


def validate_flake(request,*,context=None):
    from ..tables.comparison import validate_flake as validate
    return _execute(D.VALIDATE_FLAKE,request,lambda r,i:validate(r.flake),context)


def compare_flakes(request,*,context=None):
    from ..tables.comparison import compare_flakes as compare
    return _execute(D.COMPARE_FLAKES,request,lambda r,i:compare(r.before,r.after),context)
