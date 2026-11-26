"""Pure authoring-time graph recipes for scenarios purposes."""

from dataclasses import replace

from ...model import Call, GraphBody, InputRef, MapCall, OutputRef, TargetRef

from ...commands.standard import P, DATASET

def refresh(definition, values, parameters, record, catalog=None):
    definition=replace(definition,inputs={name:P(name,required=False) for name in ('material','physical','tables','dataset','index','listing','location','query','locator','baseline','issue','destination','product_destination')})
    steps=[]
    if 'dataset' in values:
        steps.append(Call('retained','operation.observations.validate',{'dataset':InputRef('dataset')}))
        dataset=OutputRef('retained','dataset')
    elif 'tables' in values:
        steps.append(Call('extract','operation.series.extract_any',{'tables':InputRef('tables'),'issue':InputRef('issue')}))
        dataset=OutputRef('extract','dataset')
    elif 'physical' in values:
        steps.append(Call('extract','operation.series.extract_any',{'physical':InputRef('physical'),'issue':InputRef('issue')}))
        dataset=OutputRef('extract','dataset')
    elif 'material' in values:
        steps.append(Call('extract','operation.series.extract_any',{'material':InputRef('material'),'issue':InputRef('issue')}))
        dataset=OutputRef('extract','dataset')
    else:
        publication=getattr(record,'publication',record)
        kind=getattr(publication,'kind',None)
        steps.append(Call('check','operation.source.check',{k:InputRef(k) for k in ('locator','query','baseline','index','listing','location')}))
        if kind in {'fixed','direct'}:
            # The checked direct representation is already the acquired original.
            steps.append(Call('extract','operation.series.extract_any',{'material':OutputRef('check','evidence'),'issue':InputRef('issue')}))
            dataset=OutputRef('extract','dataset')
        else:
            steps.extend((Call('acquire','operation.series.acquire',{'selection':OutputRef('check','selection')}),
                MapCall('extract','operation.series.extract_any',OutputRef('acquire','materials'),item_input='material',output_port='dataset'),
                Call('merge','operation.observations.merge',{'datasets':OutputRef('extract','items')})))
            dataset=OutputRef('merge','dataset')
    if parameters.get('align',False):
        steps.append(Call('align','operation.observations.align',{'dataset':dataset}));dataset=OutputRef('align','dataset')
    outputs={'dataset':dataset, 'assessment':replace(dataset, path='.'.join(filter(None, (dataset.path, 'assessment'))))}
    obligations=[]
    if parameters.get('retain',False) or 'destination' in values:
        steps.append(Call('retain','operation.dataset.retain',{'dataset':dataset,'destination':InputRef('destination')}))
        outputs['reference']=OutputRef('retain','reference');obligations.append('retain')
    if parameters.get('ingest',False):
        steps.append(Call('ingest','operation.dataset.ingest',{'dataset':dataset,'destination':InputRef('destination')}))
        outputs['reference']=OutputRef('ingest','reference');obligations.append('ingest')
    if parameters.get('product',False):
        steps.append(Call('product','operation.product.publish',{'dataset':dataset,'destination':InputRef('product_destination')}))
        outputs['product']=OutputRef('product','product');outputs['product_reference']=OutputRef('product','reference');obligations.append('product')
    ports={k:definition.outputs[k] for k in outputs}
    return replace(definition,outputs=ports,body=GraphBody(tuple(steps),outputs,required_completions=tuple(obligations)))

def analysis(definition, values, parameters, record, catalog=None):
    method=parameters.get('calculation')
    steps=[]
    if method:
        child=catalog.get(method)
        if child.kind!='operation': raise ValueError('analysis.operation_required')
        args={}
        for name in child.inputs:
            if name in values: args[name]=InputRef(name)
            elif name in {'observations','table'} and 'dataset' in values: args[name]=InputRef('dataset')
        steps.append(Call('calculate',method,args))
        outputs={name:OutputRef('calculate',name) for name in child.outputs}
        ports=dict(child.outputs)
    else:
        steps.append(Call('validate','operation.observations.validate',{'dataset':InputRef('dataset')}))
        outputs={'dataset':OutputRef('validate','dataset')};ports={'dataset':DATASET}
    obligations=[]
    if parameters.get('product',False) or 'destination' in values:
        if 'dataset' not in outputs: raise ValueError('analysis.product_requires_dataset_result')
        steps.append(Call('product','operation.product.publish',{'dataset':outputs['dataset'],'destination':InputRef('destination')},target=parameters.get('product_target',TargetRef())))
        outputs['product']=OutputRef('product','product');outputs['reference']=OutputRef('product','reference')
        ports.update(product=P('product'),reference=P('artifact'));obligations.append('product')
    return replace(definition,inputs={**definition.inputs,**(child.inputs if method else {}),'destination':P('destination',required=False)},outputs=ports,body=GraphBody(tuple(steps),outputs,required_completions=tuple(obligations)))
