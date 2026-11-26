"""Visible standard recipe choices driven by inputs and declared representation."""
from dataclasses import replace
from ..model import *
from ..commands.standard import P, DATASET, MATERIAL, PHYSICAL
from ..operations.standard import extraction

_FORMATS={
    'xlsx':'operation.series.extract_workbook','xls':'operation.series.extract_workbook',
    'xlsb':'operation.series.extract_workbook','xlsm':'operation.series.extract_workbook',
    'json':'operation.series.extract_structured.json','csv':'operation.series.extract_structured.csv',
    'dbf':'operation.series.extract_structured.dbf','pdf':'operation.series.extract_document',
    'docx':'operation.series.extract_document','doc':'operation.series.extract_document',
    'zip':'operation.series.extract_archive','rar':'operation.series.extract_archive',
}
_MIME={'application/pdf':'pdf','application/json':'json','text/csv':'csv','application/zip':'zip',
       'application/vnd.rar':'rar','application/x-rar-compressed':'rar',
       'application/vnd.ms-excel':'xls','application/msword':'doc',
       'application/vnd.ms-excel.sheet.binary.macroenabled.12':'xlsb',
       'application/vnd.ms-excel.sheet.macroenabled.12':'xlsm',
       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':'xlsx',
       'application/vnd.openxmlformats-officedocument.wordprocessingml.document':'docx'}


def declared_format(values,parameters,record):
    explicit=parameters.get('format',parameters.get('representation'))
    if explicit: return str(explicit).lower()
    physical=values.get('physical')
    physical_formats={'WorkbookEvidence':'xlsx','DocumentEvidence':'pdf','JsonEvidence':'json','DbfEvidence':'dbf','TableEvidenceSet':'csv'}
    if physical is not None and type(physical).__name__ in physical_formats: return physical_formats[type(physical).__name__]
    material=values.get('material')
    material=getattr(material,'material',material)
    if material is not None and not type(material).__name__.endswith('Input'):
        media=(getattr(material,'media_type','') or '').split(';',1)[0].strip().lower()
        if media in _MIME: return _MIME[media]
    publication=getattr(record,'publication',record)
    formats=getattr(publication,'formats',())
    if len(formats)==1: return next(iter(formats))
    return None


