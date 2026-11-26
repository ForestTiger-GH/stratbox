"""Session-owned sealed bytes with explicit pins and fail-fast live quotas."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from hashlib import sha256
from pathlib import Path
from tempfile import mkdtemp
from threading import RLock
from uuid import uuid4
import os
import shutil

from stratbox.shared.identity import ByteIdentity
from stratbox.shared.data.materials import StagedMaterialRef, staged_references
from stratbox.shared.data.values import fingerprint


class StagingError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass
class _Entry:
    path: Path
    size: int = 0
    reference: StagedMaterialRef | None = None
    owners: set[str] = field(default_factory=set)
    readers: int = 0


class StagedValueStore:
    """Only this registry resolves tokens into its private physical directory."""
    def __init__(self, *, directory=None, max_bytes=16 * 1024**3,
                 max_objects=10000, max_readers=64):
        if any(type(x) is not int or x < 1 for x in (max_bytes, max_objects, max_readers)):
            raise ValueError("stage.invalid_limits")
        self.session_id = uuid4().hex
        self.directory = Path(mkdtemp(prefix="stratbox-stage-", dir=directory))
        from .staging_ownership import StagingOwnership
        self._ownership = StagingOwnership(self.directory,self.session_id)
        self.provider_scope = fingerprint(("staging", self.session_id, str(self.directory)))
        self.max_bytes, self.max_objects, self.max_readers = max_bytes, max_objects, max_readers
        self._lock = RLock()
        self._entries, self._owners = {}, {}
        self._bytes = self._readers = 0
        self._draining = False

    def builder(self, owner, *, budget=None, checkpoint=lambda: None, **properties):
        with self._lock:
            if self._draining:
                raise StagingError("stage.session_closed")
            if len(self._entries) >= self.max_objects:
                raise StagingError("stage.object_limit")
            identifier = uuid4().hex
            entry = _Entry(self.directory / identifier, owners={owner})
            self._entries[identifier] = entry
            self._owners.setdefault(owner, set()).add(identifier)
        try:
            return StageBuilder(self, identifier, properties, budget, checkpoint)
        except BaseException:
            self._drop(identifier)
            raise

    def _entry(self, reference):
        if not isinstance(reference, StagedMaterialRef):
            raise StagingError("stage.reference_required")
        if reference.session_id != self.session_id or reference.provider_scope != self.provider_scope:
            raise StagingError("stage.foreign_session")
        entry = self._entries.get(reference.stage_id)
        if entry is None or entry.reference is None:
            raise StagingError("stage.expired_reference")
        # Attribution wrappers can add logical context; physical metadata and
        # source use remain part of the sealed descriptor and are never mutable.
        if entry.reference != reference:
            raise StagingError("stage.descriptor_mismatch")
        return entry

    def pin(self, value, owner):
        references = staged_references(value)
        with self._lock:
            entries = [(ref, self._entry(ref)) for ref in references]
            old = set(self._owners.get(owner, ()))
            current = {reference.stage_id for reference in references}
            for reference, entry in entries:
                entry.owners.add(owner)
                self._owners.setdefault(owner, set()).add(reference.stage_id)
            for identifier in old - current:
                entry = self._entries[identifier]
                entry.owners.discard(owner)
                self._owners[owner].discard(identifier)
                if not entry.owners and not entry.readers:
                    self._drop(identifier)
            if owner in self._owners and not self._owners[owner]:
                self._owners.pop(owner)
        return references

    def release(self, owner):
        with self._lock:
            for identifier in tuple(self._owners.pop(owner, ())):
                entry = self._entries.get(identifier)
                if entry is not None:
                    entry.owners.discard(owner)
                    if not entry.owners and not entry.readers:
                        self._drop(identifier)
            self._cleanup_directory()

    def _drop(self, identifier):
        with self._lock:
            entry = self._entries.pop(identifier, None)
            if entry is None:
                return
            self._bytes -= entry.size
            for owner in entry.owners:
                ids = self._owners.get(owner)
                if ids is not None:
                    ids.discard(identifier)
                    if not ids:
                        self._owners.pop(owner, None)
            try:
                entry.path.unlink(missing_ok=True)
            finally:
                self._cleanup_directory()

    def _resize(self, identifier, size):
        with self._lock:
            entry = self._entries[identifier]
            delta = size - entry.size
            if self._bytes + delta > self.max_bytes:
                # Never wait for space held by dependent graph outputs.
                raise StagingError("stage.byte_limit")
            self._bytes += delta
            entry.size = size

    @contextmanager
    def open(self, reference):
        with self._lock:
            entry = self._entry(reference)
            if self._readers >= self.max_readers:
                raise StagingError("stage.reader_limit")
            entry.readers += 1
            self._readers += 1
        try:
            with entry.path.open("rb") as stream:
                yield stream
        finally:
            with self._lock:
                entry.readers -= 1
                self._readers -= 1
                if not entry.owners and not entry.readers:
                    self._drop(reference.stage_id)

    def close(self):
        """Stop builders; result/read pins keep their objects independently alive."""
        with self._lock:
            self._draining = True
            self._cleanup_directory()

    def _cleanup_directory(self):
        if self._draining and not self._entries:
            self._ownership.close()
            shutil.rmtree(self.directory, ignore_errors=True)

    def status(self):
        with self._lock:
            return {"session_id": self.session_id, "live_bytes": self._bytes,
                    "objects": len(self._entries), "readers": self._readers,
                    "draining": self._draining}


class StageBuilder:
    def __init__(self, store, identifier, properties, budget, checkpoint):
        self.store, self.stage_id = store, identifier
        self.properties = dict(properties)
        self.budget, self.checkpoint = budget, checkpoint
        self._file = store._entries[identifier].path.open("w+b")
        self._sealed = None
        self.stream = self

    def _writable(self):
        self.checkpoint()
        if self._sealed is not None or self._file.closed:
            raise StagingError("stage.writer_closed")

    def write(self, data):
        self._writable()
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("stage.binary_write_required")
        if self.budget is not None:
            self.budget.charge("temporary_bytes", len(data))
        end = self._file.tell() + len(data)
        previous = self.store._entries[self.stage_id].size
        self.store._resize(self.stage_id, max(previous, end))
        try:
            written = self._file.write(data)
        except BaseException:
            self.store._resize(self.stage_id, max(previous, self._file.tell()))
            raise
        if written != len(data):
            raise StagingError("stage.short_write")
        return written

    def read(self, size=-1):
        self.checkpoint()
        return self._file.read(size)

    def seek(self, offset, whence=0):
        return self._file.seek(offset, whence)

    def tell(self):
        return self._file.tell()

    def seekable(self):
        return True

    def readable(self):
        return True

    def writable(self):
        return self._sealed is None and not self._file.closed

    def flush(self):
        return self._file.flush()

    def truncate(self, size=None):
        self._writable()
        size = self._file.tell() if size is None else size
        if type(size) is not int or size < 0:
            raise StagingError("stage.truncate_size_invalid")
        previous = self.store._entries[self.stage_id].size
        if size > previous and self.budget is not None:
            self.budget.charge("temporary_bytes", size - previous)
        # Reserve extension before mutation. A proposed shrink must not lend
        # space to another writer until its physical operation has succeeded.
        self.store._resize(self.stage_id, max(previous, size))
        try:
            result = self._file.truncate(size)
        except BaseException:
            try:
                # Include pending buffered writes, then observe a possible
                # truncate-before-error rather than assuming no mutation.
                self._file.flush()
                actual = os.fstat(self._file.fileno()).st_size
            except (OSError, ValueError):
                pass  # Keep the conservative reservation until close.
            else:
                self.store._resize(self.stage_id, actual)
            raise
        self.store._resize(self.stage_id, size)
        return result

    def seal(self, *, metadata=None, lineage=None, source_uses=None):
        if self._sealed is not None:
            return self._sealed
        self._writable()
        self._file.flush()
        self._file.seek(0)
        digest, size = sha256(), 0
        while chunk := self._file.read(1024 * 1024):
            self.checkpoint()
            digest.update(chunk)
            size += len(chunk)
        identity = ByteIdentity(digest.hexdigest(), size)
        properties = dict(self.properties)
        for key, value in (("metadata", metadata), ("lineage", lineage), ("source_uses", source_uses)):
            if value is not None:
                properties[key] = value
        reference = StagedMaterialRef(self.stage_id, self.store.provider_scope,
                                     self.store.session_id, identity, **properties)
        self._file.close()
        with self.store._lock:
            self.store._resize(self.stage_id, size)
            self.store._entries[self.stage_id].reference = reference
        self._sealed = reference
        return reference

    def close(self):
        if not self._file.closed:
            self._file.close()
        if self._sealed is None:
            self.store._drop(self.stage_id)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
