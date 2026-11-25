"""Effect evidence follows real result ownership and explicit source policy."""
from stratbox.core.execution.effects import EffectAuthority, ExactCurrentRevisionPolicy
from stratbox.core.execution.session import ExecutionSettings
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.storage.staging import storage_scope
from stratbox.sdk import StrategyBox
from stratbox.shared.data.representation import Representation


def test_long_lived_session_releases_closed_effect_results_beyond_authority_capacity(tmp_path):
    store = LocalFileStore(str(tmp_path))
    with StrategyBox(providers={'output_filestore': store}, settings=ExecutionSettings(max_workers=1)) as box:
        box.session.effects = EffectAuthority(max_records=2, history_limit=1, attempt_limit=2)
        for i in range(24):
            material = Representation('fixture.csv', 1, 'text/csv', ('value\n' + str(i)).encode())
            result = box.invoke('save.product', inputs={'material': material},
                parameters={'destination': 'product.' + str(i) + '.csv'}, timeout=5)
            assert result.outcome == 'succeeded', result.diagnostics
            assert result.effects[0].state == 'confirmed'
            result.close()
            snapshot = box.session.effects.retention_snapshot()
            assert snapshot.records == snapshot.attempts == snapshot.runs == snapshot.pins == 0
            assert snapshot.history <= 1
        assert len(list(tmp_path.glob('product.*.csv'))) == 24


def test_later_old_source_cannot_replace_current_product_even_with_valid_storage_cas(tmp_path):
    store = LocalFileStore(str(tmp_path))
    resource = storage_scope(store, 'current.csv') + ':current.csv'
    with StrategyBox(providers={'output_filestore': store}, settings=ExecutionSettings(max_workers=1)) as box:
        policy = ExactCurrentRevisionPolicy('official.editions', source_revision='edition-Q', input_basis='basis-current')
        box.session.effects.register_revision_policy(resource, policy)
        current = Representation('fixture.csv', 1, 'text/csv', b'edition-Q\naccepted')
        result = box.invoke('save.product', inputs={'material': current}, parameters={'destination': 'current.csv',
            'source_revision': 'edition-Q', 'input_basis': 'basis-current'}, timeout=5)
        assert result.outcome == 'succeeded', result.diagnostics
        result.close()
        revision = store.current_revision('current.csv')
        older = Representation('fixture.csv', 1, 'text/csv', b'edition-Z\nold')
        rejected = box.invoke('save.product', inputs={'material': older}, parameters={
            'destination': 'current.csv', 'mode': 'replace_expected_revision', 'expected_revision': revision,
            'source_revision': 'edition-Z', 'input_basis': 'basis-old'}, timeout=5)
        assert rejected.outcome == 'failed'
        assert 'effect.source_revision_rejected' in rejected.diagnostics
        assert store.current_revision('current.csv') == revision
        assert (tmp_path / 'current.csv').read_bytes() == current.data
        rejected.close()


def test_result_read_lease_keeps_effect_evidence_until_reader_releases(tmp_path):
    store = LocalFileStore(str(tmp_path))
    with StrategyBox(providers={'output_filestore': store}) as box:
        box.session.effects = EffectAuthority(max_records=1, history_limit=0)
        material = Representation('csv', 1, 'text/csv', b'value\n1')
        result = box.invoke('save.product', inputs={'material': material}, parameters={'destination': 'leased.csv'}, timeout=5)
        reader = result.read('receipt')
        result.close()
        assert box.session.effects.retention_snapshot().records == 1
        assert reader.value.identity == material.identity
        reader.close()
        assert box.session.effects.retention_snapshot().records == 0


def test_actual_competing_save_callbacks_restore_confirmed_current_after_cas_loss(tmp_path):
    from threading import Event
    entered_a, entered_b, release_a, release_b = (Event() for _ in range(4))
    class CompetingStore(LocalFileStore):
        def replace_if_revision(self, path, data, expected_revision):
            entered, release = (entered_a, release_a) if data == b'A' else (entered_b, release_b)
            entered.set()
            assert release.wait(5)
            return super().replace_if_revision(path, data, expected_revision)
    store = CompetingStore(str(tmp_path))
    assert store.create_if_absent('report.csv', b'baseline')
    revision = store.current_revision('report.csv')
    material_a = Representation('fixture.csv', 1, 'text/csv', b'A')
    material_b = Representation('fixture.csv', 1, 'text/csv', b'B')
    with StrategyBox(providers={'output_filestore': store},
                     settings=ExecutionSettings(max_workers=2, active_runs=2)) as box:
        parameters = dict(destination='report.csv', mode='replace_expected_revision', expected_revision=revision)
        first = box.submit(box.prepare('save.product', inputs={'material': material_a}, parameters=parameters))
        assert entered_a.wait(2)
        second = box.submit(box.prepare('save.product', inputs={'material': material_b}, parameters=parameters))
        try:
            assert entered_b.wait(2)
            release_a.set()
            assert first.result(3).outcome == 'succeeded'
            pending = next(record for record in box.session.effects.snapshot() if record.intent.identity == material_a.identity)
            assert pending.destination_current is None
        finally:
            release_a.set()
            release_b.set()
        assert second.result(3).outcome == 'failed'
        records = box.session.effects.snapshot()
        actual = next(record for record in records if record.intent.identity == material_a.identity)
        rejected = next(record for record in records if record.intent.identity == material_b.identity)
        assert store.read_bytes('report.csv') == material_a.data
        assert actual.receipt.state == 'confirmed'
        assert actual.destination_current is True and actual.current is True
        assert rejected.receipt.state == 'failed'
        assert rejected.destination_current is False and rejected.current is False
