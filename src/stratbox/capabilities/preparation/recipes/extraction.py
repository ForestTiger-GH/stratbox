"""Pure authoring-time graph recipes for extraction purposes."""

from dataclasses import replace

from ...model import Call, DispatchCall, GraphBody, InputRef, MapCall, OutputRef

from ...operations.standard import extraction

from .representations import declared_format, _FORMATS

def structured(definition, values, parameters, record, catalog=None):
    identifier = definition.id
    fmt = declared_format(values, parameters, record)
    if fmt not in {'json','csv','dbf'}: raise ValueError('recipe.structured_format_required')
    return replace(extraction(identifier,'command.'+fmt+'.decode'),id=identifier)

def document(definition, values, parameters, record, catalog=None):
    identifier = definition.id
    fmt = declared_format(values, parameters, record)
    if fmt != "doc":
        return definition
    base=extraction(identifier,'command.document.decode')
    steps=(Call('convert','command.document.convert',{'material':InputRef('material')}),
           Call('decode','command.document.decode',{'material':OutputRef('convert','material')}),*base.body.steps[1:])
    return replace(base,body=replace(base.body,steps=steps))

def any_representation(definition, values, parameters, record, catalog=None):
    fmt = declared_format(values, parameters, record)
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

def archive(definition, values, parameters, record, catalog=None):
    publication=getattr(record,'publication',record)
    settings=getattr(publication,'settings',None)
    archive_mode=getattr(publication,'archive_mode',None) or (settings.get('archive_mode') if hasattr(settings,'get') else getattr(settings,'archive_mode',None))
    if archive_mode in {'workbook_collection','dbf_collection'}:
        formats=('dbf',) if archive_mode=='dbf_collection' else ('xls','xlsx','xlsb','xlsm')
        decoder='command.dbf.decode' if archive_mode=='dbf_collection' else 'command.workbook.decode'
        return replace(definition,body=GraphBody((
            Call('unpack','command.archive.unpack',{'material':InputRef('material')}),
            Call('members','command.material.select',{'materials':OutputRef('unpack','members')},{'formats':formats}),
            MapCall('decode',decoder,OutputRef('members','materials'),item_input='material',output_port='physical'),
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
