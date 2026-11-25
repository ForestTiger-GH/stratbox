"""Source-selected product graphs preserve every independently reusable stage."""
from __future__ import annotations

from stratbox.capabilities.model import Call, CollectCall, GraphBody, InputRef, OutputRef, ParameterRef, ScenarioDefinition


def product(source, definitions):
    """Bind domain stages as metadata; parameters remain explicit and inspectable."""
    by_id = {item.capability_id: item for item in definitions}
    from stratbox.capabilities.operations import definitions as standards
    by_id.update({item.capability_id: item for item in standards()})
    sid = source['series_id']
    family = source['family_id']
    steps, parameters, required, inputs, outputs = [], {}, [], {}, {}

    def call(step, identifier, bindings=None, *, initial=False, parameter_values=None):
        definition = by_id[identifier]
        bindings = dict(bindings or {})
        if initial:
            inputs.update(definition.inputs)
            bindings.update({name: InputRef(name) for name in definition.inputs})
        parameter_values = dict(parameter_values or {})
        arguments = dict(parameter_values)
        for name, default in definition.parameters.items():
            if name in parameter_values:
                continue
            public = step + '_' + name
            parameters[public] = default
            arguments[name] = ParameterRef(public)
        for name in definition.required_parameters:
            if name in parameter_values:
                continue
            public = step + '_' + name
            required.append(public)
            arguments[name] = ParameterRef(public)
        steps.append(Call(step, identifier, bindings, arguments))
        return definition

    def collect(step, producer, port, consumer, name):
        target = by_id[consumer].inputs[name]
        element = by_id[next(item.capability_id for item in steps if item.step_id == producer)].outputs[port]
        steps.append(CollectCall(step, (OutputRef(producer, port),), target, element))
        return OutputRef(step)

    if family == 'cbr.reporting_forms':
        extraction = call('extract', 'cbr.forms.extract', initial=True)
        outputs['extract'] = ('extract', 'flakes', extraction.outputs['flakes'])
        if sid.endswith(('.f134', '.f803')):
            profile = ('cbr.forms.134.fields.20120801' if sid.endswith('.f134') else 'cbr.forms.803.fields.20230701')
            call('basis', 'cbr.forms.published_field_bindings', {'flakes': OutputRef('extract', 'flakes')},
                parameter_values={'profile_id': profile})
            integrated = call('interpret', 'cbr.forms.extract_fields', {'flakes': OutputRef('extract', 'flakes')},
                parameter_values={'bindings': OutputRef('basis', 'bindings')})
            view = call('view', 'view.table', {'observations': OutputRef('interpret', 'observations')})
            rendered = call('render', 'render.table', {'view': OutputRef('view', 'view')})
            outputs['dataset'] = ('interpret', 'observations', integrated.outputs['observations'])
            outputs['view'] = ('view', 'view', view.outputs['view'])
            outputs['representation'] = ('render', 'representation', rendered.outputs['representation'])
        else:
            call('normalize', 'cbr.forms.normalize', {'flakes': OutputRef('extract', 'flakes')})
            snapshots = collect('snapshots', 'normalize', 'snapshot', 'cbr.forms.build_data', 'snapshots')
            calculated = call('calculate', 'cbr.forms.build_data', {'snapshots': snapshots})
            view = call('view', 'cbr.forms.build_views', {'data': OutputRef('calculate', 'data')})
            rendered = call('render', 'cbr.forms.render_workbook', {'views': OutputRef('view', 'views')})
            outputs['dataset'] = ('calculate', 'data', calculated.outputs['data'])
            outputs['view'] = ('view', 'views', view.outputs['views'])
            outputs['representation'] = ('render', 'workbook', rendered.outputs['workbook'])
    elif sid.endswith(('.debt_0105a', '.issuance_0104a')):
        prefix = 'cbr.industries.' + ('0105a' if sid.endswith('.debt_0105a') else '0104a')
        extraction = call('extract', prefix + '.parse', initial=True)
        flakes = collect('flakes', 'extract', 'file', prefix + '.integrate_flakes', 'flakes')
        integrated = call('integrate', prefix + '.integrate_flakes', {'flakes': flakes})
        view = call('view', prefix + '.build_pivots', {'stream': OutputRef('integrate', 'result')})
        render_id = prefix + '.render_pivots'
        render_input = next(iter(by_id[render_id].inputs))
        rendered = call('render', render_id, {render_input: OutputRef('view', 'pivots')})
        outputs.update(extract=('extract', 'file', extraction.outputs['file']),
            dataset=('integrate', 'result', integrated.outputs['result']),
            view=('view', 'pivots', view.outputs['pivots']),
            representation=('render', 'workbook', rendered.outputs['workbook']))
    elif family == 'cbr.service_network':
        extract_id = 'cbr.offices.parse' if sid.endswith('.bank_offices') else 'cbr.offices_reg.parse'
        extraction = call('extract', extract_id, initial=True)
        integrated = call('integrate', 'cbr.service_network.align', {'release': OutputRef('extract', 'release')})
        view = call('view', 'cbr.service_network.build_view', {'batch': OutputRef('integrate', 'batch')})
        rendered = call('render', 'cbr.service_network.render', {'view': OutputRef('view', 'view')})
        outputs.update(extract=('extract', 'release', extraction.outputs['release']),
            dataset=('integrate', 'batch', integrated.outputs['batch']),
            view=('view', 'view', view.outputs['view']),
            representation=('render', 'product', rendered.outputs['product']))
    elif family == 'cbr.project_finance':
        extraction = call('extract', 'cbr.escrow.parse', initial=True)
        flakes = collect('flakes', 'extract', 'file', 'cbr.escrow.integrate_flakes', 'flakes')
        integrated = call('integrate', 'cbr.escrow.integrate_flakes', {'flakes': flakes})
        view = call('view', 'cbr.escrow.build_views', {'dataset': OutputRef('integrate', 'dataset')})
        rendered = call('render', 'cbr.escrow.render_workbook', {'views': OutputRef('view', 'views')})
        outputs.update(extract=('extract', 'file', extraction.outputs['file']),
            dataset=('integrate', 'dataset', integrated.outputs['dataset']),
            view=('view', 'views', view.outputs['views']),
            representation=('render', 'workbook', rendered.outputs['workbook']))
    else:
        extraction = call('extract', 'cbr.tables.extract', initial=True)
        flakes = collect('flakes', 'extract', 'flake', 'cbr.statistics.align', 'flakes')
        integrated = call('integrate', 'cbr.statistics.align', {'flakes': flakes})
        view = call('view', 'cbr.statistics.build_view', {'dataset': OutputRef('integrate', 'dataset')})
        rendered = call('render', 'cbr.statistics.render_view', {'view': OutputRef('view', 'view')})
        outputs.update(extract=('extract', 'flake', extraction.outputs['flake']),
            dataset=('integrate', 'dataset', integrated.outputs['dataset']),
            view=('view', 'view', view.outputs['view']),
            representation=('render', 'representation', rendered.outputs['representation']))
    return ScenarioDefinition('scenario.' + sid + '.product', GraphBody(tuple(steps),
        {name: OutputRef(step, port) for name, (step, port, _) in outputs.items()},
        required_completions=tuple(step.step_id for step in steps)),
        inputs=inputs, outputs={name: contract for name, (_, _, contract) in outputs.items()},
        parameters=parameters, required_parameters=tuple(required),
        purpose='Prepare a versioned source extract, dataset, view and representation independently of acquisition or saving.')


