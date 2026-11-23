"""Operation adapters for independent escrow integration and snapshots."""
from stratbox.core.execution import OperationFailure
from stratbox.core.execution.runner import run
from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.domains.cbr.tables.project_finance import snapshots as flake_codec
from stratbox.domains.cbr.tables.project_finance.evidence import use_flake, seal_flake
from stratbox.domains.cbr.integration.project_finance import snapshots as dataset_codec
from stratbox.domains.cbr.integration.project_finance.assembly import integrate_values
from stratbox.domains.cbr.integration.project_finance.evidence import use_dataset, seal_dataset
from stratbox.domains.cbr.products.project_finance import snapshots as view_codec
from stratbox.domains.cbr.products.project_finance.evidence import use_view, seal_view

def integrate_flakes(request, *, context=None):
    from .definitions import INTEGRATE
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        invocation.stage("integrate")
        try:
            flakes = tuple(use_flake(flake, invocation) for flake in req.flakes)
            return seal_dataset(integrate_values(flakes, req.coverage), invocation)
        except (TypeError, ValueError, KeyError) as error:
            raise OperationFailure(_error_code(error, "escrow.integration_invalid")) from None
    return run(INTEGRATE, request, work, context=context)


def _error_code(error, fallback):
    code = str(error)
    return code if code.startswith("escrow.") and " " not in code else fallback


def _encode(definition, request, get_value, encode, consume, *, context):
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        invocation.stage("encode_snapshot")
        try:
            value = consume(get_value(req), invocation)
            snapshot = encode(value, dataset_id=req.dataset_id, version_id=req.version_id)
        except (TypeError, ValueError, KeyError) as error:
            raise OperationFailure(_error_code(error, "escrow.snapshot_invalid")) from None
        invocation.record(snapshot.identity, parameters={"dataset_id": snapshot.manifest.dataset_id, "version_id": snapshot.manifest.version_id})
        return snapshot
    return run(definition, request, work, context=context)


def _decode(definition, request, decode, seal, *, context):
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        invocation.stage("decode_snapshot")
        invocation.use(UsedInputReceipt("snapshot", req.snapshot.identity, "application/json", "inline"))
        invocation.budget.check("cells", sum(len(table.rows) * len(table.schema.columns) for _, table in req.snapshot.tables))
        try:
            value = decode(req.snapshot)
            return seal(value, invocation)
        except (TypeError, ValueError, KeyError) as error:
            raise OperationFailure(_error_code(error, "escrow.snapshot_invalid")) from None
    return run(definition, request, work, context=context)


def build_flake_snapshot(request, *, context=None):
    from .definitions import FLAKE_SNAPSHOT
    return _encode(FLAKE_SNAPSHOT, request, lambda req: req.flake, flake_codec.flake_snapshot, use_flake, context=context)


def read_flake_snapshot(request, *, context=None):
    from .definitions import READ_FLAKE_SNAPSHOT
    return _decode(READ_FLAKE_SNAPSHOT, request, flake_codec.flake_from_snapshot, seal_flake, context=context)


def build_dataset_snapshot(request, *, context=None):
    from .definitions import DATASET_SNAPSHOT
    return _encode(DATASET_SNAPSHOT, request, lambda req: req.dataset, dataset_codec.dataset_snapshot, use_dataset, context=context)


def read_dataset_snapshot(request, *, context=None):
    from .definitions import READ_DATASET_SNAPSHOT
    return _decode(READ_DATASET_SNAPSHOT, request, dataset_codec.dataset_from_snapshot, seal_dataset, context=context)


def build_view_snapshot(request, *, context=None):
    from .definitions import VIEW_SNAPSHOT
    return _encode(VIEW_SNAPSHOT, request, lambda req: req.view, view_codec.view_snapshot, use_view, context=context)


def read_view_snapshot(request, *, context=None):
    from .definitions import READ_VIEW_SNAPSHOT
    return _decode(READ_VIEW_SNAPSHOT, request, view_codec.view_from_snapshot, seal_view, context=context)
