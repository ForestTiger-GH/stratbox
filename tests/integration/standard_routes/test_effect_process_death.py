"""A real killed process preserves effect authority across both crash windows."""
from contextlib import contextmanager
import subprocess
import sys

import pytest

from stratbox.core.execution.effect_state import FileEffectState
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material


CHILD = '''
from contextlib import contextmanager
from pathlib import Path
import sys
from stratbox.core.execution.effect_state import FileEffectState
from stratbox.core.observability.journal import MemoryJournal
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material

directory, window = Path(sys.argv[1]), sys.argv[2]
def hold():
    print('crash-window', flush=True)
    sys.stdin.read()

class Store(LocalFileStore):
    @contextmanager
    def stage_content(self, destination):
        with super().stage_content(destination) as stage:
            class Wrapped:
                stream = stage.stream
                def location(self, identity): return stage.location(identity)
                def commit(self, identity, **kwargs):
                    result = stage.commit(identity, **kwargs)
                    if window == 'external-commit': hold()
                    return result
            yield Wrapped()

class Journal(MemoryJournal):
    def append(self, *args, **kwargs):
        if window == 'receipt-commit' and kwargs.get('kind') == 'effect.settled': hold()
        return super().append(*args, **kwargs)

with StrategyBox(providers={'filestore': Store(directory / 'files'),
        'effect_state': FileEffectState(directory / 'effects')}, journal=Journal()) as box:
    box.invoke('command.artifact.commit', inputs={'material': Material(b'killed writer bytes'),
        'destination': 'objects'})
'''


@pytest.mark.parametrize('window', ('external-commit', 'receipt-commit'))
def test_killed_external_writer_never_replays_unknown_or_forgets_confirmed_receipt(tmp_path, window):
    child = subprocess.Popen([sys.executable, '-u', '-c', CHILD, str(tmp_path), window],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == 'crash-window'
        child.kill()
        child.wait(timeout=5)
    finally:
        if child.poll() is None:
            child.kill()
        _, stderr = child.communicate(timeout=5)
    assert not stderr
    state = FileEffectState(tmp_path / 'effects')
    summary, = state.page()
    historical = state.get(summary['effect_id'])
    assert historical.status == ('unknown' if window == 'external-commit' else 'confirmed')

    class CountingStore(LocalFileStore):
        writes = 0
        @contextmanager
        def stage_content(self, destination):
            self.writes += 1
            with super().stage_content(destination) as stage:
                yield stage

    store = CountingStore(tmp_path / 'files')
    with StrategyBox(providers={'filestore': store, 'effect_state': state}) as box:
        result = box.invoke('command.artifact.commit', inputs={'material': Material(b'killed writer bytes'),
            'destination': 'objects'})
        assert result.outcome == ('unknown' if window == 'external-commit' else 'succeeded')
        assert store.writes == 0
        reconciled = box.invoke('command.artifact.reconcile', inputs={'effect': historical})
        assert reconciled.outcome == 'succeeded' and reconciled.output('assessment').complete
        final = state.get(historical.effect_id)
        assert final.status == 'confirmed' and store.writes == 0
        assert final.evidence['evidence_kind'] in {'direct_result', 'verified_current_postcondition'}