def recipe(definition,values,parameters,record,catalog=None):
    identifier=definition.id
    fmt=declared_format(values,parameters,record)
    if identifier=='operation.series.extract_structured':
        if fmt not in {'json','csv','dbf'}: raise ValueError('recipe.structured_format_required')
        return replace(extraction(identifier,'command.'+fmt+'.decode'),id=identifier)
    if identifier=='operation.series.extract_document' and fmt=='doc':
        base=extraction(identifier,'command.document.decode')
        steps=(Call('convert','command.document.convert',{'material':InputRef('material')}),
               Call('decode','command.document.decode',{'material':OutputRef('convert','material')}),*base.body.steps[1:])
        return replace(base,body=replace(base.body,steps=steps))
    if identifier=='operation.series.extract_any':
        if 'tables' in values:
            return replace(definition, body=GraphBody((
                Call('interpret','command.table.interpret',{'tables':InputRef('tables'),'issue':InputRef('issue')}),
                Call('validate','command.observations.validate',{'dataset':OutputRef('interpret','dataset')}),
            ), {'dataset':OutputRef('validate','dataset')}, required_checks=('validate',)))
        if fmt in _FORMATS:
            return replace(definition,body=GraphBody((Call('extract',_FORMATS[fmt],
                {'material':InputRef('material'),'physical':InputRef('physical'),'issue':InputRef('issue')},parameters={'format':fmt}),),
                {'dataset':OutputRef('extract','dataset')}))
        depth=int(parameters.get('archive_depth',0))
        limit=int(parameters.get('max_archive_depth',1))
        if not 0<=depth<=limit or not 0<=limit<=8: raise ValueError('recipe.archive_depth_limit')
        alternatives={key:value for key,value in _FORMATS.items() if key not in {'zip','rar'} or depth<limit}
        return replace(definition,body=GraphBody((DispatchCall('format',InputRef('material'),alternatives,
            inputs={'issue':InputRef('issue')}),),{'dataset':OutputRef('format','dataset')}))
    if identifier=='operation.series.extract_archive':
        publication=getattr(record,'publication',record)
        settings=getattr(publication,'settings',None)
        archive_mode=getattr(publication,'archive_mode',None) or (settings.get('archive_mode') if hasattr(settings,'get') else getattr(settings,'archive_mode',None))
        if archive_mode=='workbook_collection':
            return replace(definition,body=GraphBody((
                Call('unpack','command.archive.unpack',{'material':InputRef('material')}),
                Call('members','command.material.select',{'materials':OutputRef('unpack','members')},{'formats':('xls','xlsx','xlsb','xlsm')}),
                MapCall('decode','command.workbook.decode',OutputRef('members','materials'),item_input='material',output_port='physical'),
                Call('select','command.table.extract',{'physical':OutputRef('decode','items')}),
                Call('interpret','command.table.interpret',{'tables':OutputRef('select','tables'),'issue':InputRef('issue')}),
                Call('validate','command.observations.validate',{'dataset':OutputRef('interpret','dataset')}),
            ),{'dataset':OutputRef('validate','dataset')},required_checks=('validate',)))
        return replace(definition,body=GraphBody((
            Call('unpack','command.archive.unpack',{'material':InputRef('material')}),
            Call('selected','command.material.select',{'materials':OutputRef('unpack','members')},{'formats':('xls','xlsx','xlsb','xlsm','pdf','doc','docx','json','csv','dbf')}),
            MapCall('members','operation.series.extract_any',OutputRef('selected','materials'),item_input='material',output_port='dataset',parameters={'format':None}),
            Call('merge','command.observations.merge',{'datasets':OutputRef('members','items')}),
        ),{'dataset':OutputRef('merge','dataset')}))
    if identifier=='operation.material.acquire':
        from stratbox.shared.data.values import PublicationAsset
        from ..plan import TemplateInput
        original=definition.body
        identify={**original.steps[-1].inputs,'request':OutputRef('request','request'),'evidence':OutputRef('fetch','evidence')}
        if isinstance(values.get('locator'),(PublicationAsset,TemplateInput)): identify['asset']=InputRef('locator')
        if 'claim' in values: identify['claim']=InputRef('claim')
        return replace(definition,inputs={**definition.inputs,'claim':P('claim',required=False)},body=replace(original,steps=(*original.steps[:-1],replace(original.steps[-1],inputs=identify))))
    if identifier=='operation.series.acquire':
        if 'selection' in values:
            return replace(definition,body=GraphBody((
                MapCall('assets','operation.material.acquire',InputRef('selection',path='entries'),item_input='locator',output_port='material'),
            ),{'materials':OutputRef('assets','items')}))
        return replace(definition,body=GraphBody((
            Call('asset','operation.material.acquire',{'locator':InputRef('locator'),'query':InputRef('query')}),
            CollectCall('collect',(OutputRef('asset','material'),)),
        ),{'materials':OutputRef('collect','items')}))
    if identifier=='operation.source.check':
        definition=replace(definition,inputs={**definition.inputs,'index':P('index',required=False),'listing':P('listing',required=False),'location':P('location',required=False)})
        # Supplied listing and index are legal entrances, including delivered inventories.
        steps=[]
        if 'listing' in values:
            listing=InputRef('listing');evidence=InputRef('listing')
        else:
            if 'index' in values:
                index=InputRef('index')
            elif 'location' in values:
                steps.append(Call('list','command.material.list',{'location':InputRef('location'),'query':InputRef('query')}))
                index=OutputRef('list','inventory')
            else:
                steps.extend((Call('request','command.request.prepare',{'locator':InputRef('locator'),'query':InputRef('query')},{'role':'index'}),
                    Call('fetch','command.material.fetch',{'request':OutputRef('request','request')})))
                index=OutputRef('fetch','material')
            steps.append(Call('scan','command.publication.scan',{'index':index}))
            listing=OutputRef('scan','listing');evidence=index
        steps.extend((Call('select','command.issue.select',{'listing':listing,'query':InputRef('query')}),
            Call('assess','command.source.assess',{'evidence':listing,'baseline':InputRef('baseline')})))
        return replace(definition,outputs={**definition.outputs,'evidence':P('listing' if 'listing' in values else 'inventory' if 'location' in values else 'material')},body=GraphBody(tuple(steps),{'assessment':OutputRef('assess','assessment'),'evidence':evidence,'selection':OutputRef('select','selection')},required_completions=('assess',)))
    if identifier=='scenario.series.refresh':
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
    if identifier=='scenario.analysis.prepare':
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
    if identifier in {'cascade.sources.refresh','cascade.analysis.release'}:
        members=values.get('members')
        if isinstance(members,(tuple,list)) and not members:
            if not parameters.get('allow_empty',False) or identifier=='cascade.analysis.release': raise ValueError('cascade.members_required')
            return replace(definition,body=GraphBody((),{'results':(),'outcomes':()}))
        if identifier=='cascade.analysis.release' and isinstance(members,(tuple,list)) and members and all(hasattr(item,'rows') for item in members):
            members=tuple({'target':parameters.get('analysis_target',getattr(item,'source_id',None)), 'inputs':{'dataset':item,'destination':values.get('member_destination')}, 'parameters':{'product':True}} for item in members)
        if isinstance(members,(tuple,list)) and members and all(hasattr(item,'capability_id') or isinstance(item,dict) or hasattr(item,'items') and 'target' in item for item in members):
            from .requests import InvocationRequest
            steps=[];outputs=[];required=[];optional=[]
            for ordinal,item in enumerate(members):
                if isinstance(item,InvocationRequest):
                    capability=item.capability_id;args=item.inputs;params=item.parameters;chosen=item.target;is_required=True
                else:
                    capability=item.get('capability_id','scenario.series.refresh' if identifier=='cascade.sources.refresh' else 'scenario.analysis.prepare')
                    args=item.get('inputs',{});params=item.get('parameters',{});chosen=item.get('target');is_required=item.get('required',True)
                if identifier=='cascade.analysis.release':
                    params={**params,'product':True}
                    if 'destination' not in args and 'member_destination' in values: args={**args,'destination':values['member_destination']}
                if catalog.get(capability).kind!='scenario': raise ValueError('cascade.scenario_required')
                name='member'+str(ordinal)
                steps.append(Call(name,capability,args,params,target=chosen,required=is_required))
                outputs.append(OutputRef(name,'reference' if identifier=='cascade.analysis.release' else params.get('result_port','dataset')))
                if is_required: required.append(name)
                else: optional.append(ordinal)
            steps.append(CollectCall('results',tuple(outputs),optional_items=frozenset(optional),
                min_items=0 if parameters.get('allow_empty',False) and identifier=='cascade.sources.refresh' else 1))
            result={'results':OutputRef('results','items'),'outcomes':OutputRef('results','outcomes')}
            ports={'results':P('result_collection',tuple),'outcomes':P('unit_outcomes',tuple)}
            if identifier=='cascade.analysis.release':
                steps.append(Call('release','scenario.release.publish',{'members':InputRef('release_members') if 'release_members' in values else OutputRef('results','items'),'expected_token':InputRef('expected_token')}))
                result['receipt']=OutputRef('release','receipt');ports['receipt']=P('publication_receipt');result['manifest']=OutputRef('release','manifest');ports['manifest']=P('release_manifest');required.append('release')
            return replace(definition,inputs={**definition.inputs,'release_members':P('accepted_members',tuple,required=False),'member_destination':P('destination',required=False),'expected_token':P('state_token',required=False)},outputs=ports,body=GraphBody(tuple(steps),result,required_completions=tuple(required)))
    return definition
