"""Separate shared physical workbook decoding from CBR source attribution."""
from dataclasses import replace

from stratbox.capabilities.model import Call, CommandDefinition, GraphBody, InputRef, OperationDefinition, OutputRef, ReuseContract
from stratbox.capabilities.commands import MATERIAL, WORKBOOK, READABLE
from stratbox.capabilities.model import ParameterRef, PortContract


def assemble(definitions):
    result = dict(definitions)
    extraction = result['cbr.tables.extract']
    original, flake = extraction.inputs['original'], extraction.outputs['flake']
    payload = CommandDefinition('cbr.command.original.payload',
        'stratbox.domains.cbr.capability_methods:original_payload',
        inputs={'original': original}, outputs={'material': MATERIAL}, reuse=ReuseContract(mutation='immutable'))
    attribute = CommandDefinition('cbr.command.tables.attribute_workbook',
        'stratbox.domains.cbr.capability_methods:flake_from_decoded_workbook',
        inputs={'original': original, 'workbook': WORKBOOK}, outputs={'flake': flake},
        reuse=ReuseContract(mutation='immutable'))
    for command in (payload, attribute):
        result[command.capability_id] = command
    steps = (
        Call('material', payload.capability_id, {'original': InputRef('original')}),
        Call('decode', 'workbook.decode', {'material': OutputRef('material', 'material')}),
        Call('attribute', attribute.capability_id,
            {'original': InputRef('original'), 'workbook': OutputRef('decode')}),
    )
    result['cbr.tables.extract'] = replace(extraction,
        body=GraphBody(steps, {'flake': OutputRef('attribute', 'flake')}, required_completions=('attribute',)))
    result.pop('cbr.command.tables.extract', None)
    readable = result['cbr.tables.readable']
    result['cbr.tables.readable_original'] = OperationDefinition('cbr.tables.readable_original', GraphBody((*steps,
        Call('readable', 'cbr.command.tables.readable', {'flake': OutputRef('attribute', 'flake')}),
    ), {'readable': OutputRef('readable', 'readable')}, required_completions=('readable',)),
        inputs={'original': original}, outputs=readable.outputs,
        summary='Prepare complete source-qualified readable cells through the shared workbook decoder.')
    # Statistical and specialized interpretations now consume the same physical
    # WorkbookCells contract; original bytes remain a separate typed input.
    for prefix, implementation in (('cbr.industries.0105a', 'interpret_debt_decoded'),
                                   ('cbr.industries.0104a', 'interpret_issuance_decoded'),
                                   ('cbr.escrow', 'interpret_escrow_decoded')):
        parsed = result[prefix + '.parse']
        inputs = {**parsed.inputs, 'source': MATERIAL}
        command_id = prefix + '.command.interpret_workbook'
        result[command_id] = CommandDefinition(command_id,
            'stratbox.domains.cbr.capability_methods:' + implementation,
            inputs={**inputs, 'workbook': WORKBOOK}, outputs=parsed.outputs,
            parameters=parsed.parameters, required_parameters=parsed.required_parameters,
            reuse=ReuseContract(shareable=False), acceptance=parsed.acceptance)
        decode = Call('decode', 'workbook.decode', {'material': InputRef('source')})
        result[prefix + '.parse'] = replace(parsed, inputs=inputs, body=GraphBody((decode,
            Call('interpret', command_id,
                {**{name: InputRef(name) for name in inputs}, 'workbook': OutputRef('decode')},
                {name: ParameterRef(name) for name in (*parsed.parameters, *parsed.required_parameters)}),
        ), {name: OutputRef('interpret', name) for name in parsed.outputs}, required_completions=('interpret',)))
        result.pop('cbr.command.' + prefix[4:] + '.parse', None)
        result[prefix + '.readable_original'] = OperationDefinition(prefix + '.readable_original', GraphBody((
            decode, Call('readable', 'workbook.readable', {'workbook': OutputRef('decode')}),
        ), {'readable': OutputRef('readable')}), inputs={'source': MATERIAL}, outputs={'readable': READABLE})
    item_payload = CommandDefinition('cbr.command.workbook.item_payload',
        'stratbox.domains.cbr.capability_methods:workbook_item_payload', inputs={'item': PortContract()},
        outputs={'material': MATERIAL}, reuse=ReuseContract(mutation='immutable'))
    result[item_payload.capability_id] = item_payload
    item_steps = (Call('material', item_payload.capability_id, {'item': InputRef('item')}),
        Call('decode', 'workbook.decode', {'material': OutputRef('material', 'material')}))
    for prefix in ('cbr.industries.0105a', 'cbr.industries.0104a', 'cbr.escrow'):
        item = result[prefix + '.parse_item']
        command_id = prefix + '.command.parse_item'
        command = result[command_id]
        result[command_id] = replace(command, inputs={**command.inputs, 'workbook': WORKBOOK})
        result[prefix + '.parse_item'] = replace(item, body=GraphBody((*item_steps,
            Call('interpret', command_id, {'item': InputRef('item'), 'workbook': OutputRef('decode')},
                {name: ParameterRef(name) for name in item.parameters}),
        ), {'value': OutputRef('interpret')}, required_completions=('interpret',)))
    result['cbr.workbook.item_readable'] = OperationDefinition('cbr.workbook.item_readable', GraphBody((*item_steps,
        Call('readable', 'workbook.readable', {'workbook': OutputRef('decode')}),
    ), {'readable': OutputRef('readable')}), inputs={'item': PortContract()}, outputs={'readable': READABLE})
    return tuple(result.values())
