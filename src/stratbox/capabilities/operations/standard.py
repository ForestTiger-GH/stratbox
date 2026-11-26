"""Source-neutral operation graphs with independently callable entrances."""
from ..model import *
from ..commands.standard import BY_ID, P, DATASET, MATERIAL, PHYSICAL


def op(identifier, inputs, steps, outputs, *, parameters=None, checks=(), effects=(), entrances=None, contracts=None):
    ports = {}
    for name, ref in outputs.items():
        step = next(s for s in steps if s.step_id == ref.step)
        if isinstance(step, Call) and step.capability_id in BY_ID:
            ports[name] = BY_ID[step.capability_id].outputs[ref.port]
        else:
            ports[name] = (contracts or {}).get(name, P('typed_value'))
    return OperationDefinition(identifier, inputs=inputs, outputs=ports, parameters=parameters or {},
        entrances=entrances or {}, body=GraphBody(tuple(steps), outputs, checks, effects))

SOURCE_CHECK = op('operation.source.check',
    {'locator': P('locator', required=False), 'query': P('query', required=False), 'baseline': P('baseline', required=False)},
    (Call('request', 'command.request.prepare', {'locator': InputRef('locator'), 'query': InputRef('query')}, {'mode': 'index'}),
     Call('fetch', 'command.material.fetch', {'request': OutputRef('request','request')}),
     Call('scan', 'command.publication.scan', {'index': OutputRef('fetch','material')}),
     Call('select', 'command.issue.select', {'listing': OutputRef('scan','listing'), 'query': InputRef('query')}),
     Call('assess', 'command.source.assess', {'evidence': OutputRef('scan','listing'), 'baseline': InputRef('baseline')})),
    {'assessment': OutputRef('assess','assessment'), 'evidence': OutputRef('fetch','material'), 'selection': OutputRef('select','selection')})

ACQUIRE = op('operation.series.acquire', {'locator': P('locator', required=False), 'query': P('query', required=False)},
    (Call('request', 'command.request.prepare', {'locator': InputRef('locator'), 'query': InputRef('query')}, {'mode': 'asset'}),
     Call('fetch', 'command.material.fetch', {'request': OutputRef('request','request')}),
     Call('identify', 'command.material.identify', {'material': OutputRef('fetch','material')})),
    {'material': OutputRef('identify','material')})


def extraction(identifier, decoder):
    steps = (Call('decode', decoder, {'material': InputRef('material')}),
             Call('select','command.table.extract',{'physical': OutputRef('decode','physical')}),
             Call('interpret','command.table.interpret',{'tables':OutputRef('select','tables'),'issue':InputRef('issue')}),
             Call('validate','command.observations.validate',{'dataset':OutputRef('interpret','dataset')}))
    return op(identifier, {'material': PortContract('material', MATERIAL.value_type, required=False),
        'physical': PortContract('physical', PHYSICAL.value_type, required=False),
        'tables': PortContract('tables', required=False), 'issue': P('issue', required=False)}, steps,
        {'dataset': OutputRef('validate','dataset'), 'assessment': OutputRef('validate','assessment')}, checks=('validate',),
        entrances={'physical':OutputRef('decode','physical'),'tables':OutputRef('select','tables')})

EXTRACT_WORKBOOK = extraction('operation.series.extract_workbook','command.workbook.decode')
EXTRACT_DOCUMENT = extraction('operation.series.extract_document','command.document.decode')
EXTRACT_JSON = extraction('operation.series.extract_structured.json','command.json.decode')
EXTRACT_CSV = extraction('operation.series.extract_structured.csv','command.csv.decode')
EXTRACT_DBF = extraction('operation.series.extract_structured.dbf','command.dbf.decode')

ADJUST = op('operation.timeseries.adjust', {'series': BY_ID['command.timeseries.adjust'].inputs['series']},
    (Call('validate','command.timeseries.validate',{'series':InputRef('series')}),
     Call('estimate','command.timeseries.adjust',{'series':InputRef('series')}, depends_on=('validate',)),
     Call('diagnose','command.timeseries.diagnose',{'adjustment':OutputRef('estimate','adjustment')})),
    {'adjustment':OutputRef('estimate','adjustment'),'diagnostics':OutputRef('diagnose','diagnostics')}, checks=('validate','diagnose'))

