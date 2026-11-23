"""Exact material boundaries, complete snapshot budgets and computation receipts."""
from stratbox.core.execution import values

from stratbox.shared.data.documents import DocumentExtract,document_snapshot
from stratbox.shared.data.workbooks import WorkbookExtract,workbook_snapshot
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.data.views import ObservationView,view_snapshot
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.reference.geography.editions import TerritoryEdition,territory_snapshot
from ..tables.contracts import RosstatSourceFlake
from ..tables.snapshots import flake_snapshot
from ..integration.datasets import RosstatDataset,dataset_snapshot
from ..publications.archives import RegionalMember


def _snapshot(value,invocation):
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
    return snapshot


def snapshot_of(value, invocation):
    return values.snapshot_of(value, invocation, snapshot_factory=_snapshot)


def use_value(value, invocation, role):
    return values.use_value(value, invocation, role, snapshot_factory=_snapshot)


def record_value(value, request, definition, invocation):
    if isinstance(value, tuple):
        for index, item in enumerate(value):
            if isinstance(item, RegionalMember):
                invocation.account_output(item.payload.identity, key=f"member.{index}")
    return values.record_value(value, request, definition, invocation, snapshot_factory=_snapshot)
