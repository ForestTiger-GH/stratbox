"""Held OS locks over stable local anchors; process death releases ownership."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import stat


def lock_stream(stream):
    stream.seek(0)
    if os.name == 'nt':
        import msvcrt
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def unlock_stream(stream):
    stream.seek(0)
    if os.name == 'nt':
        import msvcrt
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@contextmanager
def held_anchor(path):
    """Fail immediately when busy; never unlink the shared coordination inode.

    The directory belongs to a qualified local provider. Cooperating writers
    preserve the anchor; a writer that can replace it is outside this guarantee.
    """
    path = Path(path)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(descriptor, 'r+b') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise OSError('storage.lock_anchor_invalid')
        if before.st_size == 0:
            stream.write(b'0')
            stream.flush()
        lock_stream(stream)
        try:
            current = path.lstat()
            if stat.S_ISLNK(current.st_mode) or (before.st_dev, before.st_ino) != (current.st_dev, current.st_ino):
                raise OSError('storage.lock_anchor_replaced')
            yield
        finally:
            unlock_stream(stream)
