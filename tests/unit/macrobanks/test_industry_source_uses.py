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
            parameters={'max_materialized_bytes': encoded.identity.size}, target=SeriesTarget(source_id)), 'value')
        assert replayed.source_uses == uses
        calculated = checked(box.invoke('command.calculate.formula', inputs={'dataset': replayed},
            target=CalculationTarget('cbr.corporate_lending.' + family + '_apk')), 'dataset')
        assert calculated.source_uses == uses
        product = ProductTarget('cbr.industries.workbook')
        view = checked(box.invoke('command.view.prepare', inputs={'dataset': calculated},
            parameters={'metrics': ('apk',)}, target=product), 'view')
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


@pytest.mark.parametrize("carrier_kind", ("retained", "staged"))
def test_decoded_industry_entrance_needs_identity_without_original_byte_buffer(publication, carrier_kind):
    from dataclasses import replace
    from types import SimpleNamespace
    from stratbox.core.commands.decoding import workbook_decode
    from stratbox.domains.cbr.common.contracts import FamilySettings
    from stratbox.domains.cbr.methods.actions import industries
    from stratbox.shared.data.materials import StagedMaterialRef
    from stratbox.shared.data.values import ImmutableMaterialRef
    from stratbox.shared.identity import ByteIdentity
    family, source_id, original, baseline = publication
    context = SimpleNamespace(parameters={}, checkpoint=lambda: None)
    physical = workbook_decode({"material": original}, None, context)["physical"]
    metadata = {"filename": original.metadata["name"], "source_id": source_id, "issue_id": "2019-02-01"}
    if carrier_kind == "retained":
        reference = ImmutableMaterialRef("retained/source", original.identity, metadata=metadata)
    else:
        reference = StagedMaterialRef("stage", "fixture", "session", original.identity,
            source_id=source_id, metadata=metadata)
    assert not hasattr(reference, "data")
    settings = FamilySettings(source_id, "industry_" + family)
    tables = industries.extract({"physical": replace(physical, material=reference)}, settings, context)["tables"]
    interpreted = industries.interpret({"tables": tables}, settings, context)["dataset"]
    assert interpreted.rows == baseline.rows
    assert interpreted.source_uses == baseline.source_uses
    assert interpreted.native.source_sha256 == original.identity.sha256
    bad_workbook = replace(physical.workbook, identity=ByteIdentity.of(b"other publication"))
    with pytest.raises(ValueError, match="original_identity_mismatch"):
        industries.extract({"physical": replace(physical, material=reference, workbook=bad_workbook)}, settings, context)
