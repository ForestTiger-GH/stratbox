"""Explicit synthetic layout fixture, not publisher-layout certification."""
from io import BytesIO
import pytest
from stratbox.domains.rosstat.common.kep2 import KEP2_INDICATORS

def synthetic_kep2_bytes():
    openpyxl = pytest.importorskip('openpyxl')
    book = openpyxl.Workbook()
    contents = book.active
    contents.title = 'Содержание'
    names = {'investment': '1.6 ', 'wages': '4.2 ', 'construction': '1.7 ', 'freight_turnover': '1.5 ', 'retail': '1.12 ', 'retail_food': '1.12 ', 'retail_nonfood': '1.12 ', 'catering': '1.12 ', 'wholesale': '1.15', 'paid_services': '1.13 ', 'agriculture': '1.3'}
    months = ('Янв.', 'Фев.', 'Март', 'Апр.', 'Май', 'Июнь', 'Июль', 'Август', 'Сент.', 'Окт.', 'Нояб.', 'Дек.')
    sheets = {}
    for name in dict.fromkeys(names.values()):
        sheet = book.create_sheet(name)
        sheets[name] = sheet
        sheet.cell(1, 2, 'Год')
        sheet.cell(2, 2, 'Year')
        sheet.cell(1, 3, 'Кварталы / Quarters')
        for col, quarter in enumerate(('I', 'II', 'III', 'IV'), 3):
            sheet.cell(2, col, quarter)
        for col, month in enumerate(months, 7):
            sheet.cell(1, col, month)
    next_row = {name: 3 for name in sheets}
    toc = 0
    for indicator in KEP2_INDICATORS:
        name = names[indicator.id]
        if indicator.parent is None:
            col = 1 if toc < 4 else 5
            row = 3 + toc % 4
            contents.cell(row, col, name.strip() + '.')
            contents.cell(row, col + 1, indicator.titles[0])
            toc += 1
        sheet = sheets[name]
        start = next_row[name]
        title = indicator.titles[0]
        if indicator.id == 'wages':
            title = indicator.titles[1]
        unit = 'млрд тонно-км' if indicator.id == 'freight_turnover' else 'рублей1)' if indicator.id == 'wages' else 'млрд рублей'
        sheet.cell(start, 1, title + ('1), ' if indicator.id == 'investment' else ', ') + unit)
        cursor = start + 1
        if indicator.absolute:
            sheet.cell(cursor, 1, '/ English source title')
            sheet.cell(cursor + 1, 1, 2024)
            sheet.cell(cursor + 1, 2, 1000)
            sheet.cell(cursor + 1, 3, 200)
            sheet.cell(cursor + 1, 7, 100.1)
            sheet.cell(cursor + 2, 7, '110,2 1)')
            sheet.cell(cursor + 2, 8, '—')
            sheet.cell(cursor + 2, 9, '…2)')
            sheet.cell(cursor + 3, 1, 2025)
            sheet.cell(cursor + 3, 7, 0)
            cursor += 4
        for measure, marker in (('yoy', 'в % к соответствующему периоду предыдущего года'), ('previous', 'в % к предыдущему периоду')):
            if indicator.id == 'agriculture' and measure == 'previous':
                continue
            sheet.cell(cursor, 1, marker)
            sheet.cell(cursor + 1, 1, '/ English index marker')
            sheet.cell(cursor + 2, 1, 2024)
            sheet.cell(cursor + 2, 2, 105)
            sheet.cell(cursor + 2, 3, 103)
            sheet.cell(cursor + 2, 7, 105.1 if measure == 'yoy' else 102.5)
            sheet.cell(cursor + 3, 1, 2025)
            sheet.cell(cursor + 3, 7, 101)
            cursor += 4
        sheet.cell(cursor, 1, '1) Preliminary estimate.')
        next_row[name] = cursor + 2
    freight = sheets[names['freight_turnover']]
    r = next_row[names['freight_turnover']]
    freight.cell(r, 1, 'Перевозка грузов транспортом, млн тонн')
    freight.cell(r + 1, 1, 2024)
    freight.cell(r + 1, 7, 999)
    freight.cell(r + 2, 1, 'в % к соответствующему периоду предыдущего года')
    freight.cell(r + 3, 1, 2024)
    freight.cell(r + 3, 7, 777)
    stream = BytesIO()
    book.save(stream)
    return stream.getvalue()
