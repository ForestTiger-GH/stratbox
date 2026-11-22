"""Offline Minfin source-cell, representation and explicitly mapped observation tests."""
from io import BytesIO

from openpyxl import Workbook
from stratbox.shared.evidence import SourcePayload
from stratbox.domains.minfin import (
    ExtractRequest, CompareRequest, RenderRequest, MapRequest, MetricBinding,
    ValidateRequest, SerializeRequest, ReadRepresentationRequest,
    extract, compare, validate, map_observations, render_csv_cells,
    serialize_extract, read_representation,
)


def _workbook(value=123, *, formula=False):
    wb = Workbook()
    sheet = wb.active
    sheet.title = 'Исполнение'
    sheet['A1'] = 'Доходы, млрд руб.'
    sheet['B1'] = 'Январь–октябрь 2026'
    sheet['A2'] = 'Доходы'
    sheet['B2'] = '=100+23' if formula else value
    sheet['B2'].number_format = '#,##0.00'
    sheet['A3'] = 'Расходы'
    sheet['B3'] = 0
    sheet['A4'] = '—'  # dash is not zero
    sheet['B4'] = None
    wb.create_sheet('Без значений')
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _extract(value=123, *, formula=False):
    payload = SourcePayload(_workbook(value, formula=formula),
                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            'minfin.fedbud.annex3.monthly')
    result = extract(ExtractRequest('minfin.fedbud', payload, 'xlsx'))
    assert result.outcome == 'succeeded', result.diagnostics
    return result.value


def test_xlsx_source_cells_preserve_kinds_geometry_and_zero():
    result = _extract()
    assert len(result.sheets) == 2
    cells = {(c.sheet, c.row, c.column): c for sh in result.sheets for c in sh.cells}
    assert cells['Исполнение', 2, 2].value == '123'
    assert cells['Исполнение', 2, 2].number_format == '#,##0.00'
    assert cells['Исполнение', 3, 2].value == '0'
    assert cells['Исполнение', 3, 2].kind == 'number'
    assert cells['Исполнение', 4, 1].value == '—'
    assert cells['Исполнение', 4, 1].kind == 'text'
    assert ('Исполнение', 4, 2) not in cells
    assert result.sheets[-1].name == 'Без значений'
    assert not result.sheets[-1].cells


def test_formula_without_cache_is_detected_and_not_fabricated():
    output = _extract(formula=True)
    formula = next(c for sh in output.sheets for c in sh.cells if c.kind == 'formula')
    assert formula.value == '=100+23'
    assert formula.cached is None
    validation = validate(ValidateRequest(output))
    assert validation.outcome == 'succeeded'
    assert validation.value.formulas_without_cache == 1
    assert validation.value.level == 'structural_only'
    result = map_observations(MapRequest(output, (MetricBinding('Исполнение',2,2,
        'fedbud.revenue','2026-10','ytd','RUB_bn'),)))
    assert result.outcome == 'failed'  # refuse to invent calculation result


def test_comparison_and_explicit_metric_binding():
    old, new = _extract(123), _extract(125)
    difference = compare(CompareRequest(old,new))
    assert difference.outcome == 'succeeded'
    assert len(difference.value.changes) == 1
    assert difference.value.changes[0].before.value == '123'
    assert difference.value.changes[0].after.value == '125'
    mapped = map_observations(MapRequest(new, (MetricBinding('Исполнение',2,2,
        'minfin.fedbud.revenue','2026-10','ytd','RUB_bn'),)))
    assert mapped.outcome == 'succeeded', mapped.diagnostics
    assert mapped.value.observations[0].value == '125'
    assert mapped.value.observations[0].value_basis == 'ytd'
    csv_data = render_csv_cells(RenderRequest(new))
    assert csv_data.outcome == 'succeeded'
    assert b'fedbud' in csv_data.value.data


def test_extract_round_trip_preserves_empty_sheets_and_sha():
    origin = _extract()
    packed = serialize_extract(SerializeRequest(origin))
    assert packed.outcome == 'succeeded', packed.diagnostics
    restored = read_representation(ReadRepresentationRequest(packed.value))
    assert restored.outcome == 'succeeded', restored.diagnostics
    assert restored.value == origin
    assert packed.value.data == serialize_extract(SerializeRequest(origin)).value.data


def test_cross_family_payload_is_rejected():
    payload = SourcePayload(_workbook(), 'application/octet-stream', 'minfin.conbud.monthly')
    r = extract(ExtractRequest('minfin.fedbud',payload,'xlsx'))
    assert r.outcome == 'failed'
    assert r.diagnostics[0].code == 'minfin.source_family_mismatch'


def test_csv_source_local_no_unjustified_economic_inference():
    data = 'Показатель;Период;Значение\nДоходы;2026-10;0\n'.encode('utf-8')
    payload = SourcePayload(data, 'text/csv', 'minfin.conbud.monthly')
    r = extract(ExtractRequest('minfin.conbud',payload,'csv'))
    assert r.outcome == 'succeeded',r.diagnostics
    assert len(r.value.sheets) == 1
    assert all(c.kind == 'text' for c in r.value.sheets[0].cells)


def test_domain_registration_available_without_loading_handlers():
    from stratbox.domains.registry import operation_catalog
    catalog = operation_catalog()
    ids = {(r.operation_id,r.contract_version) for r in catalog.list_refs()}
    assert ('minfin.discover',1) in ids
    assert ('minfin.extract',1) in ids
    assert ('minfin.read_representation',1) in ids
    assert ('minfin.readable',1) in ids
    assert catalog.owner_of('minfin.extract',1) == 'minfin'


def test_docx_source_readable_is_qualified_partial():
    from docx import Document
    from stratbox.domains.minfin import ReadableRequest, readable_document

    doc = Document()
    doc.add_paragraph('Отчет о Фонде национального благосостояния')
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = 'Показатель'
    table.cell(0, 1).text = 'Значение'
    table.cell(1, 0).text = 'Остаток'
    table.cell(1, 1).text = '10'
    buf = BytesIO()
    doc.save(buf)
    payload = SourcePayload(buf.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                            'minfin.nwf.volume')
    result = readable_document(ReadableRequest('minfin.nwf', payload, format='docx'))
    assert result.outcome == 'partial', result.diagnostics
    assert result.value.coverage == 'text_only_partial'
    assert any('Остаток' in p for p in result.value.pages)