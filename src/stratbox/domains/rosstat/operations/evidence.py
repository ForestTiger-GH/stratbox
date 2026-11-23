"""Exact material boundaries, complete snapshot budgets and computation receipts."""
from dataclasses import fields,is_dataclass
from datetime import date,datetime,time,timedelta
from decimal import Decimal

from stratbox.shared.data.documents import DocumentExtract,document_snapshot
from stratbox.shared.data.workbooks import WorkbookExtract,workbook_snapshot
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.data.views import ObservationView,view_snapshot
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import SourcePayload,UsedInputReceipt
from stratbox.shared.identity import ByteIdentity,canonical_manifest_bytes
from stratbox.shared.reference.geography.editions import TerritoryEdition,territory_snapshot
from ..tables.contracts import RosstatSourceFlake
from ..tables.snapshots import flake_snapshot
from ..integration.datasets import RosstatDataset,dataset_snapshot
from ..publications.archives import RegionalMember

_MEDIA="application/vnd.stratbox.dataset+json"


def plain(value):
    if value is None or type(value) in {str,bool,int}:
        return value
    if isinstance(value,SourcePayload):
        return {"type":"source_payload","identity":plain(value.identity),"media_type":value.media_type,
            "source_id":value.source_id,"charset":value.charset}
    if isinstance(value,TerritoryEdition):
        return {"type":"territory_edition","reference_id":value.reference_id,"edition_id":value.edition_id,"identity":plain(value.identity)}
    if isinstance(value,Decimal):
        return {"type":"decimal","literal":str(value)}
    if isinstance(value,(date,datetime,time)):
        return {"type":type(value).__name__,"literal":value.isoformat()}
    if isinstance(value,timedelta):
        return {"type":"duration","days":value.days,"seconds":value.seconds,"microseconds":value.microseconds}
    if isinstance(value,float):
        return {"type":"float64","literal":value.hex()}
    if isinstance(value,bytes):
        return {"type":"bytes","identity":plain(ByteIdentity.of(value))}
    if isinstance(value,(tuple,list)):
        return tuple(plain(item) for item in value)
    if isinstance(value,(set,frozenset)):
        return tuple(sorted((plain(item) for item in value),key=repr))
    if isinstance(value,dict):
        return {str(key):plain(item) for key,item in value.items()}
    if is_dataclass(value):
        return {field.name:plain(getattr(value,field.name)) for field in fields(value)}
    if isinstance(value,str):
        return str(value)
    raise ValueError("rosstat.evidence_value_unsupported")


def snapshot_of(value,invocation):
    cache=getattr(invocation,"_rosstat_snapshots",None)
    if cache is None:
        cache={}
        invocation._rosstat_snapshots=cache
    if id(value) in cache:
        return cache[id(value)]
    if isinstance(value,DatasetSnapshot):
        snapshot=value
    elif isinstance(value,WorkbookExtract):
        invocation.budget.check("cells",sum(len(sheet.cells) for sheet in value.sheets))
        snapshot=workbook_snapshot(value)
    elif isinstance(value,DocumentExtract):
        invocation.budget.check("objects",len(value.blocks))
        snapshot=document_snapshot(value)
    elif isinstance(value,RosstatSourceFlake):
        invocation.budget.check("cells",len(value.values))
        snapshot=flake_snapshot(value)
    elif isinstance(value,RosstatDataset):
        invocation.budget.check("cells",len(value.batch.observations))
        snapshot=dataset_snapshot(value)
    elif isinstance(value,ObservationView):
        invocation.budget.check("cells",len(value.batch.observations))
        snapshot=view_snapshot(value)
    elif isinstance(value,ObservationBatch):
        invocation.budget.check("cells",len(value.observations))
        snapshot=observation_snapshot(value)
    elif isinstance(value,TerritoryEdition):
        snapshot=territory_snapshot(value)
    else:
        return None
    cache[id(value)]=snapshot
    return snapshot


def snapshot_size(snapshot):
    return snapshot.identity.size+sum(table.identity.size for _,table in snapshot.tables)


def _cells(snapshot):
    return sum(len(table.rows)*max(1,len(table.schema.columns)) for _,table in snapshot.tables)


def use_value(value,invocation,role):
    invocation.check_cancelled()
    if isinstance(value,tuple):
        for index,item in enumerate(value):
            use_value(item,invocation,f"{role}.{index}")
        return
    if isinstance(value,SourcePayload):
        invocation.budget.charge("input_bytes",value.identity.size)
        invocation.use(UsedInputReceipt.for_payload(value,role))
        return
    snapshot=snapshot_of(value,invocation)
    if snapshot is not None:
        invocation.budget.charge("input_bytes",snapshot_size(snapshot))
        invocation.budget.charge("cells",_cells(snapshot))
        invocation.use(UsedInputReceipt(role,snapshot.identity,_MEDIA,"inline",snapshot.manifest.dataset_id,version=snapshot.identity))
        return
    encoded=canonical_manifest_bytes({"type":type(value).__name__,"value":plain(value)})
    identity=ByteIdentity.of(encoded)
    invocation.budget.charge("input_bytes",identity.size)
    invocation.use(UsedInputReceipt(role,identity,"application/json","inline"))


def record_value(value,request,definition,invocation):
    invocation.check_cancelled()
    snapshot=snapshot_of(value,invocation)
    if snapshot is not None:
        for name,table in snapshot.tables:
            invocation.account_output(table.identity,key="component:"+name)
        invocation.account_output(snapshot.identity,key="manifest")
        invocation.budget.charge("cells",_cells(snapshot))
        identity=snapshot.identity
    elif isinstance(value,Representation):
        identity=value.identity
        invocation.account_output(identity)
    else:
        if isinstance(value,tuple):
            for index,item in enumerate(value):
                if isinstance(item,RegionalMember):
                    invocation.account_output(item.payload.identity,key=f"member.{index}")
        identity=ByteIdentity.of(canonical_manifest_bytes({"operation":definition.operation_id,"value":plain(value)}))
        invocation.account_output(identity)
    parameters={name:plain(getattr(request,name)) for name in definition.processing.parameters}
    invocation.record(identity,parameters=parameters)
