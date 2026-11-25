"""Execute one admitted CBR technical method within its existing invocation."""
from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from importlib import import_module
from .capability_declarations import DECLARATIONS

_INDEX = {item['id']: item for item in DECLARATIONS}


def _symbol(reference):
    module, name = reference.split(':')
    value = import_module(module)
    for part in name.split('.'):
        value = getattr(value, part)
    return value


def _field(value, path):
    for part in path.split('.') if path else ():
        value = getattr(value, part)
    return value


def invoke_definition(values, invocation, definition_id, method, **method_options):
    """Construct exact domain input; provider admission stays in the common runner."""
    from stratbox.core.execution import Completion, OperationFailure
    definition = _INDEX[definition_id]
    whole = next((port for port in definition['inputs'] if not port.get('path', port['name'])), None)
    parameters = {field: values[name] for name, field in definition['parameters'].items()
        if '.' not in field and values.get(name) is not None}
    if whole is not None:
        request = values[whole['name']]
        if parameters:
            if not is_dataclass(request):
                raise OperationFailure('cbr.capability.request_parameters_invalid')
            request = replace(request, **parameters)
    else:
        request_type = _symbol(definition['request'])
        kwargs = dict(parameters)
        for port in definition['inputs']:
            if values.get(port['name']) is not None:
                path = port.get('path', port['name'])
                if '.' in path:
                    raise OperationFailure('cbr.capability.nested_request_not_supported')
                kwargs[path] = values[port['name']]
        try:
            request = request_type(**kwargs)
        except TypeError:
            raise OperationFailure('cbr.capability.request_fields_invalid') from None
    answer = method(request, invocation=invocation, **method_options)
    value = answer.value if isinstance(answer, Completion) else answer
    outputs = {}
    for port in definition['outputs']:
        outcome = answer.outcome if isinstance(answer, Completion) else 'succeeded'
        if outcome not in port.get('outcomes', ('succeeded',)):
            continue
        try:
            outputs[port['name']] = _field(value, port.get('path', port['name']))
        except AttributeError:
            raise OperationFailure('cbr.capability.output_unavailable') from None
    value = (next(iter(outputs.values())) if outputs else value) if len(definition['outputs']) == 1 else outputs
    return Completion(value, answer.outcome, *answer.diagnostics) if isinstance(answer, Completion) else value


def extract_form_fields(values, invocation):
    from stratbox.domains.cbr.tables.reporting_forms.field_observations import extract_fields
    from stratbox.core.execution import OperationFailure
    try:
        result = extract_fields(values['flakes'], tuple(values['bindings']),
            include_deleted=values['include_deleted'], checkpoint=invocation.check_cancelled,
            budget=invocation.budget)
    except (ValueError, TypeError) as error:
        raise OperationFailure(str(error) if str(error).startswith('cbr.')
            else 'cbr.forms.field_bindings_invalid') from None
    for receipt in result.lineage:
        invocation.use(receipt)
    return result


def form_source_version(values, invocation):
    """Pin the full physical model input vector before an output selection."""
    from dataclasses import asdict
    from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
    from stratbox.shared.data.tables import table_identity
    snapshots = values['snapshots']
    if not snapshots:
        from stratbox.core.execution import OperationFailure
        raise OperationFailure('cbr.forms.snapshots_empty')
    for snapshot in snapshots:
        for receipt in snapshot.lineage:
            invocation.use(receipt)
    return ByteIdentity.of(canonical_manifest_bytes(tuple(
        {'key': asdict(item.key), 'fields': dict(item.physical_fields),
         'tables': asdict(table_identity((('dbf_rows', item.rows),)))} for item in snapshots))).sha256


def parse_debt_item(values, invocation):
    from stratbox.domains.cbr.methods.corporate_lending.debt.operations import parse
    request = values['item']
    if values.get('selection') is not None:
        request = replace(request, selection=values['selection'])
    return parse(request, invocation=invocation, decoded=values.get('workbook'))


def parse_issuance_item(values, invocation):
    from stratbox.domains.cbr.methods.corporate_lending.issuance.operations import parse
    request = values['item']
    if values.get('selection') is not None:
        request = replace(request, selection=values['selection'])
    return parse(request, invocation=invocation, decoded=values.get('workbook'))


def parse_escrow_item(values, invocation):
    from stratbox.domains.cbr.methods.project_finance.handlers import parse
    return parse(values['item'], invocation=invocation, decoded=values.get('workbook'))


def bind_published_form_fields(values, invocation):
    from stratbox.domains.cbr.tables.reporting_forms.field_observations import published_bindings
    from stratbox.core.execution import OperationFailure
    try:
        return published_bindings(values['flakes'], values['profile_id'], unit=values['unit'],
            scale=values['scale'], period=values['period'])
    except (ValueError, TypeError) as error:
        raise OperationFailure(str(error) if str(error).startswith('cbr.')
            else 'cbr.forms.published_field_basis_required') from None


