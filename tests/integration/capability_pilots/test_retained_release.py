"""A reusable retained-product cascade and separately verified release pointer."""
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from .conftest import row_profile


def test_retained_cascade_saves_members_then_publishes_verified_release(profiled_catalog, two_tables, tmp_path):
    store = LocalFileStore(str(tmp_path))
    with StrategyBox(capabilities=profiled_catalog, providers={'output_filestore': store}) as box:
        extracted = box.invoke('extract.observations', inputs={'material': two_tables},
                               parameters={'profile': row_profile()}, timeout=10)
        batch = extracted.output('observations')
        plan = box.prepare('cascade.coherent_products', inputs={
            'primary__observations': batch, 'secondary__observations': batch}, parameters={
            'primary__destination': 'primary.csv', 'secondary__destination': 'secondary.csv',
            'secondary__format': 'jsonl'})
        assert not any(task.operation_id in {'http.acquire', 'workbook.decode', 'fields.interpret'} for task in plan.tasks)
        saved = box.run(plan, timeout=10)
        assert saved.outcome == 'succeeded', saved.diagnostics
        receipts = (saved.output('primary__receipt'), saved.output('secondary__receipt'))
        published = box.invoke('publish.release', inputs={'receipts': receipts}, parameters={
            'release_id': 'fixture.release', 'destination': 'release.json',
            'members': ('primary', 'secondary'),
            'expected_members': {name: receipt.identity.sha256 for name, receipt in zip(('primary', 'secondary'), receipts)},
        }, timeout=10)
        assert published.outcome == 'succeeded', published.diagnostics
        assert (tmp_path / 'release.json').read_bytes() == published.output('manifest').data
        assert all((tmp_path / name).exists() for name in ('primary.csv', 'secondary.csv'))
        assert len([scope for scope in plan.scopes if scope.definition_id == 'scenario.save_retained_product']) == 2
