"""Canonical CBR methods retain physical evidence and independently replay stages."""
from datetime import date
from decimal import Decimal
from io import BytesIO
from struct import pack

import pytest
from openpyxl import Workbook

from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.domains.cbr.capabilities import contribution, dispositions, stage_matrix
from stratbox.domains.cbr.publications.contracts import IdentifiedOriginal
from stratbox.domains.cbr.tables.reporting_forms.contracts import FormKey
from stratbox.domains.cbr.tables.reporting_forms.field_observations import FormFieldBinding
from stratbox.shared.data.observations import MetricRef, PeriodRef
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.source_publications import SourceAssetIdentity
from stratbox.sdk import StrategyBox


def catalog():
    from stratbox.capabilities.catalog import CatalogContribution
    from stratbox.capabilities.commands import definitions as commands
    from stratbox.capabilities.operations import definitions as operations
    return CatalogSnapshot.from_contributions(CatalogContribution(definitions=(*commands(), *operations())), contribution())


def workbook():
    book = Workbook()
    sheet = book.active
    sheet.title = 'Денежные агрегаты'
    sheet.append(['Денежные агрегаты, млрд руб.', date(2026, 1, 1), date(2026, 2, 1)])
    sheet.append(['M2', 123, 456])
    sheet.append(['Notes', 'source footnote', '—'])
    stream = BytesIO(); book.save(stream)
    source = 'cbr.monetary_statistics.monetary_agg'
    return IdentifiedOriginal(SourceAssetIdentity(source, 'capture-1', 'main'),
        SourcePayload(stream.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', source), 'xlsx')


def dbf():
    columns = (('REGN', 'C', 8, 0), ('ROW', 'C', 8, 0), ('VALUE', 'N', 18, 4))
    rows = ((b' ', (b'0012', b'011', b'000001.2300')), (b'*', (b'0012', b'012', b'99')),
            (b' ', (b'0012', b'013', b'0')), (b' ', (b'0012', b'014', b'')))
    header = pack('<BBBBIHH20x', 3, 126, 4, 1, len(rows), 33 + 32 * len(columns), 1 + sum(c[2] for c in columns))
    fields = b''.join(pack('<11sc4xBB14x', n.encode(), k.encode(), size, decimals) for n, k, size, decimals in columns)
    records = b''.join(flag + b''.join(value.ljust(column[2]) for value, column in zip(values, columns)) for flag, values in rows)
    return SourcePayload(header + fields + b'\r' + records + b'\x1a', 'application/x-dbf')


def checked(result):
    assert result.outcome == 'succeeded', result.diagnostics
    return result


def test_complete_source_and_method_inventory_has_canonical_routes():
    snapshot = catalog()
    assert len(snapshot.groups) == 57
    assert len(snapshot.profiles) >= 99
    assert len(dispositions()) == 156
    assert {item['source_id'] for item in stage_matrix()} == {
        group.source_ids[0] for group in snapshot.groups}
    assert all(snapshot.definition(item['capability_id']).kind == item['kind'] for item in dispositions())
    assert snapshot.definition('cbr.forms.parse').kind == 'scenario'
    assert snapshot.definition('cbr.sors.restore_from_originals').kind == 'scenario'


def test_original_extract_and_snapshot_replay_use_one_canonical_session(monkeypatch):
    with StrategyBox(capabilities=catalog()) as box:
        extracted = checked(box.invoke('cbr.tables.extract', inputs={'original': workbook()}, timeout=15))
        source = extracted.output('flake')
        assert source.sheets[0].cell(2, 2).value == 123
        saved = checked(box.invoke('cbr.tables.flake_snapshot', inputs={'flake': source}, timeout=15)).output('snapshot')
        def forbidden(*args, **kwargs):
            raise AssertionError('A retained source stage must not decode an original again')
        monkeypatch.setattr('stratbox.domains.cbr.tables.statistics.extraction.read_workbook_cells', forbidden)
        replayed = checked(box.invoke('cbr.tables.read_flake_snapshot', inputs={'snapshot': saved}, timeout=15)).output('flake')
        assert replayed == source
        assert replayed.sheets[0].cell(3, 2).value == 'source footnote'
        assessed = checked(box.invoke('cbr.tables.validate', inputs={'flake': replayed}, timeout=15)).output('validation')
        assert assessed.source_identity == source.source_identity


@pytest.mark.parametrize('code', ('134', '803'))
def test_all_member_form_fields_have_explicit_semantics_and_replay(code):
    bindings = (FormFieldBinding('source.dbf', 'VALUE', 'REGN',
        MetricRef('reviewed.metric', 'RUB', 'stock', 'fixture.v1', Decimal(1000)),
        PeriodRef('as_of', as_of=date(2026, 4, 1)), ('ROW',), edition='fixture.v1'),)
    with StrategyBox(capabilities=catalog()) as box:
        result = checked(box.invoke('cbr.forms.extract', inputs={'source': dbf()},
            parameters={'key': FormKey(code, date(2026, 4, 1))}, timeout=15))
        physical = result.output('flakes')
        interpreted = checked(box.invoke('cbr.forms.extract_fields', inputs={'flakes': physical},
            parameters={'bindings': bindings}, timeout=15)).output('observations')
        assert [item.value for item in interpreted.observations] == [Decimal('1.2300'), Decimal(0), None]
        assert [item.value_status for item in interpreted.observations] == ['reported', 'reported', 'blank']
        assert interpreted.observations[0].subject.id == '0012'
        assert interpreted.observations[0].raw_token == '000001.2300'
        assert interpreted.source_uses[0].coordinate.material_identity == physical.original_identity
        assert interpreted.source_uses[0].coordinate.semantic_profile_edition
        assert len(physical.members[0].table.records) == 4
        assert physical.members[0].table.records[1].deleted
        invalid = box.invoke('cbr.forms.extract_fields', inputs={'flakes': physical},
            parameters={'bindings': ()}, timeout=15)
        assert invalid.outcome == 'failed'
        assert any('field_bindings_required' in str(item) for item in invalid.diagnostics)


def test_financial_model_scenario_accepts_retained_snapshots_without_originals():
    import pandas as pd
    from stratbox.domains.cbr.tables.reporting_forms.contracts import FormSnapshot
    snapshot = FormSnapshot(FormKey('802', date(2026, 4, 1)),
        {'REGN': 'REGN_GKO', 'CODE': 'STR', 'total': 'VSEGO'},
        pd.DataFrame((('1000', '14', '1.2300'),), columns=('REGN', 'CODE', 'total'), dtype=object), ())
    with StrategyBox(capabilities=catalog()) as box:
        result = checked(box.invoke('cbr.forms.build_data', inputs={'snapshots': (snapshot,)}, timeout=30))
        output = result.output('data')
        assert output.form == '802'
        assert output.long.loc[output.long['Код'].eq('14'), 'Значение'].iloc[0] == Decimal('1.2300')
        assert any('/align' in key for key in result.scopes)
        assert any('/prepare' in key for key in result.scopes)
        assert any('/calculate' in key for key in result.scopes)


def test_bounded_escrow_history_exposes_independent_source_interpretations():
    from stratbox.domains.cbr.operations.project_finance.contracts import ParseEscrowRequest
    from stratbox.domains.cbr.tables.project_finance.profiles import required_indicators
    from stratbox.core.execution.session import ExecutionSettings
    def original(period, amount):
        book = Workbook(); sheet = book.active; sheet.title = 'Regions'
        specs = required_indicators()
        values = [7.25 if spec.value_kind == 'percent' else amount for spec in specs]
        sheet.append(['No.', 'Субъект Российской Федерации (федеральный округ)',
            *(spec.canonical_name for spec in specs)])
        sheet.append(['Центральный ФО', None, *values])
        sheet.append([1, 'Example region', *values])
        sheet.append(['Итого', None, *values])
        stream = BytesIO(); book.save(stream)
        return ParseEscrowRequest(SourcePayload(stream.getvalue()), f'escrow_{period}.xlsx')
    inputs = (original('01062026', '12.25'), original('01072026', '13.25'))
    with StrategyBox(capabilities=catalog(), settings=ExecutionSettings(max_workers=1, map_window=1)) as box:
        result = checked(box.invoke('cbr.escrow.build_history', inputs={'sources': inputs}, timeout=30))
        dataset = result.output('dataset')
        assert len(dataset.releases) == 2
        assert {release.original_identity for release in dataset.releases} == {item.payload.identity for item in inputs}
        assert any('/extract[' in key or '/extract/' in key for key in result.scopes)


def test_product_keeps_accepted_extract_and_dataset_when_rendering_fails():
    identifier = 'scenario.cbr.monetary_statistics.monetary_agg.product'
    with StrategyBox(capabilities=catalog()) as box:
        result = box.invoke(identifier, inputs={'original': workbook()},
            parameters={'render_format': 'unsupported'}, timeout=30)
        assert result.outcome == 'failed'
        assert result.output('extract').sheets
        assert result.output('dataset').batches
        assert result.output('view').snapshot.complete
        with pytest.raises((ValueError, KeyError)):
            result.output('representation')


def test_source_validation_rejects_retained_values_that_disagree_with_dbf_bytes():
    from dataclasses import replace
    with StrategyBox(capabilities=catalog()) as box:
        physical = checked(box.invoke('cbr.forms.extract', inputs={'source': dbf()},
            parameters={'key': FormKey('134', date(2014, 4, 1))}, timeout=15)).output('flakes')
        assert checked(box.invoke('cbr.forms.validate', inputs={'flakes': physical}, timeout=15)).output('flakes') == physical
        member = physical.members[0]
        records = (replace(member.table.records[0], values=('0012', '011', '9999')), *member.table.records[1:])
        forged = replace(physical, members=(replace(member, table=replace(member.table, records=records)),))
        result = box.invoke('cbr.forms.validate', inputs={'flakes': forged}, timeout=15)
        assert result.outcome == 'failed'
        assert 'decoded_evidence_mismatch' in str(result.diagnostics)


@pytest.mark.parametrize('code,columns,values,member,period', (
    ('134', (('REGN', 'N', 4), ('C1', 'C', 15), ('C3', 'N', 16)),
        ('0012', 'U104.2.2.1', '123'), '042014_134D.DBF', PeriodRef('as_of', date(2014, 4, 1))),
    ('803', (('REGN_GKO', 'N', 4), ('RAZDEL', 'C', 3), ('STR', 'C', 5),
             ('KORR_P', 'N', 16), ('KORR_M', 'N', 16), ('VSEGO', 'N', 16)),
        ('0012', '001', '00014', '1', '2', '123'), 'PK8032404.dbf',
        PeriodRef('interval', start=date(2024, 1, 1), end=date(2024, 3, 31))),
))
def test_published_134_803_field_profiles_bind_exact_geometry_and_explicit_basis(code, columns, values, member, period):
    as_of = period.as_of if period.kind == 'as_of' else date(2024, 4, 1)
    header = pack('<BBBBIHH20x', 3, 124, 4, 1, 1, 33 + 32 * len(columns), 1 + sum(c[2] for c in columns))
    descriptors = b''.join(pack('<11sc4xBB14x', n.encode(), k.encode(), size, 0) for n, k, size in columns)
    data = header + descriptors + b'\r ' + b''.join(value.encode().ljust(column[2]) for value, column in zip(values, columns)) + b'\x1a'
    with StrategyBox(capabilities=catalog()) as box:
        physical = checked(box.invoke('cbr.forms.extract', inputs={'source': SourcePayload(data)},
            parameters={'key': FormKey(code, as_of), 'member_name': member}, timeout=15)).output('flakes')
        profile = 'cbr.forms.' + code + '.fields.' + ('20120801' if code == '134' else '20230701')
        bindings = checked(box.invoke('cbr.forms.published_field_bindings', inputs={'flakes': physical},
            parameters={'profile_id': profile, 'unit': 'RUB', 'scale': Decimal(1000), 'period': period}, timeout=15)).output('bindings')
        interpreted = checked(box.invoke('cbr.forms.extract_fields', inputs={'flakes': physical},
            parameters={'bindings': bindings}, timeout=15)).output('observations')
        assert len(interpreted.observations) == (1 if code == '134' else 3)
        assert all(item.period == period and item.metric.scale == Decimal(1000) for item in interpreted.observations)
        assert all(item.subject.id == '0012' for item in interpreted.observations)
        assert interpreted.source_uses[0].coordinate.material_identity == physical.original_identity


def test_statistical_extraction_and_source_readable_share_one_physical_decoder(monkeypatch):
    from stratbox.capabilities.model import ScenarioDefinition, GraphBody, Call, InputRef, OutputRef
    from stratbox.capabilities.catalog import CatalogContribution
    import stratbox.core.capabilities.workbooks as physical
    snapshot = catalog()
    extraction = snapshot.definition('cbr.tables.extract')
    readable = snapshot.definition('cbr.tables.readable_original')
    scenario = ScenarioDefinition('fixture.cbr.shared_workbook', GraphBody((
        Call('extract', extraction.capability_id, {'original': InputRef('original')}),
        Call('readable', readable.capability_id, {'original': InputRef('original')}),
    ), {'flake': OutputRef('extract', 'flake'), 'readable': OutputRef('readable', 'readable')}),
        inputs=extraction.inputs, outputs={'flake': extraction.outputs['flake'], 'readable': readable.outputs['readable']})
    snapshot = snapshot.overlay(CatalogContribution(definitions=(scenario,)))
    decoder, calls = physical.read_workbook_cells, []
    def count(*args, **options):
        calls.append(1)
        return decoder(*args, **options)
    monkeypatch.setattr(physical, 'read_workbook_cells', count)
    def forbidden(*args, **options):
        raise AssertionError('CBR source attribution must consume decoded cells rather than decode again')
    monkeypatch.setattr('stratbox.domains.cbr.tables.statistics.extraction.read_workbook_cells', forbidden)
    original = workbook()
    with StrategyBox(capabilities=snapshot) as box:
        result = checked(box.invoke(scenario.capability_id, inputs={'original': original}, timeout=30))
        assert result.output('flake').source_identity == original.payload.identity
        assert b'source footnote' in result.output('readable').data
        assert calls == [1]
