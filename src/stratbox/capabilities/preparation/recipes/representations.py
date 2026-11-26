"""Declared physical formats and their built-in extraction promises."""
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
