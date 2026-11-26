"""Source coordinates survive the standard calculation and product route."""
from io import BytesIO

import pytest
from stratbox.sdk import StrategyBox
from stratbox.capabilities.model.targets import SeriesTarget, CalculationTarget, ProductTarget
from stratbox.shared.data.values import Material
from stratbox.shared.data.source_context import ValueContext
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.sources import industry_source_uses
from test_cbr_industries_0104a_issuance import _book as issuance_book
from test_cbr_industries_0105a_debt_corp import _workbook_bytes


def checked(result, port):
    assert result.outcome == 'succeeded', result.diagnostics
    return result.output(port)


@pytest.fixture(scope='module', params=['debt', 'issuance'])
def publication(request):
    family = request.param
    if family == 'debt':
        source = 'cbr.corporate_lending.debt_0105a'
        content = _workbook_bytes(report_date='01.02.2019', kemerovo_name='Кемеровская область')
        filename = '01_05_A_Debt_corp_20190201.xlsx'
    else:
        source = 'cbr.corporate_lending.issuance_0104a'
        content = issuance_book()
        filename = '01_04_A_New_loans_corp_20190201.xlsx'
    material = Material(content, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        source, metadata={'name': filename})
    with StrategyBox() as box:
        dataset = checked(box.invoke('operation.series.extract_workbook', inputs={'material': material},
            parameters={'source_name': filename}, target=SeriesTarget(source)), 'dataset')
    return family, source, material, dataset


def test_source_bound_apk_products_and_replays_keep_actual_publication(publication):
    family, source_id, original, dataset = publication
    parsed = dataset.native
    uses = dataset.source_uses
    assert len(uses) == 1
    coordinate = uses[0].coordinate
    assert coordinate.source_id == source_id
    assert coordinate.issue_id == parsed.report_date
    assert coordinate.asset_id == 'main'
    assert coordinate.material_identity == original.identity
    assert ValueContext(uses).source_ids == (source_id,)
    with StrategyBox() as box:
        encoded = checked(box.invoke('command.value.encode', inputs={'value': dataset},
            target=SeriesTarget(source_id)), 'representation')
        replayed = checked(box.invoke('command.value.decode', inputs={'representation': encoded},
            target=SeriesTarget(source_id)), 'value')
        assert replayed.source_uses == uses
        calculated = checked(box.invoke('command.calculate.formula', inputs={'dataset': replayed},
            target=CalculationTarget('cbr.corporate_lending.' + family + '_apk')), 'dataset')
        assert calculated.source_uses == uses
        product = ProductTarget('cbr.industries.workbook')
        view = checked(box.invoke('command.view.prepare', inputs={'dataset': calculated}, target=product), 'view')
        assert view.source_uses == uses
        retained = checked(box.invoke('command.value.encode', inputs={'value': view}, target=product), 'representation')
        restored = checked(box.invoke('command.value.decode', inputs={'representation': retained}, target=product), 'value')
        assert restored.source_uses == uses
        assert checked(box.invoke('command.product.render', inputs={'view': restored}, target=product), 'product').data.startswith(b'PK')


def test_only_admitted_schema_coordinates_establish_industry_source(publication):
    _, source_id, _, dataset = publication
    frame = dataset.native.df_stream.copy()
    frame['source_name'] = 'An unrelated filename cannot change the publisher source'
    assert industry_source_uses(frame)[0].coordinate.source_id == source_id
    frame['series_code'] = 'unreviewed.schema'
    frame['source_name'] = '01_05_A_Debt_corp_20190201.xlsx'
    assert industry_source_uses(frame) == ()
