"""Typed CBR capabilities backed by direct, separately executable methods."""
from __future__ import annotations

from functools import lru_cache

from stratbox.capabilities.catalog import CatalogContribution, ProcessingGroup, ProfileDefinition, RecipeDefinition, SchemaDefinition
from stratbox.capabilities.model import AcceptanceContract, Call, GraphBody, InputRef, OperationDefinition, OutputRef, ParameterRef, PortContract, CommandDefinition, ReuseContract, ScenarioDefinition, MapCall, CollectCall
from stratbox.shared.data.processing import DataContract, DataRole
from .capability_declarations import DECLARATIONS

_INDEX = {item['id']: item for item in DECLARATIONS}


def _port(item):
    schema = item['contract']
    if schema['schema_id'] in {'material.payload', 'source.payload'}:
        schema = {'schema_id': 'material.bytes', 'version': 1, 'role': 'originals'}
    contract = DataContract(schema['schema_id'], schema.get('version', 1),
        DataRole(schema['role']) if schema.get('role') else None)
    return PortContract(contract,
        required=item.get('required', True), qualifications=frozenset(item.get('qualifications', ())),
        expected_coverage=frozenset(item.get('coverage', ())), collection=item.get('collection', False), alternatives=tuple(
            DataContract(value['schema_id'], value.get('version', 1), DataRole(value['role']) if value.get('role') else None)
            for value in item.get('alternatives', ())), outcomes=frozenset(item.get('outcomes', ('succeeded',))))


def _ports(item, name):
    return {port['name']: _port(port) for port in item[name]}


def _body(item, command_id):
    outputs = _ports(item, 'outputs')
    return GraphBody((Call('execute', command_id,
        {name: InputRef(name) for name in _ports(item, 'inputs')},
        {name: ParameterRef(name) for name in item['parameters'] if '.' not in name}),),
        {name: OutputRef('execute', name) for name in outputs}, required_completions=('execute',))


def _standard(item):
    command_id = 'cbr.command.' + item['id'][4:]
    inputs, outputs = _ports(item, 'inputs'), _ports(item, 'outputs')
    parameters = {name: None for name in item['parameters'] if name not in item['required'] and '.' not in name}
    effects = frozenset(item['effects'])
    module, function = item['method'].split(':')
    command = CommandDefinition(command_id, module + ':capability_' + function,
        inputs=inputs, outputs=outputs, fixed={'definition_id': item['id']},
        parameters=parameters, required_parameters=item['required'],
        required_capabilities=frozenset(item['providers']), optional_capabilities=frozenset(item.get('optional', ())), effects=effects,
        reuse=ReuseContract(shareable=False, effects=effects),
        acceptance=AcceptanceContract(partial_allowed=item['partial']), summary=item['summary'])
    operation = OperationDefinition(item['id'], _body(item, command_id),
        inputs=inputs, outputs=outputs, parameters=parameters, required_parameters=item['required'],
        effects=effects, acceptance=AcceptanceContract(partial_allowed=item['partial']), summary=item['summary'])
    return command, operation