TABLE_CALCULATION = op('operation.calculation.apply_table', {'table': DATASET},
    (Call('partition','command.timeseries.partition',{'dataset':InputRef('table')}),
     MapCall('apply','operation.timeseries.adjust',OutputRef('partition','items'),item_input='series',output_port='adjustment')),
    {'results':OutputRef('apply','items')}, contracts={'results':P('calculation_batch',tuple)})

_CLOSURE = GraphBody((
    Call('propagate','command.bounds.propagate',{'graph':InputRef('graph'),'state':InputRef('state')}),
    Call('inherit','command.facts.inherit',{'graph':InputRef('graph'),'state':OutputRef('propagate','state')}),
    Call('reconcile','command.facts.reconcile',{'state':OutputRef('propagate','state'),'candidates':OutputRef('inherit','candidates')}),
), {'state':OutputRef('reconcile','state')})
_WAVE = GraphBody((
    RepeatUntil('closure',_CLOSURE,InputRef('state'),inputs={'graph':InputRef('graph')}),
    Call('compile','command.model.compile',{'graph':InputRef('graph'),'state':OutputRef('closure','state')}),
    Call('feasible','command.model.feasibility',{'problem':OutputRef('compile','problem')}),
    Call('optimize','command.bounds.optimize',{'problem':OutputRef('compile','problem'),'feasibility':OutputRef('feasible','feasibility'),'state':OutputRef('closure','state')}),
    Call('reconcile','command.facts.reconcile',{'state':OutputRef('closure','state'),'optimization':OutputRef('optimize','optimization')}),
), {'state':OutputRef('reconcile','state')})
RESTORE = op('operation.constraints.restore', {'datasets':P('model_sources')},
    (Call('inputs','command.model.inputs',{'datasets':InputRef('datasets')}),
     Call('build','command.constraints.build',{'bundle':OutputRef('inputs','bundle')}),
     RepeatUntil('waves',_WAVE,OutputRef('build','state'),stop=SemanticPredicate('optimization_complete','equals',True),inputs={'graph':OutputRef('build','graph')}),
     Call('compile','command.model.compile',{'graph':OutputRef('build','graph'),'state':OutputRef('waves','state')}),
     Call('feasible','command.model.feasibility',{'problem':OutputRef('compile','problem')}),
     Call('certify','command.values.certify',{'state':OutputRef('waves','state'),'feasibility':OutputRef('feasible','feasibility')}),
     Call('assemble','command.observations.assemble',{'values':OutputRef('certify','values')})),
    {'dataset':OutputRef('assemble','dataset')}, checks=('feasible','certify'))

PUBLISH_PRODUCT = op('operation.product.publish', {'dataset':DATASET, 'destination':P('destination',required=False)},
    (Call('view','command.view.prepare',{'dataset':InputRef('dataset')}),
     Call('render','command.product.render',{'view':OutputRef('view','view')}),
     Call('save','command.artifact.commit',{'material':OutputRef('render','product'),'destination':InputRef('destination')})),
    {'product':OutputRef('render','product'),'reference':OutputRef('save','reference')},effects=('save',),entrances={'view':OutputRef('view','view')})

RELEASE = op('operation.release.publish', {'members':P('accepted_members',tuple), 'expected_token':P('state_token',required=False)},
    (Call('assemble','command.release.assemble',{'members':InputRef('members')}),
     Call('publish','command.release.publish',{'manifest':OutputRef('assemble','manifest'),'expected_token':InputRef('expected_token')})),
    {'manifest':OutputRef('assemble','manifest'),'receipt':OutputRef('publish','receipt')},effects=('publish',))

OPERATIONS = (SOURCE_CHECK,ACQUIRE,EXTRACT_WORKBOOK,EXTRACT_DOCUMENT,EXTRACT_JSON,EXTRACT_CSV,EXTRACT_DBF,ADJUST,TABLE_CALCULATION,RESTORE,PUBLISH_PRODUCT,RELEASE)
