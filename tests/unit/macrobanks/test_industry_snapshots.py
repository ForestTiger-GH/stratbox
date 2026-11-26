"""Retained source data completes the current calculation route without originals."""
from dataclasses import replace
from io import BytesIO
from types import SimpleNamespace

import pandas as pd
import pytest
from openpyxl import load_workbook
from stratbox.sdk import StrategyBox
from stratbox.capabilities.model.targets import SeriesTarget, CalculationTarget, ProductTarget
from stratbox.shared.data.values import Material
from stratbox.domains.cbr.methods.actions.serialization import encode, decode
from stratbox.domains.cbr.methods.tables.corporate_lending.observations import validate_source_dataset
from test_industry_source_uses import checked, publication
from test_cbr_industries_0104a_issuance import _book as issuance_workbook
from test_cbr_industries_0105a_debt_corp import _workbook_bytes


@pytest.mark.parametrize('family', ['debt', 'issuance'])
def test_all_stages_replay_before_final_render(family, tmp_path):
    source = 'cbr.corporate_lending.' + ('debt_0105a' if family == 'debt' else 'issuance_0104a')
    content = _workbook_bytes(report_date='01.02.2019', kemerovo_name='Кемеровская область') if family == 'debt' else issuance_workbook()
    filename = '01_05_A_Debt_corp_20190201.xlsx' if family == 'debt' else '01_04_A_New_loans_corp_20190201.xlsx'
    with StrategyBox() as first:
        dataset = checked(first.invoke('operation.series.extract_workbook', inputs={'material': Material(
            content, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', source, metadata={'name': filename})},
            parameters={'source_name': filename}, target=SeriesTarget(source)), 'dataset')
        encoded = checked(first.invoke('command.value.encode', inputs={'value': dataset}, target=SeriesTarget(source)), 'representation')
    path = tmp_path / 'source.json'
    path.write_bytes(encoded.data)
    with StrategyBox() as second:
        retained = checked(second.invoke('command.value.decode', inputs={'representation': path.read_bytes()},
            parameters={'max_materialized_bytes': encoded.identity.size}, target=SeriesTarget(source)), 'value')
        pd.testing.assert_frame_equal(retained.native.df_stream, dataset.native.df_stream)
        assert retained.native.source_sha256 == dataset.native.source_sha256
        assert retained.native.geography_reference == dataset.native.geography_reference
        assert retained.native.selection == dataset.native.selection
        derived = checked(second.invoke('command.calculate.formula', inputs={'dataset': retained},
            target=CalculationTarget('cbr.corporate_lending.' + family + '_apk')), 'dataset')
        # Neutral derived rows retain formula operands and source uses independently.
        derived_value = checked(second.invoke('command.value.encode', inputs={'value': derived}), 'representation')
        derived = checked(second.invoke('command.value.decode', inputs={'representation': derived_value}), 'value')
        assert derived.source_uses == dataset.source_uses
        view = checked(second.invoke('command.view.prepare', inputs={'dataset': derived},
            parameters={'metrics': ('apk',)}, target=ProductTarget('cbr.industries.workbook')), 'view')
        view_value = checked(second.invoke('command.value.encode', inputs={'value': view}), 'representation')
        prepared = checked(second.invoke('command.value.decode', inputs={'representation': view_value}), 'value')
        rendered = checked(second.invoke('command.product.render', inputs={'view': prepared},
            target=ProductTarget('cbr.industries.workbook')), 'product')
    workbook = load_workbook(BytesIO(rendered.data), read_only=True, data_only=True)
    assert len(workbook.sheetnames) == (6 if family == 'debt' else 3)
    workbook.close()


def test_retained_source_rejects_truncated_and_mutated_scientific_content(publication):
    _, _, _, dataset = publication
    context = SimpleNamespace(parameters={}, checkpoint=lambda: None)
    representation = encode({'value': dataset}, None, context)['representation']
    context.parameters['max_materialized_bytes'] = representation.identity.size
    with pytest.raises(ValueError):
        decode({'representation': representation.data[:-1]}, None, context)
    changed = replace(dataset.native, df_stream=dataset.native.df_stream.copy(deep=True))
    changed.df_stream.loc[0, 'value'] = 999
    with pytest.raises(ValueError, match='content_mismatch'):
        encode({'value': replace(dataset, native=changed)}, None, context)


def test_merge_preserves_independent_source_issues_and_rejects_conflicts(publication):
    _, _, _, dataset = publication
    # One duplicate observation must not silently become two source publications.
    with StrategyBox() as box:
        duplicate = box.invoke('operation.observations.merge', inputs={'datasets': (dataset, dataset)})
        assert duplicate.outcome != 'succeeded' or len(duplicate.output('dataset').rows) == len(dataset.rows)
        conflicting = replace(dataset, rows=({**dict(dataset.rows[0]), 'value': dataset.rows[0]['value'] + 1},))
        conflict = box.invoke('operation.observations.merge', inputs={'datasets': (dataset, conflicting)})
        assert conflict.outcome != 'succeeded', conflict.diagnostics