def _composed(definitions):
    """Preserve logical boundaries while exposing intermediate accepted stages."""
    by_id = {item.capability_id: item for item in definitions}
    def replace(identifier, body):
        original = by_id[identifier]
        by_id.pop('cbr.command.' + identifier[4:], None)
        by_id[identifier] = ScenarioDefinition(identifier, body, inputs=original.inputs,
            outputs=original.outputs, parameters=original.parameters, required_parameters=original.required_parameters,
            effects=original.effects, acceptance=original.acceptance, summary=original.summary,
            purpose=original.summary)
    replace('cbr.forms.parse', GraphBody((
        Call('extract', 'cbr.forms.extract', {'source': InputRef('source')}, {'key': ParameterRef('key')}),
        Call('normalize', 'cbr.forms.normalize', {'flakes': OutputRef('extract', 'flakes')}),
    ), {'snapshot': OutputRef('normalize', 'snapshot')}))
    replace('cbr.forms.build_data', GraphBody((
        Call('version', 'cbr.forms.source_version', {'snapshots': InputRef('snapshots')}),
        Call('align', 'cbr.forms.align', {'snapshots': InputRef('snapshots')},
            {'dataset_id': 'cbr.forms.model-source', 'version_id': OutputRef('version', 'version_id'), 'periods': ParameterRef('periods')}),
        Call('prepare', 'cbr.forms.prepare_model_inputs', {'batch': OutputRef('align', 'batch')}),
        Call('calculate', 'cbr.forms.calculate', {'inputs': OutputRef('prepare', 'inputs')},
            {name: ParameterRef(name) for name in ('banks', 'model', 'selection_profile')}),
    ), {'data': OutputRef('calculate', 'data')}))
    # The immutable source bundle remains complete when a later view is narrow.
    replace('cbr.sors.restore_from_originals', GraphBody((
        Call('prepare', 'cbr.sors.prepare_from_originals', {'sources': InputRef('sources')}, {'config': ParameterRef('config')}),
        Call('restore', 'cbr.sors.restore', {'bundle': OutputRef('prepare', 'bundle')}, {'config': ParameterRef('config')}),
    ), {'result': OutputRef('restore', 'result')}))
    replace('cbr.offices.capture', GraphBody((
        Call('acquire', 'cbr.offices.acquire', parameters={name: ParameterRef(name) for name in ('capture_zone', 'baseline')}),
        Call('parse', 'cbr.offices.parse', {'source': OutputRef('acquire', 'payload')},
            {'captured_on': OutputRef('acquire', 'capture_date')}),
    ), {name: OutputRef('parse', name) for name in ('release', 'representation')}))
    replace('cbr.offices_reg.capture', GraphBody((
        Call('acquire', 'cbr.offices_reg.acquire', parameters={name: ParameterRef(name) for name in ('as_of', 'url')}),
        Call('parse', 'cbr.offices_reg.parse', {'source': OutputRef('acquire', 'payload')},
            {'as_of': ParameterRef('as_of')}),
    ), {name: OutputRef('parse', name) for name in ('release', 'candidates', 'representation')},
        required_completions=('acquire', 'parse')))
    # History expands independent source interpretations through the session's
    # bounded admission path, then integrates the accepted collection.
    for prefix, parser in (('cbr.industries.0105a', 'parse_debt_item'),
                           ('cbr.industries.0104a', 'parse_issuance_item'),
                           ('cbr.escrow', 'parse_escrow_item')):
        industrial = prefix != 'cbr.escrow'
        target = prefix + ('.build_stream' if industrial else '.build_history')
        parse = by_id[prefix + '.parse']
        integrate = by_id[prefix + '.integrate_flakes']
        output = parse.outputs['file']
        element_inputs = {'item': PortContract()}
        options = {'selection': None} if industrial else {}
        command_id = prefix + '.command.parse_item'
        operation_id = prefix + '.parse_item'
        scenario_id = 'scenario.' + prefix + '.parse_item'
        by_id[command_id] = CommandDefinition(command_id,
            'stratbox.domains.cbr.capability_methods:' + parser,
            inputs=element_inputs, outputs={'value': output}, parameters=options,
            resources={'parse': 1}, reuse=ReuseContract(shareable=False))
        by_id[operation_id] = OperationDefinition(operation_id, GraphBody((
            Call('parse', command_id, {'item': InputRef('item')},
                {name: ParameterRef(name) for name in options}),
        ), {'value': OutputRef('parse')}), inputs=element_inputs, outputs={'value': output}, parameters=options)
        by_id[scenario_id] = ScenarioDefinition(scenario_id, GraphBody((
            Call('extract', operation_id, {'item': InputRef('item')},
                {name: ParameterRef(name) for name in options}),
        ), {'value': OutputRef('extract')}), inputs=element_inputs, outputs={'value': output}, parameters=options,
            purpose='Interpret one explicitly supplied original with its source context.')
        original = by_id[target]
        collection = integrate.inputs['flakes']
        replace(target, GraphBody((
            MapCall('extract', scenario_id, InputRef('sources'), window=4, max_items=1000,
                parameters={name: ParameterRef(name) for name in options}),
            CollectCall('flakes', (OutputRef('extract'),), collection, output),
            Call('integrate', integrate.capability_id, {'flakes': OutputRef('flakes')},
                {'expected_report_dates': ParameterRef('expected_report_dates')} if industrial else
                {'coverage': ParameterRef('coverage')}),
        ), {name: OutputRef('integrate', name) for name in original.outputs}))
        from dataclasses import replace as amend
        by_id[target] = amend(by_id[target], parameters={**options,
            **({'expected_report_dates': None} if industrial else {'coverage': None})})
    from .capability_collections import assemble
    from .capability_products import industry_renders
    return tuple(assemble(industry_renders(by_id)).values())