def industry_renders(definitions):
    """Numerical preparation is an explicit predecessor of industry rendering."""
    from stratbox.capabilities.model import CommandDefinition, OperationDefinition, PortContract, ReuseContract, MapCall
    from stratbox.shared.data.processing import DataContract, DataRole
    result = dict(definitions)
    names = PortContract(DataContract('cbr.industry.source_name'), str)
    periods = PortContract(DataContract('cbr.industry.reference_periods'), tuple)
    code = PortContract(DataContract('cbr.industry.code'), str)
    for prefix in ('cbr.industries.0105a', 'cbr.industries.0104a'):
        stream = result[prefix + '.build_pivots'].inputs['stream']
        command = prefix + '.command.product_basis'
        basis = prefix + '.product_basis'
        result[command] = CommandDefinition(command, 'stratbox.domains.cbr.capability_methods:industry_product_basis',
            inputs={'stream': stream}, outputs={'industry_name_ru': names, 'reference_periods': periods},
            required_parameters=('industry_code',), reuse=ReuseContract(shareable=False))
        result[basis] = OperationDefinition(basis, GraphBody((
            Call('basis', command, {'stream': InputRef('stream')}, {'industry_code': ParameterRef('industry_code')}),
        ), {name: OutputRef('basis', name) for name in ('industry_name_ru', 'reference_periods')}),
            inputs={'stream': stream}, outputs={'industry_name_ru': names, 'reference_periods': periods},
            required_parameters=('industry_code',))
        single = prefix + '.render_industry'
        render = result[prefix + '.render_pivots']
        workbook = render.outputs['workbook']
        options = {'format': None} if prefix.endswith('0105a') else {'include_metadata_sheet': False}
        render_options = ({'format': ParameterRef('format')} if prefix.endswith('0105a') else
            {'industry_code': ParameterRef('industry_code'), 'industry_name_ru': OutputRef('basis', 'industry_name_ru'),
             'reference_periods': OutputRef('basis', 'reference_periods'),
             'include_metadata_sheet': ParameterRef('include_metadata_sheet')})
        result[single] = ScenarioDefinition(single, GraphBody((
            Call('basis', basis, {'stream': InputRef('stream')}, {'industry_code': ParameterRef('industry_code')}),
            Call('view', prefix + '.build_pivots', {'stream': InputRef('stream')},
                {'industry_code': ParameterRef('industry_code'), 'pivot': ParameterRef('pivot')}),
            Call('render', render.capability_id,
                {next(iter(render.inputs)): OutputRef('view', 'pivots')}, render_options),
        ), {'workbook': OutputRef('render', 'workbook')}, required_completions=('basis', 'view', 'render')),
            inputs={'stream': stream}, outputs={'workbook': workbook}, parameters=options,
            required_parameters=('industry_code', 'pivot'),
            purpose='Render one explicitly selected prepared industry; derived industry calculations run as separate operations.')
        item = 'scenario.' + prefix + '.render_item'
        result[item] = ScenarioDefinition(item, GraphBody((
            Call('product', single, {'stream': InputRef('stream')},
                {'industry_code': InputRef('item'), 'pivot': ParameterRef('pivot'),
                 **{name: ParameterRef(name) for name in options}}),
        ), {'value': OutputRef('product', 'workbook')}, required_completions=('product',)),
            inputs={'item': code, 'stream': stream}, outputs={'value': workbook}, parameters=options,
            required_parameters=('pivot',), purpose='Prepare one independently accepted industry workbook.')
        collection = PortContract(DataContract(prefix + '.workbooks', 1, DataRole.PRODUCTS), tuple, collection=True)
        multiple = prefix + '.render_industries'
        result[multiple] = ScenarioDefinition(multiple, GraphBody((
            MapCall('items', item, ParameterRef('industry_codes'), inputs={'stream': InputRef('stream')},
                parameters={'pivot': ParameterRef('pivot'), **{name: ParameterRef(name) for name in options}},
                window=4, max_items=100),
            CollectCall('workbooks', (OutputRef('items'),), collection, workbook),
        ), {'workbooks': OutputRef('workbooks')}, required_completions=('items', 'workbooks')),
            inputs={'stream': stream}, outputs={'workbooks': collection}, parameters=options,
            required_parameters=('industry_codes', 'pivot'),
            purpose='Render selected industry workbooks through independent bounded scenario occurrences.')
        for identifier in (single, multiple):
            result.pop('cbr.command.' + identifier[4:], None)
    return result