def validate_form_flakes(values, invocation):
    from stratbox.core.execution import OperationFailure
    from stratbox.core.formats.dbf_lossless import decode_dbf
    from stratbox.domains.cbr.tables.reporting_forms.flakes import validate_flakes
    value = values['flakes']
    try:
        validate_flakes(value)
        for member in value.members:
            invocation.check_cancelled()
            if member.table is not None:
                decoded = decode_dbf(member.data, encoding=member.table.encoding,
                    encoding_basis=member.table.encoding_basis, budget=invocation.budget,
                    checkpoint=invocation.check_cancelled)
                if decoded != member.table:
                    raise ValueError('cbr.forms.decoded_evidence_mismatch')
        for receipt in value.lineage:
            invocation.use(receipt)
    except (ValueError, TypeError) as error:
        raise OperationFailure(str(error) if str(error).startswith(('cbr.', 'dbf.'))
            else 'cbr.forms.validation_failed') from None
    return value


def validate_bank_offices(values, invocation):
    from stratbox.domains.cbr.tables.service_network.snapshots import validate_release
    from stratbox.domains.cbr.methods.service_network.bank_offices.snapshots import _validate
    from stratbox.core.execution import OperationFailure
    value = values['release']
    try:
        validate_release(value, 'cbr.offices', 'cbr.offices.wide-csv')
        _validate(value)
    except (ValueError, TypeError) as error:
        raise OperationFailure(str(error) if str(error).startswith('cbr.') else 'cbr.offices.validation_failed') from None
    for receipt in value.inputs:
        invocation.use(receipt)
    return value


def validate_territorial_offices(values, invocation):
    from stratbox.domains.cbr.tables.service_network.snapshots import validate_release
    from stratbox.domains.cbr.methods.service_network.territorial_offices.snapshots import _validate_release
    from stratbox.core.execution import OperationFailure
    value = values['release']
    try:
        validate_release(value, 'cbr.offices_reg', 'cbr.offices_reg.wide-csv')
        _validate_release(value)
    except (ValueError, TypeError) as error:
        raise OperationFailure(str(error) if str(error).startswith('cbr.') else 'cbr.offices_reg.validation_failed') from None
    for receipt in value.inputs:
        invocation.use(receipt)
    return value


def validate_debt_flake(values, invocation):
    from stratbox.domains.cbr.methods.corporate_lending.industry.snapshot_operations import _use
    from stratbox.domains.cbr.operations.corporate_lending.debt.snapshot_profile import TYPES
    from stratbox.core.execution import OperationFailure
    value = values['file']
    _use(value, '0105a', 'flake', invocation, TYPES)
    if any(issue.severity == 'error' for issue in value.validation_issues):
        raise OperationFailure('source.validation_failed')
    return value


def validate_issuance_flake(values, invocation):
    from stratbox.domains.cbr.methods.corporate_lending.industry.snapshot_operations import _use
    from stratbox.domains.cbr.operations.corporate_lending.issuance.snapshot_profile import TYPES
    from stratbox.core.execution import OperationFailure
    value = values['file']
    _use(value, '0104a', 'flake', invocation, TYPES)
    if any(issue.severity == 'error' for issue in value.validation_issues):
        raise OperationFailure('source.validation_failed')
    return value


def escrow_change(values, invocation):
    from stratbox.domains.cbr.integration.project_finance.evidence import use_dataset
    from stratbox.domains.cbr.integration.project_finance.mapping import align_values
    from stratbox.domains.cbr.analytics.project_finance.changes import calculate
    from stratbox.core.execution import OperationFailure
    try:
        batch = align_values(use_dataset(values['dataset'], invocation), tuple(values['geography']))
        result = calculate(batch, values['before'], values['after'], tuple(values['metric_ids']), method=values['method'])
    except (ValueError, TypeError) as error:
        raise OperationFailure(str(error) if str(error).startswith('escrow.') else 'escrow.change_input_invalid') from None
    for receipt in result.lineage:
        invocation.use(receipt)
    return result


def collect_raw_member(values, invocation):
    from stratbox.domains.cbr.methods.collection.steps import CollectRawStepRequest, collect_raw_step
    from stratbox.domains.cbr.publications.collection.contracts import CollectFilesRequest
    from stratbox.core.execution import OperationFailure
    selected = tuple(values['source_ids'])
    if not selected or len(selected) != len(set(selected)) or values['item'] not in selected:
        raise OperationFailure('cbr.collection.selection_invalid')
    policy = CollectFilesRequest((values['item'],), values['continue_on_error'], values['try_case_variants'],
        values['deadline_per_source_seconds'], values['max_batch_bytes'], values['retry'])
    return collect_raw_step(CollectRawStepRequest(policy, values.get('state'), values['max_batch_bytes'],
        values['continue_on_error'], values['item'] == selected[-1]), invocation=invocation)