@lru_cache(maxsize=1)
def contribution():
    from stratbox.domains.registry.declarations import source_documents, source_route
    from stratbox.core.resources import iter_resources, read_document
    definitions = tuple(value for item in DECLARATIONS for value in _standard(item))
    definitions = list(_composed(definitions))
    flakes = PortContract(DataContract('cbr.forms.flakes', 1, DataRole.EXTRACTS))
    from stratbox.shared.data.observations import ObservationBatch
    batch = PortContract(DataContract('observations.batch', 1, DataRole.EXTRACTS), ObservationBatch)
    definitions.extend((
        CommandDefinition('cbr.command.forms.extract_fields',
            'stratbox.domains.cbr.capability_methods:extract_form_fields',
            inputs={'flakes': flakes}, outputs={'observations': batch}, parameters={'include_deleted': False},
            required_parameters=('bindings',), reuse=ReuseContract(shareable=False)),
        OperationDefinition('cbr.forms.extract_fields', GraphBody((
            Call('interpret', 'cbr.command.forms.extract_fields', {'flakes': InputRef('flakes')},
                {'bindings': ParameterRef('bindings'), 'include_deleted': ParameterRef('include_deleted')}),
        ), {'observations': OutputRef('interpret', 'observations')}),
            inputs={'flakes': flakes}, outputs={'observations': batch}, parameters={'include_deleted': False},
            required_parameters=('bindings',)),
    ))
    bindings = PortContract(DataContract('cbr.forms.field_bindings'), tuple)
    definitions.extend((
        CommandDefinition('cbr.command.forms.published_field_bindings',
            'stratbox.domains.cbr.capability_methods:bind_published_form_fields',
            inputs={'flakes': flakes}, outputs={'bindings': bindings},
            required_parameters=('profile_id', 'unit', 'scale', 'period'), reuse=ReuseContract(shareable=False)),
        OperationDefinition('cbr.forms.published_field_bindings', GraphBody((
            Call('bind', 'cbr.command.forms.published_field_bindings', {'flakes': InputRef('flakes')},
                {name: ParameterRef(name) for name in ('profile_id', 'unit', 'scale', 'period')}),
        ), {'bindings': OutputRef('bind', 'bindings')}), inputs={'flakes': flakes}, outputs={'bindings': bindings},
            required_parameters=('profile_id', 'unit', 'scale', 'period')),
    ))
    snapshots = _ports(_INDEX['cbr.forms.build_data'], 'inputs')['snapshots']
    version = PortContract(DataContract('cbr.forms.source_version'), str)
    definitions.extend((
        CommandDefinition('cbr.command.forms.source_version', 'stratbox.domains.cbr.capability_methods:form_source_version',
            inputs={'snapshots': snapshots}, outputs={'version_id': version}, reuse=ReuseContract(shareable=False)),
        OperationDefinition('cbr.forms.source_version', GraphBody((
            Call('version', 'cbr.command.forms.source_version', {'snapshots': InputRef('snapshots')}),
        ), {'version_id': OutputRef('version', 'version_id')}), inputs={'snapshots': snapshots}, outputs={'version_id': version}),
    ))
    # Standalone validation and calculation stages consume retained values.
    def technical(identifier, method, input_ports, output_ports, options=None, required=()):
        command = 'cbr.command.' + identifier[4:]
        options = dict(options or {})
        definitions.extend((
            CommandDefinition(command, 'stratbox.domains.cbr.capability_methods:' + method,
                inputs=input_ports, outputs=output_ports, parameters=options, required_parameters=required,
                reuse=ReuseContract(shareable=False)),
            OperationDefinition(identifier, GraphBody((
                Call('evaluate', command, {name: InputRef(name) for name in input_ports},
                    {name: ParameterRef(name) for name in (*options, *required)}),
            ), {name: OutputRef('evaluate', name) for name in output_ports}, required_checks=('evaluate',)),
                inputs=input_ports, outputs=output_ports, parameters=options, required_parameters=required),
        ))
    technical('cbr.forms.validate', 'validate_form_flakes', {'flakes': flakes}, {'flakes': flakes})
    for prefix, method in (('cbr.offices', 'validate_bank_offices'),
                           ('cbr.offices_reg', 'validate_territorial_offices')):
        release = _ports(_INDEX[prefix + '.parse'], 'outputs')['release']
        technical(prefix + '.validate', method, {'release': release}, {'release': release})
    for prefix, method in (('cbr.industries.0105a', 'validate_debt_flake'),
                           ('cbr.industries.0104a', 'validate_issuance_flake')):
        parsed = _ports(_INDEX[prefix + '.parse'], 'outputs')['file']
        technical(prefix + '.validate', method, {'file': parsed}, {'file': parsed})
    technical('cbr.escrow.calculate_change', 'escrow_change',
        {'dataset': _ports(_INDEX['cbr.escrow.align_observations'], 'inputs')['dataset']},
        {'observations': PortContract(DataContract('cbr.escrow.changes', 1, DataRole.INTEGRATED), ObservationBatch)},
        {'method': 'absolute', 'geography': ()}, ('before', 'after', 'metric_ids'))
    from .capability_workbooks import assemble as workbook_stages
    definitions = list(workbook_stages({item.capability_id: item for item in definitions}))
    profiles = tuple(ProfileDefinition(value['profile_id'], value['declaration'])
        for value in (read_document(path) for path in iter_resources('cbr', 'profiles')))
    from .tables.reporting_forms.field_observations import PUBLISHED_FIELD_PROFILES
    profiles += tuple(ProfileDefinition(identifier, data) for identifier, data in PUBLISHED_FIELD_PROFILES.items())
    groups, recipes = [], []
    for source in source_documents('cbr'):
        sid = source['series_id']
        from .capability_products import product
        product_definition = product(source, definitions)
        definitions.append(product_definition)
        route = source_route(sid)
        extraction = next(step.capability_id for step in product_definition.body.steps if step.step_id == 'extract')
        groups.append(ProcessingGroup(sid + '.processing', source_ids=(sid,), representations=tuple(source['formats'])))
        if extraction:
            for representation in source['formats']:
                binding = next((value for value in route.operations if value.operation_id == extraction), None)
                if binding is not None and binding.formats and representation not in binding.formats:
                    continue
                recipes.append(RecipeDefinition('recipe.' + sid + '.' + representation + '.product',
                    'source.product', product_definition.capability_id, selection={'source_id': sid, 'representation': representation}))
                recipes.append(RecipeDefinition('recipe.' + sid + '.' + representation + '.extract',
                    'source.extract', extraction, selection={'source_id': sid, 'representation': representation}))
    schemas = {}
    for item in DECLARATIONS:
        for port in (*item['inputs'], *item['outputs']):
            contract = port['contract']
            schemas.setdefault(contract['schema_id'], set()).add(contract.get('version', 1))
    return CatalogContribution(definitions=tuple(definitions), profiles=profiles, groups=tuple(groups),
        recipes=tuple(recipes), schemas=tuple(SchemaDefinition(identifier, data={'versions': tuple(sorted(versions))})
            for identifier, versions in sorted(schemas.items())))


