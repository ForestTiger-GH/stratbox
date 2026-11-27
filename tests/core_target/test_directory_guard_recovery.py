"""Real process death releases held locks without replacing shared anchors."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

from stratbox.core.storage.filestore import LocalFileStore, MutationRejected
from stratbox.core.storage.filestore.types import DIRECTORY_GUARD_NAME
from stratbox.core.storage.staging_ownership import cleanup_abandoned_staging


def test_killed_directory_owner_releases_lock_and_preserves_anchor_inode(tmp_path):
    code = '''
import sys
from stratbox.core.storage.filestore import LocalFileStore
store = LocalFileStore(sys.argv[1])
with store.guard_directory('.'):
    print('locked', flush=True)
    sys.stdin.read()
'''
    # Use an explicit blocking pipe: the child cannot normally exit its context
    # before the parent sends the real uncatchable process termination.
    child = subprocess.Popen([sys.executable, '-u', '-c', code, str(tmp_path)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == 'locked'
        anchor = tmp_path / DIRECTORY_GUARD_NAME
        original = anchor.stat()
        with pytest.raises(MutationRejected, match='busy'):
            with LocalFileStore(tmp_path).guard_directory('.'):
                pass
        child.kill()
        child.wait(timeout=5)
        with LocalFileStore(tmp_path).guard_directory('.'):
            current = anchor.stat()
            assert (current.st_dev, current.st_ino) == (original.st_dev, original.st_ino)
        assert anchor.exists()
        with LocalFileStore(tmp_path).guard_directory('.'):
            assert anchor.stat().st_ino == original.st_ino
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)


def test_killed_private_staging_owner_is_reclaimable_but_live_owner_is_pinned(tmp_path):
    code = '''
import sys
from stratbox.core.storage.staged_values import StagedValueStore
store = StagedValueStore(directory=sys.argv[1])
writer = store.builder('result')
writer.write(b'held bytes')
writer.seal()
print(store.directory, flush=True)
sys.stdin.read()
'''
    child = subprocess.Popen([sys.executable, '-u', '-c', code, str(tmp_path)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        directory = Path(child.stdout.readline().strip())
        assert directory.is_dir()
        assert cleanup_abandoned_staging(tmp_path)['busy'] == 1
        child.kill()
        child.wait(timeout=5)
        assert cleanup_abandoned_staging(tmp_path)['removed'] == 1
        assert not directory.exists()
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)


@pytest.mark.skipif(os.name == 'nt', reason='POSIX symlink qualification')
def test_guard_does_not_follow_a_symlink_anchor(tmp_path):
    external = tmp_path / 'caller'
    external.write_bytes(b'untouched')
    (tmp_path / DIRECTORY_GUARD_NAME).symlink_to(external)
    with pytest.raises(MutationRejected):
        with LocalFileStore(tmp_path).guard_directory('.'):
            pass
    assert external.read_bytes() == b'untouched'


def test_provider_directory_mutations_cannot_remove_a_live_shared_anchor(tmp_path):
    guarded = tmp_path / 'guarded'
    guarded.mkdir()
    store = LocalFileStore(tmp_path)
    with store.guard_directory('guarded'):
        with pytest.raises(MutationRejected, match='coordination'):
            store.rmtree('guarded')
        with pytest.raises(MutationRejected, match='regular file'):
            store.rename('guarded', 'other')
        assert (guarded / DIRECTORY_GUARD_NAME).exists()
