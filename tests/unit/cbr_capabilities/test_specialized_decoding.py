"""CBR interpretation and retained evidence consume one explicit physical decode."""
from pathlib import Path
import runpy

import pandas as pd
import pytest

from stratbox.capabilities.model.targets import SeriesTarget
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material

_ROOT = Path(__file__).resolve().parents[3]


def fixture(family):
    if family == "0105a":
        data = runpy.run_path(str(_ROOT / "tests/unit/macrobanks/test_cbr_industries_0105a_debt_corp.py"))
        return "cbr.corporate_lending.debt_0105a", data["_workbook_bytes"](report_date="01.02.2019", kemerovo_name="Кемеровская область"), "01_05_A_Debt_corp_20190201.xlsx"
    if family == "0104a":
        data = runpy.run_path(str(_ROOT / "tests/unit/macrobanks/test_cbr_industries_0104a_issuance.py"))
        return "cbr.corporate_lending.issuance_0104a", data["_book"](), "01_04_A_New_loans_corp_20190201.xlsx"
    data = runpy.run_path(str(_ROOT / "tests/unit/cbr_escrow/test_replay.py"))
    request = data["publication"]()
    return "cbr.project_finance.escrow", request.payload.data, request.source_name


def checked(result, port):
    assert result.outcome == "succeeded", result.diagnostics
    return result.output(port)


@pytest.mark.parametrize("family", ("0105a", "0104a", "escrow"))
def test_specialized_interpretation_and_retention_share_one_decoder(family, monkeypatch):
    from stratbox.core.formats.spreadsheets import cells
    source, data, filename = fixture(family)
    calls, decoder = [], cells.read_workbook_cells
    def count(*args, **kwargs):
        calls.append(1)
        return decoder(*args, **kwargs)
    monkeypatch.setattr(cells, "read_workbook_cells", count)
    def forbidden(*args, **kwargs):
        raise AssertionError("An interpreter must consume retained physical cells")
    if family == "escrow":
        monkeypatch.setattr("stratbox.domains.cbr.methods.tables.project_finance.parser.load_workbook", forbidden)
    else:
        owner = "debt" if family == "0105a" else "issuance"
        monkeypatch.setattr("stratbox.domains.cbr.methods.tables.corporate_lending." + owner + ".parser.open_ooxml_workbook", forbidden)
    target = SeriesTarget(source)
    with StrategyBox() as box:
        physical = checked(box.invoke("command.workbook.decode", inputs={"material": Material(data, source_id=source)}), "physical")
        saved = checked(box.invoke("command.value.encode", inputs={"value": physical}, target=target), "representation")
        restored = checked(box.invoke("command.value.decode", inputs={"representation": saved}, target=target), "value")
        dataset = checked(box.invoke("operation.series.extract_workbook", inputs={"physical": restored, "issue": "2019-02-01" if family != "escrow" else "2026-06-01"}, parameters={"source_name": filename}, target=target), "dataset")
        assert dataset.rows and dataset.source_uses[0].coordinate.material_identity == physical.material.identity
        assert physical.workbook == restored.workbook
        if family != "escrow":
            assert dataset.native.validation_issues == ()
            assert len(dataset.native.df_stream) == 96 * 26 * (6 if family == "0105a" else 3)
        assert calls == [1]


def test_other_known_source_is_rejected_before_physical_decode(monkeypatch):
    from stratbox.core.formats.spreadsheets import cells
    source, data, filename = fixture("escrow")
    def forbidden(*args, **kwargs):
        raise AssertionError("Wrong logical source must fail before decoding")
    monkeypatch.setattr(cells, "read_workbook_cells", forbidden)
    with StrategyBox() as box:
        with pytest.raises(ValueError, match="source"):
            box.prepare("operation.series.extract_workbook", inputs={"material": Material(data, source_id="cbr.funding.funds_all")}, target=SeriesTarget(source))


def test_interpretation_uses_occupied_extent_and_bounds_sparse_distant_content():
    from stratbox.shared.data.workbook_cells import WorkbookCells, WorkbookCell, SheetCells
    from stratbox.shared.identity import ByteIdentity
    from stratbox.domains.cbr.methods.tables.decoded_workbooks import decoded_sheets
    original = b'exact original bytes'
    active = WorkbookCell(1, 1, 'A1', 'source header', None, 'inlineStr')
    cells = WorkbookCells((SheetCells('Source', 0, 1_048_576, 16_384, (active,)),), ByteIdentity.of(original))
    assert tuple(decoded_sheets(cells, original)[0][1]) == (('source header',),)
    distant = WorkbookCell(1000, 6000, 'HVT1000', 1, '1', 'n')
    # Column HVT is 6000; a declared sparse source must not allocate six million slots.
    large = WorkbookCells((SheetCells('Source', 0, 1000, 6000, (active, distant)),), ByteIdentity.of(original))
    with pytest.raises(ValueError, match='interpretation_extent_limit'):
        tuple(decoded_sheets(large, original)[0][1])


def test_source_gate_rejects_negative_issuance_outside_the_selected_industry():
    from io import BytesIO
    from openpyxl import load_workbook
    source, data, filename=fixture("0104a")
    book=load_workbook(BytesIO(data))
    book["rubles"]["C4"]=-1
    output=BytesIO();book.save(output);book.close()
    with StrategyBox() as box:
        result=box.invoke("operation.series.extract_workbook",inputs={"material":Material(output.getvalue(),source_id=source),"issue":"2019-02-01"},parameters={"source_name":filename},target=SeriesTarget(source))
        assert result.outcome=="failed"
        assert any("industry_source_validation_failed" in str(item) for item in result.diagnostics)
