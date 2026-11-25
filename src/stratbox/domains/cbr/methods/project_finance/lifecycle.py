"""Operation adapters for independent escrow integration and snapshots."""
from stratbox.core.execution import OperationFailure
from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.domains.cbr.tables.project_finance import snapshots as flake_codec
from stratbox.domains.cbr.tables.project_finance.evidence import use_flake, seal_flake
from stratbox.domains.cbr.integration.project_finance import snapshots as dataset_codec
from stratbox.domains.cbr.integration.project_finance.assembly import integrate_values
from stratbox.domains.cbr.integration.project_finance.evidence import use_dataset, seal_dataset
from stratbox.domains.cbr.products.project_finance import snapshots as view_codec
from stratbox.domains.cbr.products.project_finance.evidence import use_view, seal_view

def integrate_flakes(request, *, invocation=None):
    from stratbox.domains.cbr.operations.project_finance.definitions import INTEGRATE

    def work(req, invocation):
        require_extra('pandas', 'dataframe')
        invocation.stage('integrate')
        try:
            flakes = tuple((use_flake(flake, invocation) for flake in req.flakes))
            return seal_dataset(integrate_values(flakes, req.coverage), invocation)
        except (TypeError, ValueError, KeyError) as error:
            raise OperationFailure(_error_code(error, 'escrow.integration_invalid')) from None
    return work(request, invocation)

def _error_code(error, fallback):
    code = str(error)
    return code if code.startswith('escrow.') and ' ' not in code else fallback

def _encode(definition, request, get_value, encode, consume, *, invocation):

    def work(req, invocation):
        require_extra('pandas', 'dataframe')
        invocation.stage('encode_snapshot')
        try:
            value = consume(get_value(req), invocation)
            snapshot = encode(value, dataset_id=req.dataset_id, version_id=req.version_id)
        except (TypeError, ValueError, KeyError) as error:
            raise OperationFailure(_error_code(error, 'escrow.snapshot_invalid')) from None
        invocation.record(snapshot.identity, parameters={'dataset_id': snapshot.manifest.dataset_id, 'version_id': snapshot.manifest.version_id})
        return snapshot
    return work(request, invocation)

def _decode(definition, request, decode, seal, *, invocation):

    def work(req, invocation):
        require_extra('pandas', 'dataframe')
        invocation.stage('decode_snapshot')
        invocation.use(UsedInputReceipt('snapshot', req.snapshot.identity, 'application/json', 'inline'))
        invocation.budget.check('cells', sum((len(table.rows) * len(table.schema.columns) for _, table in req.snapshot.tables)))
        try:
            value = decode(req.snapshot)
            return seal(value, invocation)
        except (TypeError, ValueError, KeyError) as error:
            raise OperationFailure(_error_code(error, 'escrow.snapshot_invalid')) from None
    return work(request, invocation)

def build_flake_snapshot(request, *, invocation=None):
    from stratbox.domains.cbr.operations.project_finance.definitions import FLAKE_SNAPSHOT
    return _encode(FLAKE_SNAPSHOT, request, lambda req: req.flake, flake_codec.flake_snapshot, use_flake, invocation=invocation)

def read_flake_snapshot(request, *, invocation=None):
    from stratbox.domains.cbr.operations.project_finance.definitions import READ_FLAKE_SNAPSHOT
    return _decode(READ_FLAKE_SNAPSHOT, request, flake_codec.flake_from_snapshot, seal_flake, invocation=invocation)

def build_dataset_snapshot(request, *, invocation=None):
    from stratbox.domains.cbr.operations.project_finance.definitions import DATASET_SNAPSHOT
    return _encode(DATASET_SNAPSHOT, request, lambda req: req.dataset, dataset_codec.dataset_snapshot, use_dataset, invocation=invocation)

def read_dataset_snapshot(request, *, invocation=None):
    from stratbox.domains.cbr.operations.project_finance.definitions import READ_DATASET_SNAPSHOT
    return _decode(READ_DATASET_SNAPSHOT, request, dataset_codec.dataset_from_snapshot, seal_dataset, invocation=invocation)

def build_view_snapshot(request, *, invocation=None):
    from stratbox.domains.cbr.operations.project_finance.definitions import VIEW_SNAPSHOT
    return _encode(VIEW_SNAPSHOT, request, lambda req: req.view, view_codec.view_snapshot, use_view, invocation=invocation)

def read_view_snapshot(request, *, invocation=None):
    from stratbox.domains.cbr.operations.project_finance.definitions import READ_VIEW_SNAPSHOT
    return _decode(READ_VIEW_SNAPSHOT, request, view_codec.view_from_snapshot, seal_view, invocation=invocation)


def capability_build_dataset_snapshot(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.dataset_snapshot', build_dataset_snapshot)


def capability_build_flake_snapshot(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.flake_snapshot', build_flake_snapshot)


def capability_integrate_flakes(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.integrate_flakes', integrate_flakes)


def capability_read_dataset_snapshot(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.read_dataset_snapshot', read_dataset_snapshot)


def capability_read_flake_snapshot(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.read_flake_snapshot', read_flake_snapshot)


def capability_read_view_snapshot(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.read_view_snapshot', read_view_snapshot)


def capability_build_view_snapshot(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.view_snapshot', build_view_snapshot)
