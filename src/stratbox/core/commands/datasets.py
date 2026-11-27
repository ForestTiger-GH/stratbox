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
    provider_id = getattr(writer, 'provider_id', None)
    scope = getattr(writer, 'storage_scope', None)
    provider_scope = scope(str(destination)) if callable(scope) else getattr(writer, 'scope_id', None)
    if (not isinstance(provider_id, str) or not provider_id or not isinstance(provider_scope, str)
            or not provider_scope or len(provider_scope) > 4096):
        raise ExecutionFailure('dataset.provider_scope_required')
    intent = {'provider_id': provider_id, 'provider_scope': provider_scope,
        'destination': str(destination), 'identity': identity}
    def action():
        return writer.ingest(dataset, destination=destination, identity=identity)
    receipt = context.effect("dataset.write", fingerprint(("dataset.write", _provider_scope(writer, destination), destination, identity)),
        action, resource=str(destination), intent=intent)
    if receipt.status != "confirmed": raise ExecutionFailure("dataset.unknown", outcome="unknown")
    return {"reference": receipt.value, "receipt": receipt}


def dataset_query(inputs, settings, context):
    reader = context.provider("dataset_reader")
    result = reader.query(inputs["reference"], inputs.get("query") or _get(settings, "query", {}))
    _rows(result)
    return {"observations": result}
