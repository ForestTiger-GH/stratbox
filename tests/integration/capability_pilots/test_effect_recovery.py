"""A real-store lost reply preserves computation and resumes only saving."""
from stratbox.core.execution.contracts import EffectReceipt
from stratbox.core.execution.session import ExecutionSettings
from stratbox.core.storage.bytes import file_identity
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from .conftest import row_profile, ratio_pair


def test_lost_save_reply_reconciles_from_retained_product_without_reextract(profiled_catalog, two_tables, tmp_path, monkeypatch):
    import stratbox.core.capabilities.workbooks as codec
    original, decodes = codec.read_workbook_cells, []
    def decode(*args, **options):
        decodes.append(1)
        return original(*args, **options)
    monkeypatch.setattr(codec, 'read_workbook_cells', decode)
    class LostReplyStore(LocalFileStore):
        writes = 0
        def create_if_absent(self, path, data):
            self.writes += 1
            result = super().create_if_absent(path, data)
            if self.writes == 1:
                raise TimeoutError('committed bytes, lost reply')
            return result
    store = LostReplyStore(str(tmp_path))
    with StrategyBox(capabilities=profiled_catalog, providers={'output_filestore': store},
                     settings=ExecutionSettings(max_workers=1)) as box:
        failed = box.invoke('cascade.observation_package', inputs={'material': two_tables}, parameters={
            'numerator_profile': row_profile(), 'denominator_profile': row_profile('Total', 'fixture.total'),
            'destination': 'ratio.csv', 'pair': ratio_pair()}, timeout=15)
        assert failed.outcome == 'unknown'
        assert (tmp_path / 'ratio.csv').exists()
        assert failed.scope_outputs['cascade.observation_package/ratio/calculate']['observations'].observations
        material = failed.scope_outputs['cascade.observation_package/ratio/render']['representation']
        assert decodes == [1]
        record, = box.session.effects.snapshot()
        assert record.receipt.state == 'unknown'
        retry = box.invoke('save.product', inputs={'material': material}, parameters={'destination': 'ratio.csv'}, timeout=10)
        assert retry.outcome == 'unknown'
        assert store.writes == 1
        assert file_identity('ratio.csv', store=store) == material.identity
        box.session.effects.reconcile(record.intent.run_id, record.intent.scope_id, record.intent.effect_id,
            EffectReceipt('storage.write', 'confirmed', effect_id=record.intent.effect_id,
                reference='ratio.csv', identity=material.identity, guarantee='atomic_create'),
            expected_revision=record.revision)
        recovered = box.invoke('save.product', inputs={'material': material}, parameters={'destination': 'ratio.csv'}, timeout=10)
        assert recovered.outcome == 'succeeded', recovered.diagnostics
        assert recovered.output('receipt').identity == material.identity
        assert store.writes == 1
        assert decodes == [1]
