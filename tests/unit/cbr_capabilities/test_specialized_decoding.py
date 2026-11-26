"""Source parsers and physical readable projections share one admitted decode."""
from pathlib import Path
import runpy

import pandas as pd
import pytest

from stratbox.capabilities.catalog import CatalogContribution
from stratbox.capabilities.model import ScenarioDefinition, GraphBody, Call, InputRef, OutputRef
from stratbox.sdk import StrategyBox

from test_catalog_and_replay import catalog, checked

_ROOT = Path(__file__).resolve().parents[3]


def fixture(family):
    if family == '0105a':
        data = runpy.run_path(str(_ROOT / 'tests/unit/macrobanks/test_cbr_industries_0105a_debt_corp.py'))
        raw = data['_workbook_bytes'](report_date='01.02.2019', kemerovo_name='Кемеровская область')
        from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import ParseIndustryRequest
        from stratbox.domains.cbr.operations.corporate_lending.debt.operations import parse
        from stratbox.shared.evidence import SourcePayload
        return ParseIndustryRequest(SourcePayload(raw), '01_05_A_Debt_corp_20190201.xlsx'), parse
    if family == '0104a':
        data = runpy.run_path(str(_ROOT / 'tests/unit/macrobanks/test_cbr_industries_0104a_issuance.py'))
        from stratbox.domains.cbr.operations.corporate_lending.issuance.operations import parse
        return data['_request'](), parse
    data = runpy.run_path(str(_ROOT / 'tests/unit/cbr_escrow/test_replay.py'))
    from stratbox.domains.cbr.operations.project_finance.handlers import parse
    return data['publication'](), parse


@pytest.mark.parametrize('family', ('0105a', '0104a', 'escrow'))
def test_specialized_interpretation_and_readable_share_decode_with_equal_source_results(family, monkeypatch):
    import stratbox.core.capabilities.workbooks as physical
    request, standalone = fixture(family)
    expected = standalone(request)
    assert expected.outcome == 'succeeded', expected.diagnostics
    prefix = 'cbr.escrow' if family == 'escrow' else 'cbr.industries.' + family
    snapshot = catalog()
    parser = snapshot.definition(prefix + '.parse')
    readable = snapshot.definition(prefix + '.readable_original')
    scenario = ScenarioDefinition('fixture.cbr.shared_' + family, GraphBody((
        Call('interpret', parser.capability_id, {'source': InputRef('source')}, {'source_name': request.source_name}),
        Call('readable', readable.capability_id, {'source': InputRef('source')}),
    ), {'file': OutputRef('interpret', 'file'), 'readable': OutputRef('readable', 'readable')}),
        inputs=parser.inputs, outputs={'file': parser.outputs['file'], 'readable': readable.outputs['readable']})
    snapshot = snapshot.overlay(CatalogContribution(definitions=(scenario,)))
    decoder, calls = physical.read_workbook_cells, []
    def count(*args, **options):
        calls.append(1)
        return decoder(*args, **options)
    monkeypatch.setattr(physical, 'read_workbook_cells', count)
    def forbidden(*args, **options):
        raise AssertionError('A CBR interpreter must consume the shared physical cells')
    if family == 'escrow':
        monkeypatch.setattr('stratbox.domains.cbr.methods.tables.project_finance.parser.load_workbook', forbidden)
    else:
        module = 'debt' if family == '0105a' else 'issuance'
        monkeypatch.setattr('stratbox.domains.cbr.methods.tables.corporate_lending.' + module + '.parser.open_ooxml_workbook', forbidden)
    with StrategyBox(capabilities=snapshot) as box:
        result = checked(box.invoke(scenario.capability_id, inputs={'source': request.payload}, timeout=40))
        actual = result.output('file')
        if family == 'escrow':
            pd.testing.assert_frame_equal(actual.df_cells, expected.value.df_cells)
            pd.testing.assert_frame_equal(actual.df_long, expected.value.df_long)
            assert b'"formula":"1+1"' in result.output('readable').data
        else:
            pd.testing.assert_frame_equal(actual.df_stream, expected.value.df_stream)
            assert actual.validation_issues == expected.value.validation_issues
        assert calls == [1]


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
