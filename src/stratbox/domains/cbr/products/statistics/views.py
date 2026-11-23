"""Select an integrated result into a complete, retained presentation dataset."""
from dataclasses import dataclass, replace

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.domains.cbr.integration.statistics.snapshots import input_table, diagnostic_table

VIEW = DataContract("cbr.statistics.view", 1, DataRole.PRODUCTS)
_META = TableSchema(DataContract("cbr.statistics.view.metadata", 1, DataRole.PRODUCTS), (
    ColumnSchema("title", ScalarType.TEXT), ColumnSchema("profile", ScalarType.TEXT),
    ColumnSchema("mapping_version", ScalarType.TEXT), ColumnSchema("method", ScalarType.TEXT)))
_NAMES = ("series", "release", "subject_namespace", "subject", "metric", "label", "period",
          "value", "status", "unit", "scale", "quantity_kind", "basis", "source_sheet", "evidence")
_ROWS = TableSchema(DataContract("cbr.statistics.view.rows", 1, DataRole.PRODUCTS),
                    tuple(ColumnSchema(name, ScalarType.TEXT) for name in _NAMES))


@dataclass(frozen=True, slots=True)
class StatisticsView:
    snapshot: DatasetSnapshot

    @property
    def identity(self):
        return self.snapshot.identity


def build_view(dataset, *, series_ids=(), metric_ids=(), release_ids=(), title="Bank of Russia statistics"):
    if not isinstance(title, str) or not title.strip() or len(title) > 1024:
        raise ValueError("cbr.statistics.view_title_invalid")
    if series_ids and not set(series_ids) <= {batch.dataset_id for batch in dataset.batches}:
        raise ValueError("cbr.statistics.view_series_unknown")
    if release_ids and not set(release_ids) <= {batch.release_id for batch in dataset.batches}:
        raise ValueError("cbr.statistics.view_release_unknown")
    rows, seen_metrics = [], set()
    for batch in dataset.batches:
        if series_ids and batch.dataset_id not in series_ids or release_ids and batch.release_id not in release_ids:
            continue
        for item in batch.observations:
            if metric_ids and item.metric.id not in metric_ids:
                continue
            seen_metrics.add(item.metric.id)
            dimensions = dict(item.dimensions)
            period = str(item.period.as_of) if item.period.as_of else f"{item.period.start}/{item.period.end}"
            rows.append((batch.dataset_id, batch.release_id, item.subject.namespace, item.subject.id, item.metric.id,
                dimensions.get("source_hierarchy", item.metric.id), period, "" if item.value is None else str(item.value),
                item.value_status, item.metric.unit, "" if item.metric.scale is None else str(item.metric.scale),
                item.metric.quantity_kind or "", dimensions.get("measure_basis", ""), dimensions.get("source_sheet", ""), item.evidence_ref))
    if metric_ids and set(metric_ids) != seen_metrics:
        raise ValueError("cbr.statistics.view_metric_unknown")
    if not rows:
        raise ValueError("cbr.statistics.view_empty_selection")
    parent = dataset.identity
    lineage = (*dataset.lineage, UsedInputReceipt("integrated_statistics", parent,
        "application/vnd.stratbox.dataset+json", "inline", version=parent))
    tables = (("metadata", TypedTable(_META, ((title, "cbr.statistics.views", dataset.mapping_version, dataset.method),))),
              ("observations", TypedTable(_ROWS, tuple(rows))), ("inputs", input_table(dataset.inputs)),
              ("diagnostics", diagnostic_table(dataset.diagnostics)))
    snapshot = DatasetSnapshot.build("cbr.statistics.view", "content", VIEW, tables,
        coverage=SnapshotCoverage("partial", "Explicit presentation selection; full input versions remain attached."),
        inputs=lineage, parents=(parent,))
    snapshot = DatasetSnapshot(replace(snapshot.manifest, version_id=snapshot.identity.sha256), snapshot.tables)
    return StatisticsView(snapshot)


def view_snapshot(view):
    if not isinstance(view, StatisticsView):
        raise ValueError("cbr.statistics.prepared_view_required")
    view_from_snapshot(view.snapshot)
    return view.snapshot


def view_from_snapshot(snapshot):
    from stratbox.domains.cbr.integration.statistics.snapshots import INPUTS, DIAGNOSTICS
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete or snapshot.manifest.contract != VIEW
            or tuple(name for name, _ in snapshot.tables) != ("metadata", "observations", "inputs", "diagnostics")
            or snapshot.table("metadata").schema != _META or len(snapshot.table("metadata").rows) != 1
            or snapshot.table("observations").schema != _ROWS or snapshot.table("inputs").schema != INPUTS
            or snapshot.table("diagnostics").schema != DIAGNOSTICS or not snapshot.manifest.parents
            or not snapshot.table("inputs").rows):
        raise ValueError("cbr.statistics.view_snapshot_invalid")
    return StatisticsView(snapshot)
