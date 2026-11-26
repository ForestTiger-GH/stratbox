"""Pure authoring-time graph recipes for acquisition purposes."""

from dataclasses import replace

from ...model import Call, CollectCall, DispatchCall, GraphBody, InputRef, MapCall, OutputRef

from ...commands.standard import P

def material(definition, values, parameters, record, catalog=None):
    from ...plan import TemplateInput, ValueRef
    locator=values.get('locator')
    if isinstance(locator,(TemplateInput,ValueRef)):
        return replace(definition,inputs={**definition.inputs,'claim':P('claim',required=False)},body=GraphBody((DispatchCall('transport',InputRef('locator'),
            {'http':'operation.material.acquire_http','file':'operation.material.acquire_file'},
            inputs={key:InputRef(key) for key in ('claim','retained') if key in values},input_name='locator',output_port='material',selector_kind='acquisition_kind'),),
            {'material':OutputRef('transport','material')}))
    location=getattr(locator,'locator',locator)
    metadata=getattr(locator,'metadata',{})
    kind='file' if metadata.get('delivery') in {'file','filestore','delivered'} or isinstance(location,str) and not location.startswith(('https://','http://')) else 'http'
    args={k:InputRef(k) for k in ('locator','claim') if k in values}
    if kind=='http': args.update({k:InputRef(k) for k in ('query','retained') if k in values})
    return replace(definition,inputs={**definition.inputs,'claim':P('claim',required=False)},
        body=GraphBody((Call('acquire','operation.material.acquire_'+kind,args),),{'material':OutputRef('acquire','material')}))

def http(definition, values, parameters, record, catalog=None):
    from stratbox.shared.data.values import PublicationAsset
    from ...plan import TemplateInput
    identify={'material':OutputRef('fetch','material'),'inspection':OutputRef('inspect','inspection'),
        'request':OutputRef('fetch','request'),'evidence':OutputRef('fetch','evidence')}
    if isinstance(values.get('locator'),(PublicationAsset,TemplateInput)): identify['asset']=InputRef('locator')
    if 'claim' in values: identify['claim']=InputRef('claim')
    return replace(definition,inputs={**definition.inputs,'claim':P('claim',required=False)},body=GraphBody((
        Call('request','command.request.prepare',{'locator':InputRef('locator'),'query':InputRef('query')},{'role':'asset'}),
        Call('fetch','command.material.fetch',{'request':OutputRef('request','request'),'retained':InputRef('retained')}),
        Call('inspect','command.material.inspect',{'material':OutputRef('fetch','material')}),
        Call('identify','command.material.identify',identify)),
        {'material':OutputRef('identify','material')},required_checks=('identify',)))

def file(definition, values, parameters, record, catalog=None):
    from stratbox.shared.data.values import PublicationAsset
    from ...plan import TemplateInput
    identify={**definition.body.steps[-1].inputs,'evidence':OutputRef('read','evidence'),
        'inspection':OutputRef('inspect','inspection')}
    if isinstance(values.get('locator'),(PublicationAsset,TemplateInput)):
        identify['asset']=InputRef('locator')
    return replace(definition,body=replace(definition.body,steps=(*definition.body.steps[:-1],
        Call('inspect','command.material.inspect',{'material':OutputRef('read','material')}),
        replace(definition.body.steps[-1],inputs=identify))))

def receive(definition, values, parameters, record, catalog=None):
    from stratbox.shared.data.values import PublicationAsset
    from ...plan import TemplateInput
    identify=dict(definition.body.steps[-1].inputs)
    if isinstance(values.get('locator'),(PublicationAsset,TemplateInput)):
        identify['asset']=InputRef('locator')
    if 'claim' in values:
        identify['claim']=InputRef('claim')
    return replace(definition,inputs={**definition.inputs,'claim':P('claim',required=False)},
        body=replace(definition.body,steps=(*definition.body.steps[:-1],replace(definition.body.steps[-1],inputs=identify))))

def series(definition, values, parameters, record, catalog=None):
    if 'selection' in values:
        return replace(definition,body=GraphBody((
            MapCall('assets','operation.material.acquire',InputRef('selection',path='entries'),item_input='locator',output_port='material'),
        ),{'materials':OutputRef('assets','items'),'outcomes':OutputRef('assets','outcomes')}))
    return replace(definition,body=GraphBody((
        Call('asset','operation.material.acquire',{'locator':InputRef('locator'),'query':InputRef('query')}),
        CollectCall('collect',(OutputRef('asset','material'),)),
    ),{'materials':OutputRef('collect','items'),'outcomes':OutputRef('collect','outcomes')}))
