"""Cross-process ownership of private temporary directories, never caller files."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
from .ownership_lock import lock_stream as _lock, unlock_stream as _unlock

_MARKER = 'stratbox-session.json'
_LOCK = 'stratbox-session.lock'
_KIND = 'stratbox.private.staged-values'


class StagingOwnership:
    def __init__(self,directory,session_id):
        self.directory = Path(directory)
        descriptor = os.open(self.directory/_LOCK,os.O_RDWR | os.O_CREAT | os.O_EXCL,0o600)
        self.stream = os.fdopen(descriptor,'r+b')
        self.stream.write(b'0'); self.stream.flush()
        try:
            _lock(self.stream)
            (self.directory/_MARKER).write_text(json.dumps({'kind':_KIND,
                'session_id':session_id,'directory':self.directory.name}),encoding='utf-8')
        except BaseException:
            self.stream.close()
            raise

    def close(self):
        if not self.stream.closed:
            _unlock(self.stream)
            self.stream.close()


def cleanup_abandoned_staging(directory, *, max_entries=1000):
    """Reclaim only marked, unlocked immediate private session directories."""
    if type(max_entries) is not int or not 1 <= max_entries <= 100000:
        raise ValueError('stage.cleanup_limit_invalid')
    scanned = removed = busy = 0
    root = Path(directory)
    if not root.exists():
        return {'scanned':0,'removed':0,'busy':0}
    with os.scandir(root) as entries:
        for entry in entries:
            if scanned >= max_entries:
                break
            scanned += 1
            if not entry.name.startswith('stratbox-stage-') or not entry.is_dir(follow_symlinks=False):
                continue
            candidate = Path(entry.path)
            marker = candidate/_MARKER
            lock = candidate/_LOCK
            if marker.is_symlink() or lock.is_symlink():
                continue
            try:
                with marker.open('rb') as source:
                    raw = source.read(4097)
                if len(raw) > 4096:
                    continue
                metadata = json.loads(raw)
                if (metadata.get('kind') != _KIND or metadata.get('directory') != entry.name
                        or not isinstance(metadata.get('session_id'),str) or len(metadata['session_id']) != 32):
                    continue
                descriptor = os.open(lock,os.O_RDWR | getattr(os,'O_NOFOLLOW',0))
                stream = os.fdopen(descriptor,'r+b')
            except (OSError,ValueError,TypeError):
                continue
            try:
                try:
                    _lock(stream)
                except OSError:
                    busy += 1
                    continue
                # A new session always creates a fresh private directory and
                # cannot resume this token. Close the lock before removal for
                # Windows; competing janitors may only remove the same orphan.
                _unlock(stream)
                stream.close()
                shutil.rmtree(candidate)
                removed += 1
            except OSError:
                continue
            finally:
                stream.close()
    return {'scanned':scanned,'removed':removed,'busy':busy}
