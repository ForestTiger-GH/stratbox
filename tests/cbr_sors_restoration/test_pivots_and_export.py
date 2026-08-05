from pathlib import Path

import openpyxl

from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsPivotRequest,
    SorsWorkbookRequest,
)
from stratbox.macrobanks.cbr_sors_restoration.export import export_sors_workbook
from stratbox.macrobanks.cbr_sors_restoration.pivots import build_sors_pivot


def test_region_pivot_has_classes_as_rows(small_result) -> None:
    pivot = build_sors_pivot(small_result, SorsPivotRequest(region_name='Регион 1'))
    assert pivot.orientation == 'REGION_TO_CLASSES'
    assert tuple(pivot.table['class_code']) == ('01', '16')


def test_class_pivot_has_regions_as_rows(small_result) -> None:
    pivot = build_sors_pivot(small_result, SorsPivotRequest(class_code='16'))
    assert pivot.orientation == 'CLASS_TO_REGIONS'
    assert tuple(pivot.table['region_code']) == ('r1', 'r2')


def test_workbook_export_uses_pivot_contract(tmp_path: Path, small_result) -> None:
    output = tmp_path / 'sors.xlsx'
    exported = export_sors_workbook(
        small_result,
        SorsWorkbookRequest(
            output,
            pivots=(SorsPivotRequest(region_name='Регион 1'),),
        ),
    )
    assert exported.output_path == output
    assert exported.sha256
    workbook = openpyxl.load_workbook(output, read_only=True)
    assert 'Regional_OKVED2' in workbook.sheetnames
    assert any(name.startswith('Pivot_1_') for name in workbook.sheetnames)
