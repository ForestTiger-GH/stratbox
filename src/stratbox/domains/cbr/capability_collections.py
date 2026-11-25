"""Ordered member scenarios use ordinary session retries and byte admission."""
from dataclasses import replace

from stratbox.capabilities.model import (AcceptanceContract, Call, CommandDefinition, FoldCall,
    GraphBody, InputRef, OperationDefinition, OutputRef, ParameterRef, PortContract,
    ReuseContract, ScenarioDefinition)
from stratbox.core.network import RetryPolicy as HttpRetry

_RETRY_CODES = ('http.connection_error', 'http.timeout', 'http.truncated', 'http.status_429',
    'http.status_500', 'http.status_502', 'http.status_503', 'http.status_504')


def assemble(definitions):
    result = dict(definitions)
    for name, method, step_id in (
        ('collect_raw', 'collect_raw_member', 'collect_raw_step'),
        ('collect_to_store', 'collect_stored_member', 'collect_stored_step'),
        ('collect_materials', 'collect_material_member', 'collect_material_step')):
        identifier = 'cbr.file_collector.' + name
        original = result[identifier]
        state = original.outputs['collection']
        prior = replace(state, required=False)
        inputs = {'item': PortContract(), 'state': prior}
        stored, materials = name == 'collect_to_store', name == 'collect_materials'
        parameters = ({'continue_on_error': True, 'max_batch_bytes': 256 * 1024**2} if materials else
            {} if stored else {'continue_on_error': True, 'try_case_variants': True,
                'deadline_per_source_seconds': 60, 'max_batch_bytes': 256 * 1024**2, 'retry': HttpRetry()})
        required = ('selection', 'destinations') if stored else ('items',) if materials else ('source_ids',)
        children_parameters = {key: ParameterRef(key) for key in (*parameters, *required)}
        effects = frozenset({'storage.write'}) if stored else frozenset()
        command_id = 'cbr.command.file_collector.' + method
        operation_id = 'cbr.file_collector.' + method
        scenario_id = 'scenario.cbr.file_collector.' + method
        result[command_id] = CommandDefinition(command_id,
            'stratbox.domains.cbr.capability_methods:' + method,
            inputs=inputs, outputs={'value': state}, parameters=parameters, required_parameters=required,
            required_capabilities=frozenset({'http', 'output_filestore'} if stored else {'http'} if not materials else ()),
            optional_capabilities=frozenset({'http', 'filestore'} if materials else ()), effects=effects,
            reuse=ReuseContract(shareable=False, effects=effects), acceptance=AcceptanceContract(partial_allowed=True))
        result[operation_id] = OperationDefinition(operation_id, GraphBody((
            Call('receive', command_id, {key: InputRef(key) for key in inputs}, children_parameters),
        ), {'value': OutputRef('receive')}, required_completions=('receive',)),
            inputs=inputs, outputs={'value': state}, parameters=parameters, required_parameters=required,
            effects=effects, acceptance=AcceptanceContract(partial_allowed=True))
        result[scenario_id] = ScenarioDefinition(scenario_id, GraphBody((
            Call('receive', operation_id, {key: InputRef(key) for key in inputs}, children_parameters),
        ), {'value': OutputRef('receive')}, required_completions=('receive',)),
            inputs=inputs, outputs={'value': state}, parameters=parameters, required_parameters=required,
            effects=effects, acceptance=AcceptanceContract(partial_allowed=True),
            purpose='Receive one publisher member while retaining the cumulative admitted collection.')
        policy_path = ('selection', 'retry') if stored else ('retry', '')
        retry = None if materials else {
            'max_attempts': ParameterRef(policy_path[0], '.'.join(filter(None, (policy_path[1], 'attempts')))),
            'delay': ParameterRef(policy_path[0], '.'.join(filter(None, (policy_path[1], 'initial_delay_seconds')))),
            'retry_codes': _RETRY_CODES}
        items = ParameterRef('selection', 'source_ids') if stored else ParameterRef('items' if materials else 'source_ids')
        result[identifier] = ScenarioDefinition(identifier, GraphBody((
            FoldCall('members', scenario_id, items, None, state, parameters=children_parameters,
                retry=retry, max_items=10000),
        ), {'collection': OutputRef('members')}, required_completions=('members',)),
            outputs={'collection': state}, parameters=parameters, required_parameters=required,
            effects=effects, acceptance=AcceptanceContract(partial_allowed=True),
            purpose='Receive selected originals as individually admitted ordered members with one cumulative byte allowance.')
        result.pop('cbr.command.' + identifier[4:], None)
    return result
