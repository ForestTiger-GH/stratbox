"""Pure authoring-time graph recipes for acquisition purposes."""

from dataclasses import replace

from ...model import Call, CollectCall, DispatchCall, GraphBody, InputRef, MapCall, OutputRef

from ...commands.standard import P

def material(definition, values, parameters, record, catalog=None):
    from ...plan import TemplateInput, ValueRef
    locator=values.get('locator')
    if isinstance(locator,(TemplateInput,ValueRef)):
        return replace(definition,body=GraphBody((DispatchCall('transport',InputRef('locator'),
            {'http':'operation.material.acquire_http','file':'operation.material.acquire_file'},
            inputs={'claim':InputRef('claim')},input_name='locator',output_port='material',selector_kind='acquisition_kind'),),
            {'material':OutputRef('transport','material')}))
    location=getattr(locator,'locator',locator)
    metadata=getattr(locator,'metadata',{})
    kind='file' if metadata.get('delivery') in {'file','filestore','delivered'} or isinstance(location,str) and not location.startswith(('https://','http://')) else 'http'
    args={k:InputRef(k) for k in ('locator','claim') if k in values}
    if kind=='http': args.update({k:InputRef(k) for k in ('query',) if k in values})
    return replace(definition,inputs={**definition.inputs,'claim':P('claim',required=False)},
        body=GraphBody((Call('acquire','operation.material.acquire_'+kind,args),),{'material':OutputRef('acquire','material')}))

def http(definition, values, parameters, record, catalog=None):
    from stratbox.shared.data.values import PublicationAsset
    from ...plan import TemplateInput
    original=definition.body
    identify={**original.steps[-1].inputs,'request':OutputRef('request','request'),'evidence':OutputRef('fetch','evidence')}
    if isinstance(values.get('locator'),(PublicationAsset,TemplateInput)): identify['asset']=InputRef('locator')
    if 'claim' in values: identify['claim']=InputRef('claim')
    return replace(definition,inputs={**definition.inputs,'claim':P('claim',required=False)},body=replace(original,steps=(*original.steps[:-1],replace(original.steps[-1],inputs=identify))))

def file(definition, values, parameters, record, catalog=None):
    from stratbox.shared.data.values import PublicationAsset
    from ...plan import TemplateInput
    identify={**definition.body.steps[-1].inputs,'evidence':OutputRef('read','evidence')}
    if isinstance(values.get('locator'),(PublicationAsset,TemplateInput)):
        identify['asset']=InputRef('locator')
    return replace(definition,body=replace(definition.body,steps=(*definition.body.steps[:-1],
        replace(definition.body.steps[-1],inputs=identify))))

def series(definition, values, parameters, record, catalog=None):
    if 'selection' in values:
        return replace(definition,body=GraphBody((
            MapCall('assets','operation.material.acquire',InputRef('selection',path='entries'),item_input='locator',output_port='material'),
        ),{'materials':OutputRef('assets','items')}))
    return replace(definition,body=GraphBody((
        Call('asset','operation.material.acquire',{'locator':InputRef('locator'),'query':InputRef('query')}),
        CollectCall('collect',(OutputRef('asset','material'),)),
    ),{'materials':OutputRef('collect','items')}))
