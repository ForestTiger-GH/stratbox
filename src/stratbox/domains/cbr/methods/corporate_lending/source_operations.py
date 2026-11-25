"""Runner admission around reusable source observation transformations."""
from dataclasses import replace
from stratbox.core.execution import Completion, OperationFailure
from stratbox.core.operations.tables import record_tables, use_tables
from stratbox.domains.cbr.tables.corporate_lending import observation_snapshots as codec
from stratbox.domains.cbr.tables.corporate_lending.observations import extract_observations
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.domains.cbr.operations.corporate_lending.source_definitions import EXTRACT, ENCODE, DECODE

def extract(request, *, invocation=None):

    def work(req, invocation):
        invocation.stage('extract_observations')
        invocation.use(UsedInputReceipt('source_workbook_flake', req.flake.identity, 'application/vnd.stratbox.dataset+json', 'reference_only', req.flake.series_id))
        invocation.use(UsedInputReceipt('original', req.flake.source_identity, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'reference_only', req.flake.series_id))
        try:
            value = extract_observations(req.flake, periods=req.periods, checkpoint=invocation.check_cancelled, budget=invocation.budget)
            codec.validate(value)
        except (ValueError, TypeError, KeyError) as error:
            raise OperationFailure(_code(error)) from None
        value = replace(value, evidence=record_tables(invocation, (('observations', value.observations),), metadata=codec.metadata(value), parameters={'periods': req.periods}))
        return Completion(value, 'partial', 'cbr.corporate.source_layout_partial') if value.diagnostics else value
    return work(request, invocation)

def use_observations(value, invocation, *, role='corporate_source_observations'):
    codec.validate(value, require_seal=True)
    frame, = use_tables(invocation, (('observations', value.observations),), receipt=value.evidence, role=role, metadata=codec.metadata(value))
    return replace(value, observations=frame)

def build_snapshot(request, *, invocation=None):

    def work(req, invocation):
        invocation.stage('encode_snapshot')
        try:
            value = use_observations(req.value, invocation)
            result = codec.snapshot(value, dataset_id=req.dataset_id, version_id=req.version_id, checkpoint=invocation.check_cancelled)
        except (ValueError, TypeError, KeyError) as error:
            raise OperationFailure(_code(error)) from None
        for name, table in result.tables:
            invocation.account_output(table.identity, key='snapshot:' + name)
        invocation.account_output(result.identity, key='snapshot:manifest')
        invocation.record(result.identity)
        return result
    return work(request, invocation)

def read_snapshot(request, *, invocation=None):

    def work(req, invocation):
        invocation.stage('decode_snapshot')
        invocation.budget.charge('input_bytes', req.snapshot.identity.size + sum((t.identity.size for _, t in req.snapshot.tables)))
        invocation.budget.check('cells', sum((len(t.rows) * len(t.schema.columns) for _, t in req.snapshot.tables)))
        invocation.use(UsedInputReceipt('snapshot', req.snapshot.identity, 'application/json', 'inline'))
        try:
            value = codec.from_snapshot(req.snapshot, checkpoint=invocation.check_cancelled)
        except (ValueError, TypeError, KeyError) as error:
            raise OperationFailure(_code(error)) from None
        invocation.parents.append(('source_observations', value.evidence))
        invocation.record(value.evidence.output)
        return value
    return work(request, invocation)

def _code(error):
    text = str(error)
    return text if text.startswith(('cbr.', 'dataframe.')) and ' ' not in text else 'cbr.corporate.source_invalid'


def capability_extract(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.corporate_lending.extract_observations', extract)


def capability_build_snapshot(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.corporate_lending.observation_snapshot', build_snapshot)


def capability_read_snapshot(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.corporate_lending.read_observation_snapshot', read_snapshot)