def collect_stored_member(values, invocation):
    from stratbox.domains.cbr.methods.collection.steps import CollectStoredStepRequest, collect_stored_step
    from stratbox.domains.cbr.publications.collection.contracts import CollectToStoreRequest
    from stratbox.core.execution import OperationFailure
    policy, destinations = values['selection'], dict(values['destinations'])
    selected = policy.source_ids
    if (not selected or len(selected) != len(set(selected)) or values['item'] not in selected
            or set(destinations) != set(selected)
            or len({item.locator for item in destinations.values()}) != len(selected)):
        raise OperationFailure('cbr.collection.selection_invalid')
    single = CollectToStoreRequest(replace(policy, source_ids=(values['item'],)),
        {values['item']: destinations[values['item']]})
    return collect_stored_step(CollectStoredStepRequest(single, values.get('state'), policy.max_batch_bytes,
        policy.continue_on_error, values['item'] == selected[-1]), invocation=invocation)


def collect_material_member(values, invocation):
    from stratbox.domains.cbr.methods.collection.steps import CollectMaterialStepRequest, collect_material_step
    from stratbox.core.execution import OperationFailure
    selected = tuple(values['items'])
    if not selected or len({item.key for item in selected}) != len(selected):
        raise OperationFailure('cbr.collection.selection_invalid')
    return collect_material_step(CollectMaterialStepRequest(values['item'], values.get('state'),
        values['max_batch_bytes'], values['continue_on_error'], values['item'].key == selected[-1].key),
        invocation=invocation)


def industry_product_basis(values, invocation):
    """Read product labels and reference periods from the admitted source data."""
    from stratbox.core.operations.tables import use_stream
    from stratbox.core.execution import OperationFailure
    frame = use_stream(invocation, values['stream'])
    if not {'industry_code', 'industry_name_ru'} <= set(frame.columns):
        raise OperationFailure('cbr.industries.product_source_invalid')
    selected = frame.loc[frame.industry_code.eq(values['industry_code'])]
    names = tuple(selected.industry_name_ru.dropna().astype(str).unique())
    if len(names) != 1 or not len(selected):
        raise OperationFailure('cbr.industries.product_industry_unresolved')
    periods = tuple(sorted(selected.reference_period.dropna().astype(str).unique())) if 'reference_period' in frame else ()
    return {'industry_name_ru': names[0], 'reference_periods': periods}


def original_payload(values, invocation):
    from stratbox.domains.cbr.operations.statistics.evidence import use_value
    original = values['original']
    use_value(original, invocation, 'original')
    return original.payload


def flake_from_decoded_workbook(values, invocation):
    from types import SimpleNamespace
    from stratbox.domains.cbr.tables.statistics.extraction import extract_workbook_value
    from stratbox.domains.cbr.operations.statistics.evidence import use_value, record_value
    from stratbox.domains.cbr.operations.statistics.definitions import EXTRACT
    from stratbox.core.execution import OperationFailure
    original, workbook = values['original'], values['workbook']
    try:
        use_value(original, invocation, 'original')
        value = extract_workbook_value(original, budget=invocation.budget, workbook=workbook)
        record_value(value, SimpleNamespace(original=original), EXTRACT, invocation)
    except (TypeError, ValueError) as error:
        raise OperationFailure(str(error) if str(error).startswith(('cbr.', 'workbook.'))
            else 'cbr.workbook.decoded_source_invalid') from None
    return value


def interpret_debt_decoded(values, invocation):
    from stratbox.domains.cbr.methods.corporate_lending.debt.operations import parse
    return invoke_definition(values, invocation, 'cbr.industries.0105a.parse', parse, decoded=values['workbook'])


def interpret_issuance_decoded(values, invocation):
    from stratbox.domains.cbr.methods.corporate_lending.issuance.operations import parse
    return invoke_definition(values, invocation, 'cbr.industries.0104a.parse', parse, decoded=values['workbook'])


def interpret_escrow_decoded(values, invocation):
    from stratbox.domains.cbr.methods.project_finance.handlers import parse
    return invoke_definition(values, invocation, 'cbr.escrow.parse', parse, decoded=values['workbook'])


def workbook_item_payload(values, invocation):
    from stratbox.shared.evidence import SourcePayload
    from stratbox.core.execution import OperationFailure
    payload = getattr(values['item'], 'payload', None)
    if not isinstance(payload, SourcePayload):
        raise OperationFailure('cbr.workbook.item_payload_required')
    return payload
