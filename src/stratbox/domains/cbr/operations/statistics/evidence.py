"""Account complete logical values and bind exact inputs to each operation."""
from dataclasses import asdict, is_dataclass

from stratbox.core.operations.source.validation import use_payload
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.domains.cbr.publications.contracts import IdentifiedOriginal
from stratbox.domains.cbr.tables.statistics.contracts import WorkbookFlake
from stratbox.domains.cbr.tables.statistics.snapshots import flake_snapshot
from stratbox.domains.cbr.integration.statistics.contracts import StatisticsDataset
from stratbox.domains.cbr.integration.statistics.snapshots import dataset_snapshot
from stratbox.domains.cbr.products.statistics.views import StatisticsView, view_snapshot

_SNAPSHOT_MEDIA = "application/vnd.stratbox.dataset+json"


def _snapshot(value, invocation):
    # Check a lower bound before allocating a canonical tabular projection.
    if isinstance(value, WorkbookFlake):
        invocation.budget.check("cells", sum(len(sheet.cells) for sheet in value.sheets))
        return flake_snapshot(value)
    if isinstance(value, StatisticsDataset):
        invocation.budget.check("cells", sum(len(batch.observations) for batch in value.batches))
        return dataset_snapshot(value)
    if isinstance(value, StatisticsView):
        return view_snapshot(value)
    if isinstance(value, DatasetSnapshot):
        return value
    return None


def _cells(snapshot):
    return sum(len(table.rows) * max(1, len(table.schema.columns)) for _, table in snapshot.tables)


def use_value(value, invocation, role):
    invocation.check_cancelled()
    if isinstance(value, tuple):
        for index, item in enumerate(value):
            use_value(item, invocation, f"{role}.{index}")
        return
    if isinstance(value, IdentifiedOriginal):
        use_payload(value.payload, invocation, role=role, limit=256 * 1024**2)
        # The descriptor pins series/issue/asset context independently of bytes.
        invocation.use(UsedInputReceipt(role + ".context", value.artifact.identity,
            "application/vnd.stratbox.material+json", "inline", value.asset.series_id,
            version=value.artifact.identity))
        return
    snapshot = _snapshot(value, invocation)
    if snapshot is None:
        raise ValueError("cbr.statistics.input_invalid")
    invocation.budget.charge("cells", _cells(snapshot))
    invocation.budget.charge("input_bytes", snapshot.identity.size + sum(
        table.identity.size for _, table in snapshot.tables))
    invocation.use(UsedInputReceipt(role, snapshot.identity, _SNAPSHOT_MEDIA, "inline",
        snapshot.manifest.dataset_id, version=snapshot.identity))


def record_value(value, request, definition, invocation):
    invocation.check_cancelled()
    snapshot = _snapshot(value, invocation)
    if snapshot is not None:
        invocation.budget.charge("cells", _cells(snapshot))
        for name, table in snapshot.tables:
            invocation.account_output(table.identity, key="component:" + name)
        invocation.account_output(snapshot.identity, key="manifest")
        identity = snapshot.identity
    else:
        identity = value.identity
        invocation.account_output(identity)
    parameters = {name: getattr(request, name) for name in definition.processing.parameters}
    def scalar(item):
        if is_dataclass(item):
            return asdict(item)
        if isinstance(item, tuple):
            return tuple(scalar(value) for value in item)
        return item
    invocation.record(identity, parameters={name: scalar(item) for name, item in parameters.items()})
