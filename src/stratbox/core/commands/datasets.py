"""Ingest and query logical datasets through explicit dataset providers."""
from __future__ import annotations
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import SnapshotRef, fingerprint
from ._settings import _get, _option
from ._values import _rows
from ._storage import _provider_scope


def dataset_ingest(inputs, settings, context):
    dataset, writer = inputs["dataset"], context.provider("dataset_writer")
    _rows(dataset)
    destination = inputs.get("destination") or _option(context, settings, "destination", dataset.source_id)
    identity = fingerprint(dataset)
    def action():
        result = writer.ingest(dataset, destination=destination, identity=identity)
        return result if isinstance(result, SnapshotRef) else SnapshotRef(str(result), str(getattr(writer, "provider_id", "dataset_writer")), identity)
    receipt = context.effect("dataset.write", fingerprint(("dataset.write", _provider_scope(writer, destination), destination, identity)), action, resource=str(destination))
    if receipt.status != "confirmed": raise ExecutionFailure("dataset.unknown", outcome="unknown")
    return {"reference": receipt.value, "receipt": receipt}


def dataset_query(inputs, settings, context):
    reader = context.provider("dataset_reader")
    result = reader.query(inputs["reference"], inputs.get("query") or _get(settings, "query", {}))
    _rows(result)
    return {"observations": result}