def dispositions():
    """Every declaration has one canonical owner and one direct implementation."""
    canonical = {item.capability_id: item for item in contribution().definitions}
    return tuple({'source_id': item['id'], 'capability_id': item['id'],
        'kind': canonical[item['id']].kind, 'status': 'migrated',
        'implementation': item['method']} for item in DECLARATIONS)


def stage_matrix():
    from stratbox.domains.registry.declarations import source_documents, source_route
    result = []
    shared = {'preserve': ('preserve.material',), 'ingest': ('ingest.observations',),
              'publish': ('publish.release',), 'inspect': ('cbr.describe_source',)}
    for source in source_documents('cbr'):
        sid = source['series_id']
        route = source_route(sid)
        for stage in ('discover', 'inspect', 'acquire', 'preserve', 'readable', 'extract', 'read_extract',
                      'compare', 'integrate', 'ingest', 'calculate', 'view', 'render', 'publish', 'validate'):
            capabilities = tuple(dict.fromkeys(binding.operation_id for binding in route.operations
                if binding.operation_id in _INDEX and stage in _INDEX[binding.operation_id]['stages']))
            if stage == 'read_extract':
                capabilities = tuple(binding.operation_id for binding in route.operations
                    if binding.operation_id in _INDEX and any(token in binding.operation_id
                        for token in ('.read_', '.restore')))
            if stage == 'validate' and not capabilities:
                if source['family_id'] == 'cbr.reporting_forms':
                    capabilities = ('cbr.forms.validate',)
                elif source['family_id'] == 'cbr.service_network':
                    capabilities = ('cbr.offices.validate' if sid.endswith('.bank_offices') else 'cbr.offices_reg.validate',)
                elif sid.endswith(('.debt_0105a', '.issuance_0104a')):
                    capabilities = ('cbr.industries.0105a.validate' if sid.endswith('.debt_0105a') else 'cbr.industries.0104a.validate',)
            if stage == 'readable' and not capabilities and sid.endswith(('.debt_0105a', '.issuance_0104a')):
                capabilities = ('convert.readable',)
            if stage == 'calculate' and source['family_id'] == 'cbr.project_finance':
                capabilities = ('cbr.escrow.calculate_change',)
            if sid.endswith(('.f134', '.f803')) and not capabilities:
                capabilities = {'integrate': ('cbr.forms.published_field_bindings', 'cbr.forms.extract_fields', 'align.observations'),
                    'calculate': ('cbr.forms.extract_fields', 'calculate.ratio'),
                    'view': ('cbr.forms.extract_fields', 'view.table')}.get(stage, ())
            selected = capabilities or shared.get(stage, ())
            result.append({'source_id': sid, 'stage': stage, 'capabilities': selected,
                'state': 'direct' if capabilities else 'shared' if stage in shared else 'requires_reviewed_binding',
                'qualifications': route.qualifications,
                'requirements': ('Published layout/field edition and explicit measurement/period contracts apply; '
                    'source-level calculations do not assert an unreviewed financial model.'),
                'formats': tuple(source['formats'])})
    return tuple(result)
