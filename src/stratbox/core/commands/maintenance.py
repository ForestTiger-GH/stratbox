"""Plan and apply explicit conditional filesystem maintenance actions."""
from __future__ import annotations
from pathlib import Path
from typing import Mapping
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import fingerprint
from ._settings import _get, _option
from ._storage import _provider_scope


def material_maintenance_plan(inputs, settings, context):
    actions = _option(context, settings, "actions", ())
    if not actions: return {"plan": ()}
    available = {str(item.get("path")) if isinstance(item, Mapping) else str(item) for item in inputs["inventory"]}
    if any(str(_get(action, "source")) not in available for action in actions):
        raise ExecutionFailure("maintenance.inventory_mismatch")
    return {"plan": tuple(actions)}


def material_maintenance_apply(inputs, settings, context):
    store, receipts = context.provider("filestore"), []
    for action in inputs["plan"]:
        context.checkpoint()
        source, operation = _get(action, "source"), _get(action, "operation")
        scope = _option(context, settings, "scope")
        if scope is None or not Path(str(source)).is_relative_to(Path(str(scope))):
            raise ExecutionFailure("maintenance.explicit_scope_required")
        expected = _get(action, "expected_identity")
        if expected is None: raise ExecutionFailure("maintenance.expected_identity_required")
        methods = ("guard_directory", "inspect_file", "rename_expected" if operation == "move" else "remove_expected")
        if operation not in {"move", "delete"} or not all(callable(getattr(store, name, None)) for name in methods):
            raise ExecutionFailure("maintenance.conditional_provider_required")
        destination = _get(action, "destination")
        if destination is not None and not Path(str(destination)).is_relative_to(Path(str(scope))):
            raise ExecutionFailure("maintenance.destination_outside_scope")
        if destination is not None and Path(str(source)).parent != Path(str(destination)).parent:
            raise ExecutionFailure("maintenance.same_directory_required")
        def perform(source=source, destination=destination, expected=expected, operation=operation):
            from stratbox.core.storage.filestore import MutationRejected
            with store.guard_directory(str(Path(str(source)).parent)):
                observed = store.inspect_file(source)
                if observed.identity != expected:
                    raise MutationRejected("Source changed", code="maintenance.state_conflict")
                success = store.rename_expected(observed, destination) if operation == "move" else store.remove_expected(observed)
                if not success: raise MutationRejected("Conditional mutation rejected", code="maintenance.state_conflict")
                return {"source": source, "destination": destination, "identity": expected, "operation": operation}
        receipt = context.effect("storage.write", fingerprint(("maintenance", _provider_scope(store, source), operation, source, destination, expected)), perform, resource=str(source))
        if receipt.status != "confirmed": raise ExecutionFailure("maintenance." + receipt.status, outcome="unknown" if receipt.status == "unknown" else "failed")
        receipts.append(receipt)
    return {"receipts": tuple(receipts)}
